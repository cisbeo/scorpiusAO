"""
LLM Service for Claude API interactions.
"""
import json
from typing import Dict, List, Any
from anthropic import Anthropic, AsyncAnthropic
import redis.asyncio as redis
import redis as redis_sync

from app.core.config import settings
from app.core.prompts import (
    TENDER_ANALYSIS_PROMPT,
    CRITERIA_EXTRACTION_PROMPT,
    RESPONSE_GENERATION_PROMPT,
    COMPLIANCE_CHECK_PROMPT
)


class LLMService:
    """Service for interacting with Claude AI."""

    def __init__(self):
        # Async client for API endpoints
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        # Sync client for Celery tasks
        self.sync_client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model
        self.redis_client: redis.Redis | None = None
        self.redis_sync_client: redis_sync.Redis | None = None

    async def _get_cache(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(settings.redis_url)
        return self.redis_client

    async def _cache_key(self, prefix: str, content: str) -> str:
        """Generate cache key from content."""
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{prefix}:{content_hash}"

    async def analyze_tender(
        self,
        tender_content: str,
        context: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Analyze tender document and extract key information.

        Args:
            tender_content: Full text of the tender document
            context: Additional context for analysis

        Returns:
            Analysis results including summary, requirements, deadlines, etc.
        """
        cache = await self._get_cache()
        cache_key = await self._cache_key("tender_analysis", tender_content)

        # Check cache
        cached = await cache.get(cache_key)
        if cached:
            print(f"✅ Cache hit for tender analysis")
            return json.loads(cached)

        # Truncate content if too long (keep first 100k chars)
        if len(tender_content) > 100000:
            print(f"⚠️  Content too long ({len(tender_content)} chars), truncating to 100k")
            tender_content = tender_content[:100000] + "\n\n[...contenu tronqué...]"

        prompt = TENDER_ANALYSIS_PROMPT.format(tender_content=tender_content)

        print(f"🤖 Calling Claude API for tender analysis ({len(prompt)} chars prompt)...")

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            print(f"✅ Claude API response received ({response.usage.input_tokens} input, {response.usage.output_tokens} output tokens)")
        except Exception as e:
            print(f"❌ Claude API error: {e}")
            raise

        # Parse response
        result = self._parse_analysis_response(response.content[0].text)

        # Cache for 1 hour
        await cache.setex(cache_key, 3600, json.dumps(result))

        return result

    async def extract_criteria(
        self,
        tender_content: str
    ) -> List[Dict[str, Any]]:
        """
        Extract evaluation criteria from tender.

        Args:
            tender_content: Full text of the tender document

        Returns:
            List of criteria with type, description, weight, and mandatory status
        """
        # Truncate content if too long
        if len(tender_content) > 100000:
            tender_content = tender_content[:100000] + "\n\n[...contenu tronqué...]"

        prompt = CRITERIA_EXTRACTION_PROMPT.format(tender_content=tender_content)

        print(f"🤖 Calling Claude API for criteria extraction...")

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,  # More tokens for detailed criteria
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            print(f"✅ Claude API response received for criteria")
        except Exception as e:
            print(f"❌ Claude API error (criteria): {e}")
            raise

        return self._parse_criteria_response(response.content[0].text)

    async def generate_response_section(
        self,
        section_type: str,
        requirements: Dict[str, Any],
        company_context: Dict[str, Any] | None = None
    ) -> str:
        """
        Generate a response section for tender.

        Args:
            section_type: Type of section (company_presentation, methodology, etc.)
            requirements: Requirements from tender
            company_context: Company information and past projects

        Returns:
            Generated section content
        """
        prompt = RESPONSE_GENERATION_PROMPT.format(
            section_type=section_type,
            requirements=json.dumps(requirements, indent=2, ensure_ascii=False),
            company_context=json.dumps(company_context or {}, indent=2, ensure_ascii=False)
        )

        print(f"🤖 Calling Claude API for {section_type} section generation...")

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            print(f"✅ Claude API response received for section generation ({response.usage.input_tokens} input, {response.usage.output_tokens} output tokens)")
        except Exception as e:
            print(f"❌ Claude API error (section generation): {e}")
            raise

        return response.content[0].text

    async def check_compliance(
        self,
        proposal: str,
        requirements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check proposal compliance against requirements.

        Args:
            proposal: Full proposal text
            requirements: List of requirements to check

        Returns:
            Compliance analysis with score and issues
        """
        # Truncate content if too long
        if len(proposal) > 100000:
            print(f"⚠️  Proposal too long ({len(proposal)} chars), truncating to 100k")
            proposal = proposal[:100000] + "\n\n[...contenu tronqué...]"

        requirements_text = "\n".join([
            f"- {req.get('description', str(req))}" for req in requirements
        ])

        prompt = COMPLIANCE_CHECK_PROMPT.format(
            proposal=proposal,
            requirements=requirements_text
        )

        print(f"🤖 Calling Claude API for compliance check...")

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            print(f"✅ Claude API response received for compliance ({response.usage.input_tokens} input, {response.usage.output_tokens} output tokens)")
        except Exception as e:
            print(f"❌ Claude API error (compliance): {e}")
            raise

        return self._parse_compliance_response(response.content[0].text)

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse analysis response from Claude."""
        try:
            # Try to extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            return json.loads(response)
        except Exception:
            # Fallback to structured text parsing
            return {
                "summary": "Unable to parse analysis",
                "raw_response": response
            }

    def _parse_criteria_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse criteria extraction response."""
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            return json.loads(response)
        except Exception:
            return []

    def _parse_compliance_response(self, response: str) -> Dict[str, Any]:
        """Parse compliance check response."""
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            return json.loads(response)
        except Exception:
            return {
                "compliance_score": 0.0,
                "issues": ["Unable to parse compliance check"],
                "raw_response": response
            }

    def _build_hierarchical_structure(
        self,
        sections: List[Dict[str, Any]]
    ) -> str:
        """
        Build hierarchical structure for LLM prompt from sections.

        Strategy:
        - Show only key sections in full detail
        - Show parent sections (headers) with title only
        - Skip TOC sections entirely
        - Preserve hierarchy for context

        This reduces tokens from ~25k to ~7.5k (-70%)

        Args:
            sections: List of section dicts with hierarchy info

        Returns:
            Formatted hierarchical text for LLM
        """
        output_lines = []

        # Group sections by parent for efficient lookup
        sections_by_number = {s.get('section_number'): s for s in sections if s.get('section_number')}

        for section in sections:
            # Skip TOC sections
            if section.get('is_toc'):
                continue

            section_number = section.get('section_number', '')
            title = section.get('title', '')
            content = section.get('content', '')
            is_key = section.get('is_key_section', False)
            level = section.get('level', 1)

            # Indentation based on level
            indent = "  " * (level - 1)

            # Format section header
            header = f"{indent}## {section_number} - {title}" if section_number else f"{indent}## {title}"

            if is_key:
                # KEY SECTIONS: Full content (essential for analysis)
                output_lines.append(header)
                if content:
                    output_lines.append(f"{indent}{content}")
                output_lines.append("")  # blank line
            elif content and len(content) > 200:
                # REGULAR SECTIONS WITH SUBSTANTIAL CONTENT: Summary only (200 chars max)
                output_lines.append(header)
                summary = content[:200] + "..."
                output_lines.append(f"{indent}[Résumé] {summary}")
                output_lines.append("")
            elif content:
                # SHORT CONTENT: Include in full (already concise)
                output_lines.append(header)
                output_lines.append(f"{indent}{content}")
                output_lines.append("")
            else:
                # PARENT SECTIONS (no content): Headers only for context
                output_lines.append(header)

        return "\n".join(output_lines)

    def _serialize_section_for_llm(
        self,
        section: Dict[str, Any],
        include_full_content: bool = False
    ) -> str:
        """
        Serialize a single section for LLM input.

        Args:
            section: Section dict
            include_full_content: Whether to include full content

        Returns:
            Formatted section text
        """
        number = section.get('section_number', '')
        title = section.get('title', '')
        content = section.get('content', '')

        lines = []
        if number:
            lines.append(f"Section {number}: {title}")
        else:
            lines.append(title)

        if include_full_content and content:
            lines.append(content)

        return "\n".join(lines)

    async def analyze_tender_structured(
        self,
        sections: List[Dict[str, Any]],
        metadata: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Analyze tender using structured sections with hierarchy.

        More efficient than analyze_tender():
        - Uses hierarchical structure (-70% tokens)
        - Focuses on key sections
        - Preserves context via parent sections

        Args:
            sections: List of structured sections with hierarchy
            metadata: Document metadata

        Returns:
            Analysis results
        """
        # Build hierarchical structure
        structured_content = self._build_hierarchical_structure(sections)

        # Import the new prompt (will create it next)
        from app.core.prompts import TENDER_ANALYSIS_STRUCTURED_PROMPT

        cache = await self._get_cache()
        cache_key = await self._cache_key("tender_structured", structured_content)

        # Check cache
        cached = await cache.get(cache_key)
        if cached:
            print(f"✅ Cache hit for structured tender analysis")
            return json.loads(cached)

        prompt = TENDER_ANALYSIS_STRUCTURED_PROMPT.format(
            sections=structured_content,
            metadata=json.dumps(metadata or {}, indent=2)
        )

        print(f"🤖 Calling Claude API for structured analysis ({len(prompt)} chars, ~{len(prompt)//4} tokens)...")

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            print(f"✅ Claude API response: {response.usage.input_tokens} input, {response.usage.output_tokens} output tokens")
            print(f"💰 Cost estimate: ${(response.usage.input_tokens * 0.003 + response.usage.output_tokens * 0.015) / 1000:.4f}")
        except Exception as e:
            print(f"❌ Claude API error: {e}")
            raise

        # Parse response
        result = self._parse_analysis_response(response.content[0].text)

        # Cache for 1 hour
        await cache.setex(cache_key, 3600, json.dumps(result))

        return result

    # ========== SYNCHRONOUS METHODS FOR CELERY TASKS ==========

    def _get_cache_sync(self) -> redis_sync.Redis:
        """Get or create sync Redis client."""
        if self.redis_sync_client is None:
            self.redis_sync_client = redis_sync.from_url(settings.redis_url)
        return self.redis_sync_client

    def _cache_key_sync(self, prefix: str, content: str) -> str:
        """Generate cache key from content (sync version)."""
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{prefix}:{content_hash}"

    def analyze_tender_sync(
        self,
        tender_content: str,
        context: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Analyze tender document (sync version for Celery tasks).

        Args:
            tender_content: Full text of the tender document
            context: Additional context for analysis

        Returns:
            Analysis results including summary, requirements, deadlines, etc.
        """
        cache = self._get_cache_sync()
        cache_key = self._cache_key_sync("tender_analysis", tender_content)

        # Check cache
        cached = cache.get(cache_key)
        if cached:
            print(f"✅ Cache hit for tender analysis")
            return json.loads(cached)

        # Truncate content if too long (keep first 100k chars)
        if len(tender_content) > 100000:
            print(f"⚠️  Content too long ({len(tender_content)} chars), truncating to 100k")
            tender_content = tender_content[:100000] + "\n\n[...contenu tronqué...]"

        prompt = TENDER_ANALYSIS_PROMPT.format(tender_content=tender_content)

        print(f"🤖 Calling Claude API for tender analysis ({len(prompt)} chars prompt)...")

        try:
            response = self.sync_client.messages.create(
                model=self.model,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            print(f"✅ Claude API response received ({response.usage.input_tokens} input, {response.usage.output_tokens} output tokens)")
        except Exception as e:
            print(f"❌ Claude API error: {e}")
            raise

        # Parse response
        result = self._parse_analysis_response(response.content[0].text)

        # Cache for 1 hour
        cache.setex(cache_key, 3600, json.dumps(result))

        return result

    def extract_criteria_sync(
        self,
        tender_content: str
    ) -> List[Dict[str, Any]]:
        """
        Extract evaluation criteria from tender (sync version for Celery tasks).

        Args:
            tender_content: Full text of the tender document

        Returns:
            List of criteria with type, description, weight, and mandatory status
        """
        # Truncate content if too long
        if len(tender_content) > 100000:
            tender_content = tender_content[:100000] + "\n\n[...contenu tronqué...]"

        prompt = CRITERIA_EXTRACTION_PROMPT.format(tender_content=tender_content)

        print(f"🤖 Calling Claude API for criteria extraction...")

        try:
            response = self.sync_client.messages.create(
                model=self.model,
                max_tokens=4000,  # More tokens for detailed criteria
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            print(f"✅ Claude API response received for criteria")
        except Exception as e:
            print(f"❌ Claude API error (criteria): {e}")
            raise

        return self._parse_criteria_response(response.content[0].text)


# Global instance
llm_service = LLMService()
