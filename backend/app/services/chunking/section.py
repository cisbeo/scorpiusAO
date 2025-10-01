"""
Section-based chunking strategy for hierarchical documents.
"""
import re
from typing import List, Dict, Any, Optional
import logging
from .base import ChunkingStrategy, Chunk

logger = logging.getLogger(__name__)


class SectionChunkingStrategy(ChunkingStrategy):
    """
    Section-based chunking for hierarchical documents.

    Use case: past_proposal, case_study, documentation

    Algorithm:
    1. Detect headers (Markdown # ## ### or numbered 1. 1.1 1.1.1) using regex (Q4)
    2. Split by sections (H1, H2, or H3 depending on size)
    3. If section > max_chunk_size, split recursively with overlap
    4. Include section title in each chunk
    5. Extract all 5 section metadata fields (Q5)
    """

    # Regex patterns (Q4: regex only, no NLP for PHASE 2)
    MARKDOWN_HEADER_PATTERN = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
    NUMBERED_HEADER_PATTERN = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)$', re.MULTILINE)

    def __init__(
        self,
        target_chunk_size: int = 512,
        max_chunk_size: int = 1024,
        overlap: int = 100,  # Q2: 100 tokens for section strategy
        encoding_name: str = "cl100k_base",
        split_level: str = "auto"  # auto, H1, H2, H3, all
    ):
        """
        Initialize section-based chunking.

        Args:
            target_chunk_size: Target tokens per chunk (Q1: 512)
            max_chunk_size: Maximum tokens per chunk (Q1: 1024)
            overlap: Overlap in tokens (Q2: 100 for section)
            encoding_name: tiktoken encoding
            split_level: At which header level to split (auto, H1, H2, H3, all)
        """
        super().__init__(target_chunk_size, max_chunk_size, overlap, encoding_name)
        self.split_level = split_level
        logger.debug(
            f"SectionChunkingStrategy initialized: target={target_chunk_size}, "
            f"max={max_chunk_size}, overlap={overlap}, split_level={split_level}"
        )

    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text by sections with hierarchy detection.

        Args:
            text: Text to chunk
            metadata: Base metadata

        Returns:
            List of Chunk objects with all 5 section metadata fields (Q5)
        """
        metadata = metadata or {}

        if not text or not text.strip():
            logger.warning("Empty text provided to SectionChunkingStrategy")
            return []

        # 1. Detect all sections
        sections = self._detect_sections(text)
        logger.debug(f"Detected {len(sections)} sections")

        # 2. Determine split level (auto-detect if needed)
        if self.split_level == "auto":
            split_level = self._auto_detect_split_level(sections)
            logger.debug(f"Auto-detected split level: {split_level}")
        else:
            split_level = self.split_level

        # 3. Split by sections at chosen level
        chunks = []
        for section in sections:
            if section['level'] == split_level or split_level == "all":
                section_chunks = self._chunk_section(section, metadata)
                chunks.extend(section_chunks)

        # 4. Update total_chunks count
        for idx, chunk in enumerate(chunks):
            chunk.index = idx
            chunk.total_chunks = len(chunks)

        logger.info(
            f"SectionChunkingStrategy created {len(chunks)} chunks "
            f"from {len(sections)} sections (split_level={split_level})"
        )

        return chunks

    def _detect_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect all sections (Markdown or numbered) using regex (Q4).

        Args:
            text: Input text

        Returns:
            List of section dicts with:
            - level: H1, H2, H3
            - title: Section title
            - number: Section number (if numbered) (Q5)
            - parent: Parent section title (Q5)
            - start_pos: Start position in text
            - end_pos: End position in text
            - content: Section content
        """
        sections = []

        # Try Markdown headers first
        markdown_matches = list(self.MARKDOWN_HEADER_PATTERN.finditer(text))

        if markdown_matches:
            parent_stack = {}  # Track parent sections by level

            for i, match in enumerate(markdown_matches):
                level = f"H{len(match.group(1))}"  # # -> H1, ## -> H2
                title = match.group(2).strip()
                start_pos = match.start()

                # End position is start of next header or end of text
                end_pos = (
                    markdown_matches[i + 1].start()
                    if i + 1 < len(markdown_matches)
                    else len(text)
                )

                content = text[start_pos:end_pos].strip()

                # Determine parent section (Q5)
                level_num = int(level[1])  # H1 -> 1, H2 -> 2
                parent = None
                if level_num > 1:
                    # Look for parent at level-1
                    parent_level = f"H{level_num - 1}"
                    parent = parent_stack.get(parent_level)

                # Update parent stack
                parent_stack[level] = title

                sections.append({
                    'level': level,
                    'title': title,
                    'number': None,
                    'parent': parent,
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'content': content
                })

        # Try numbered headers (1. 1.1 1.1.1)
        else:
            numbered_matches = list(self.NUMBERED_HEADER_PATTERN.finditer(text))

            if numbered_matches:
                parent_stack = {}

                for i, match in enumerate(numbered_matches):
                    number = match.group(1)
                    title = match.group(2).strip()

                    # Determine level from number depth (Q5)
                    depth = number.count('.') + 1
                    level = f"H{min(depth, 3)}"

                    start_pos = match.start()
                    end_pos = (
                        numbered_matches[i + 1].start()
                        if i + 1 < len(numbered_matches)
                        else len(text)
                    )

                    content = text[start_pos:end_pos].strip()

                    # Determine parent section (Q5)
                    parent = None
                    if '.' in number:
                        parent_number = number.rsplit('.', 1)[0]
                        parent = parent_stack.get(parent_number)

                    # Update parent stack
                    parent_stack[number] = title

                    sections.append({
                        'level': level,
                        'title': title,
                        'number': number,
                        'parent': parent,
                        'start_pos': start_pos,
                        'end_pos': end_pos,
                        'content': content
                    })

        # If no sections detected, treat whole text as single section
        if not sections:
            logger.debug("No sections detected, treating as single H1 section")
            sections.append({
                'level': 'H1',
                'title': 'Document',
                'number': None,
                'parent': None,
                'start_pos': 0,
                'end_pos': len(text),
                'content': text
            })

        return sections

    def _auto_detect_split_level(self, sections: List[Dict]) -> str:
        """
        Auto-detect optimal split level based on section sizes.

        Strategy:
        - If H2 sections average ~512 tokens -> split at H2
        - If H2 too large -> split at H3
        - If H3 too large -> split at all levels

        Args:
            sections: List of detected sections

        Returns:
            Split level (H1, H2, H3, all)
        """
        # Count sections by level
        h2_sections = [s for s in sections if s['level'] == 'H2']
        h3_sections = [s for s in sections if s['level'] == 'H3']

        # Calculate average tokens per H2 section
        if h2_sections:
            avg_h2_tokens = sum(
                self.get_token_count(s['content']) for s in h2_sections
            ) / len(h2_sections)

            if avg_h2_tokens <= self.max_chunk_size:
                return 'H2'

        # Calculate average tokens per H3 section
        if h3_sections:
            avg_h3_tokens = sum(
                self.get_token_count(s['content']) for s in h3_sections
            ) / len(h3_sections)

            if avg_h3_tokens <= self.max_chunk_size:
                return 'H3'

        # Fallback: split at all levels
        return 'all'

    def _chunk_section(
        self,
        section: Dict[str, Any],
        base_metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Chunk a single section with all 5 metadata fields (Q5).

        If section fits in max_chunk_size -> single chunk
        Otherwise -> split recursively with overlap (Q2: 100 tokens)

        Args:
            section: Section dict
            base_metadata: Base metadata

        Returns:
            List of Chunk objects
        """
        content = section['content']
        token_count = self.get_token_count(content)

        chunks = []

        # Case 1: Section fits in single chunk
        if token_count <= self.max_chunk_size:
            chunk = Chunk(
                text=content,
                index=0,  # Will be updated later
                total_chunks=0,  # Will be updated later
                token_count=token_count,
                metadata={
                    **base_metadata,
                    "chunking_strategy": "section"
                },
                # Q5: All 5 section metadata fields
                section_title=section['title'],
                section_level=section['level'],
                section_number=section['number'],
                parent_section=section['parent'],
                content_type="section"
            )
            chunks.append(chunk)

        # Case 2: Section too large, split with overlap (Q2: 100 tokens)
        else:
            logger.debug(
                f"Section '{section['title']}' too large ({token_count} tokens), "
                f"splitting with overlap={self.overlap}"
            )

            # Tokenize section
            tokens = self.encoder.encode(content)

            start = 0
            chunk_idx = 0

            while start < len(tokens):
                end = min(start + self.target_chunk_size, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text = self.encoder.decode(chunk_tokens)

                chunk = Chunk(
                    text=chunk_text,
                    index=chunk_idx,
                    total_chunks=0,  # Will be updated later
                    token_count=len(chunk_tokens),
                    metadata={
                        **base_metadata,
                        "chunking_strategy": "section",
                        "section_split": True,
                        "section_part": f"{chunk_idx + 1}"
                    },
                    # Q5: All 5 section metadata fields preserved
                    section_title=section['title'],
                    section_level=section['level'],
                    section_number=section['number'],
                    parent_section=section['parent'],
                    content_type="section_part"
                )

                chunks.append(chunk)
                chunk_idx += 1
                start = end - self.overlap

        return chunks
