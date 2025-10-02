"""
Document parsing service for PDF extraction.
"""
import io
from typing import Dict, Any, Optional
from datetime import datetime
import re

import PyPDF2
import pdfplumber
from PIL import Image
import pytesseract


class ParserService:
    """Service for parsing tender documents."""

    def __init__(self):
        self.tesseract_config = "--oem 3 --psm 6"

        # TOC detection patterns
        self.TOC_INDICATORS = [
            r'\.{3,}',  # 3+ consecutive dots (...)
            r'\s+\d+\s*$',  # ends with page number
        ]

        # Key section detection patterns (case-insensitive)
        self.KEY_SECTION_PATTERNS = [
            # Exclusions
            (r'exclusion', 'exclusion'),
            (r"motifs?\s+d['']exclusion", 'exclusion'),
            (r'candidats?\s+exclu', 'exclusion'),

            # Obligations
            (r'obligation', 'obligation'),
            (r'engagements?', 'obligation'),
            (r'prescriptions?', 'obligation'),

            # Critères
            (r'crit[èe]res?\s+(de\s+)?(sélection|jugement|attribution|évaluation)', 'criteria'),
            (r'notation', 'criteria'),
            (r'pondération', 'criteria'),

            # Délais
            (r'd[ée]lai', 'deadline'),
            (r"dur[ée]e\s+(de\s+)?l['']accord", 'deadline'),
            (r'date\s+limite', 'deadline'),
            (r'échéances?', 'deadline'),

            # Pénalités
            (r'p[ée]nalit[ée]s?', 'penalty'),
            (r'sanctions?', 'penalty'),
            (r'amendes?', 'penalty'),

            # Prix et conditions financières
            (r'prix\s+(global|unitaire)', 'price'),
            (r'conditions?\s+(financières?|de\s+paiement)', 'price'),
            (r'modalit[ée]s?\s+de\s+(règlement|paiement)', 'price'),

            # Processus ITIL et gouvernance (NEW)
            (r'processus\s+à\s+mettre', 'process'),
            (r'gestion\s+de(s?|s?\s+l[ae\']?)\s+(incidents?|problèmes?|changements?)', 'process'),
            (r'gestion\s+de(s?|s?\s+l[ae\']?)\s+(demandes?|sollicitations?|évènements?|événements?)', 'process'),
            (r'gestion\s+de(s?|s?\s+l[ae\']?)\s+(configurations?|releases?|mises?\s+en\s+production)', 'process'),
            (r'gestion\s+de(s?|s?\s+l[ae\']?)\s+(capacité|disponibilité|continuité|opérations?)', 'process'),
            (r'gestion\s+de(s?|s?\s+l[ae\']?)\s+(escalades?|crises?|niveaux?\s+de\s+service)', 'process'),
            (r'gestion\s+de(s?|s?\s+l[ae\']?)\s+(projets?|contrats?)', 'process'),
            (r'gouvernance', 'governance'),
            (r'pilotage\s+des?\s+prestations?', 'governance'),
            (r'comit[ée]s?\s+(de\s+)?(pilotage|gouvernance|suivi)', 'governance'),
            (r'transition', 'transition'),
            (r'v[eé]rification\s+d["\']aptitude', 'transition'),
            (r'r[eé]versibilit[eé]', 'reversibility'),
            (r'transfert\s+de\s+connaissances?', 'transition'),
        ]

    async def extract_from_pdf(
        self,
        file_content: bytes,
        use_ocr: bool = False
    ) -> Dict[str, Any]:
        """
        Extract text and metadata from PDF with enhanced structure.

        Args:
            file_content: PDF file content as bytes
            use_ocr: Whether to use OCR for scanned PDFs

        Returns:
            Extracted content and metadata including tables and sections
        """
        pdf_file = io.BytesIO(file_content)

        # IMPROVED: Use pdfplumber for better extraction
        extraction = await self._extract_with_pdfplumber_enhanced(pdf_file)

        # If no text found, try OCR
        if not extraction["text"].strip() and use_ocr:
            pdf_file.seek(0)
            extraction["text"] = await self._extract_with_ocr(pdf_file)

        # Extract metadata
        pdf_file.seek(0)
        metadata = await self._extract_metadata(pdf_file)

        # Extract structured information (ENHANCED)
        structured_data = await self._extract_structured_info_enhanced(
            extraction["text"],
            extraction["tables"],
            extraction["sections"]
        )

        return {
            "text": extraction["text"],
            "tables": extraction["tables"],  # NEW: structured tables
            "sections": extraction["sections"],  # NEW: detected sections
            "metadata": metadata,
            "structured": structured_data,
            "page_count": metadata.get("page_count", 0),
            "extraction_method": "pdfplumber_enhanced"
        }

    async def _extract_text_pypdf2(self, pdf_file: io.BytesIO) -> str:
        """Extract text using PyPDF2."""
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            text_parts = []

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            return "\n\n".join(text_parts)
        except Exception as e:
            print(f"PyPDF2 extraction error: {e}")
            return ""

    async def _extract_text_pdfplumber(self, pdf_file: io.BytesIO) -> str:
        """Extract text using pdfplumber (better table support)."""
        try:
            text_parts = []

            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                    # Extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        table_text = self._format_table(table)
                        text_parts.append(table_text)

            return "\n\n".join(text_parts)
        except Exception as e:
            print(f"pdfplumber extraction error: {e}")
            return ""

    async def _extract_with_pdfplumber_enhanced(
        self,
        pdf_file: io.BytesIO
    ) -> Dict[str, Any]:
        """
        Enhanced extraction with pdfplumber: text + structured tables + sections with content.

        Returns:
            {
                "text": str,
                "tables": List[Dict],  # Structured tables with headers/rows
                "sections": List[Dict]  # Detected sections with full content
            }
        """
        try:
            text_parts = []
            tables = []
            sections = []
            pages_text = {}  # Store text by page for content extraction

            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                        pages_text[page_num] = page_text

                        # Detect sections in text
                        detected_sections = self._detect_sections(page_text, page_num)
                        sections.extend(detected_sections)

                    # Extract tables as STRUCTURED data
                    page_tables = page.extract_tables()
                    for table_idx, table_data in enumerate(page_tables):
                        if table_data and len(table_data) > 0:
                            # Clean empty cells
                            cleaned_table = [
                                [cell.strip() if cell else "" for cell in row]
                                for row in table_data
                            ]

                            # Skip empty tables
                            if any(any(cell for cell in row) for row in cleaned_table):
                                structured_table = {
                                    "id": f"table_p{page_num}_{table_idx}",
                                    "page": page_num,
                                    "headers": cleaned_table[0] if len(cleaned_table) > 0 else [],
                                    "rows": cleaned_table[1:] if len(cleaned_table) > 1 else [],
                                    "row_count": len(cleaned_table) - 1,
                                    "col_count": len(cleaned_table[0]) if cleaned_table else 0
                                }
                                tables.append(structured_table)

            # IMPROVED: Extract full content for sections
            sections = self._extract_section_content_from_pages(sections, pages_text)

            # Build parent-child hierarchy
            sections = self._build_section_hierarchy(sections)

            return {
                "text": "\n\n".join(text_parts),
                "tables": tables,
                "sections": sections
            }
        except Exception as e:
            print(f"Enhanced pdfplumber extraction error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "text": "",
                "tables": [],
                "sections": []
            }

    def _extract_section_content_from_pages(
        self,
        sections: list[Dict[str, Any]],
        pages_text: Dict[int, str]
    ) -> list[Dict[str, Any]]:
        """
        Extract full content for each section using page-aware text.

        Args:
            sections: List of detected sections
            pages_text: Dict mapping page_num -> page_text

        Returns:
            Sections with enriched content
        """
        if not sections:
            return sections

        # Group sections by page
        sections_by_page = {}
        for section in sections:
            page = section["page"]
            if page not in sections_by_page:
                sections_by_page[page] = []
            sections_by_page[page].append(section)

        # Extract content for each section
        for page_num, page_sections in sections_by_page.items():
            if page_num not in pages_text:
                continue

            page_text = pages_text[page_num]
            lines = page_text.split('\n')

            # Sort sections by line number
            page_sections_sorted = sorted(page_sections, key=lambda s: s["line"])

            for i, section in enumerate(page_sections_sorted):
                start_line = section["line"]

                # Find end_line: next section or end of page
                if i < len(page_sections_sorted) - 1:
                    end_line = page_sections_sorted[i + 1]["line"]
                else:
                    end_line = len(lines)

                # Extract content lines (skip the title line itself)
                content_lines = []
                for line_idx in range(start_line + 1, end_line):
                    if line_idx < len(lines):
                        line = lines[line_idx].strip()
                        if line:  # Skip empty lines
                            content_lines.append(line)

                # Store full content (limit to 2000 chars)
                full_content = "\n".join(content_lines)
                section["content"] = full_content[:2000] if len(full_content) > 2000 else full_content
                section["content_length"] = len(full_content)
                section["content_truncated"] = len(full_content) > 2000

                # Detect if section is TOC
                section["is_toc"] = self._is_toc_section(section)

                # Detect if section is key section
                is_key, category = self._is_key_section(section)
                section["is_key_section"] = is_key
                section["key_category"] = category if is_key else None

        return sections

    def _is_toc_section(
        self,
        section: Dict[str, Any]
    ) -> bool:
        """
        Detect if a section is part of Table of Contents.

        TOC characteristics:
        - Title contains dots pattern (............)
        - Empty or very short content (< 50 chars)
        - Usually on first pages (1-5)
        - Title may end with page number

        Args:
            section: Section dict with title, content, page

        Returns:
            True if section is TOC
        """
        title = section.get("title", "")
        content = section.get("content", "")
        page = section.get("page", 999)

        # Check title for TOC patterns
        has_dots = any(re.search(pattern, title) for pattern in self.TOC_INDICATORS)

        # Check content length (TOC sections have no real content)
        has_no_content = len(content) < 50

        # Check page number (TOC usually on first pages)
        is_early_page = page <= 5

        # A section is TOC if:
        # 1. Title has dots AND no content (most reliable)
        # 2. OR very early page (1-3) with no content (could be cover/TOC)
        return (has_dots and has_no_content) or (page <= 3 and has_no_content and has_dots)

    def _is_key_section(
        self,
        section: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Detect if a section is a key section for tender analysis.

        Key sections include:
        - Exclusions (exclusion criteria)
        - Obligations (contractual obligations)
        - Criteria (evaluation/selection criteria)
        - Deadlines (time limits, durations)
        - Penalties (financial penalties)
        - Price (pricing conditions)

        Args:
            section: Section dict with title, content

        Returns:
            Tuple (is_key_section, category) where category is one of:
            'exclusion', 'obligation', 'criteria', 'deadline', 'penalty', 'price', or None
        """
        title = section.get("title", "").lower()
        content = section.get("content", "").lower()

        # Check title and content against patterns
        for pattern, category in self.KEY_SECTION_PATTERNS:
            # Match in title (stronger signal)
            if re.search(pattern, title, re.IGNORECASE):
                return True, category

            # Match in content (weaker signal, requires longer content)
            if len(content) > 100 and re.search(pattern, content, re.IGNORECASE):
                return True, category

        return False, None

    def _build_section_hierarchy(
        self,
        sections: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """
        Build parent-child hierarchy for sections based on numbering.

        Examples:
        - "4.1.4.2" has parent "4.1.4"
        - "4.1.4" has parent "4.1"
        - "4.1" has parent "4"
        - "4" has no parent

        Args:
            sections: List of sections with section_number

        Returns:
            Sections with parent_number added
        """
        for section in sections:
            section_number = section.get("number")

            if not section_number:
                section["parent_number"] = None
                continue

            # Extract parent number by removing last component
            # "4.1.4.2" -> "4.1.4"
            # "4.1" -> "4"
            # "4" -> None
            parts = section_number.split('.')

            if len(parts) > 1:
                parent_number = '.'.join(parts[:-1])
                section["parent_number"] = parent_number
            else:
                section["parent_number"] = None

        return sections

    def _detect_sections(self, text: str, page_num: int) -> list[Dict[str, Any]]:
        """
        Detect document sections (PARTIE, Article, numbered sections).

        Args:
            text: Page text
            page_num: Page number

        Returns:
            List of detected sections with type, number, title, level
        """
        sections = []

        # Patterns de détection (ordre important: du plus spécifique au plus général)
        PATTERNS = [
            # PARTIE 1 – Titre
            (r'^PARTIE\s+([IVX\d]+)\s*[–-]\s*(.+)$', 'PART', 1),
            # Article 1 – Titre
            (r'^Article\s+(\d+)\s*[–-]\s*(.+)$', 'ARTICLE', 2),
            # 3.1.2 Titre (numérotation hiérarchique)
            (r'^(\d+(?:\.\d+)+)\s+(.+)$', 'SECTION', 3),
            # 1. Titre (liste numérotée niveau 1)
            (r'^(\d+)\.\s+([A-ZÀÂÄÆÇÉÈÊËÏÎÔŒÙÛÜ].+)$', 'NUMBERED_ITEM', 4),
        ]

        lines = text.split('\n')

        for line_num, line in enumerate(lines):
            line_stripped = line.strip()

            # Skip empty lines or very short lines
            if len(line_stripped) < 3:
                continue

            for pattern, section_type, level in PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE | re.MULTILINE)
                if match:
                    sections.append({
                        "type": section_type,
                        "number": match.group(1),
                        "title": match.group(2).strip() if len(match.groups()) > 1 else "",
                        "level": level,
                        "page": page_num,
                        "line": line_num,
                        "content": line_stripped,  # Will be enriched later
                        "start_line": line_num
                    })
                    break  # Stop at first match

        return sections


    async def _extract_with_ocr(self, pdf_file: io.BytesIO) -> str:
        """Extract text using OCR for scanned PDFs."""
        try:
            # TODO: Implement OCR extraction
            # Would require pdf2image and pytesseract
            return "OCR extraction not yet implemented"
        except Exception as e:
            print(f"OCR extraction error: {e}")
            return ""

    async def _extract_metadata(self, pdf_file: io.BytesIO) -> Dict[str, Any]:
        """Extract PDF metadata."""
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            metadata = reader.metadata or {}

            return {
                "page_count": len(reader.pages),
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "producer": metadata.get("/Producer", ""),
                "creation_date": metadata.get("/CreationDate", ""),
            }
        except Exception as e:
            print(f"Metadata extraction error: {e}")
            return {}

    async def _extract_structured_info(self, text: str) -> Dict[str, Any]:
        """
        Extract structured information from text.

        Args:
            text: Extracted text content

        Returns:
            Structured data (deadlines, reference numbers, etc.)
        """
        structured = {
            "reference_numbers": self._extract_reference_numbers(text),
            "deadlines": self._extract_deadlines(text),
            "organizations": self._extract_organizations(text),
            "email_addresses": self._extract_emails(text),
            "phone_numbers": self._extract_phones(text),
        }

        return structured

    async def _extract_structured_info_enhanced(
        self,
        text: str,
        tables: list[Dict[str, Any]],
        sections: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Enhanced structured information extraction with tables and sections context.

        Args:
            text: Extracted text
            tables: Structured tables
            sections: Detected sections

        Returns:
            Enhanced structured data with section context
        """
        # Basic extraction
        basic_info = {
            "reference_numbers": self._extract_reference_numbers(text),
            "deadlines": self._extract_deadlines(text),
            "organizations": self._extract_organizations(text),
            "email_addresses": self._extract_emails(text),
            "phone_numbers": self._extract_phones(text),
        }

        # Enhanced with sections context
        enhanced_info = {
            **basic_info,
            "section_summary": {
                "total_sections": len(sections),
                "parts": len([s for s in sections if s["type"] == "PART"]),
                "articles": len([s for s in sections if s["type"] == "ARTICLE"]),
                "subsections": len([s for s in sections if s["type"] == "SECTION"]),
            },
            "table_summary": {
                "total_tables": len(tables),
                "total_rows": sum(t["row_count"] for t in tables),
                "tables_by_page": self._group_tables_by_page(tables),
            },
            "key_sections": self._identify_key_sections(sections),
        }

        return enhanced_info

    def _group_tables_by_page(self, tables: list[Dict]) -> Dict[int, int]:
        """Group tables by page number."""
        by_page = {}
        for table in tables:
            page = table.get("page", 0)
            by_page[page] = by_page.get(page, 0) + 1
        return by_page

    def _identify_key_sections(self, sections: list[Dict]) -> Dict[str, Any]:
        """
        Identify key sections like exclusions, deadlines, conditions.

        Args:
            sections: List of detected sections

        Returns:
            Dictionary of key sections with their locations
        """
        key_sections = {
            "exclusions": [],
            "obligations": [],
            "conditions": [],
            "evaluation_criteria": [],
        }

        # Keywords for detection
        EXCLUSION_KEYWORDS = ["exclus", "exclu", "ne comprend pas", "hors périmètre", "ne fait pas partie"]
        OBLIGATION_KEYWORDS = ["obligatoire", "doit", "devra", "impératif", "exigé", "requis"]
        CONDITION_KEYWORDS = ["si", "sous réserve", "condition", "dans le cas"]
        CRITERIA_KEYWORDS = ["critère", "notation", "évaluation", "pondération", "barème"]

        for section in sections:
            content_lower = section.get("content", "").lower()
            title_lower = section.get("title", "").lower()
            combined = content_lower + " " + title_lower

            # Check for exclusions
            if any(kw in combined for kw in EXCLUSION_KEYWORDS):
                key_sections["exclusions"].append({
                    "section_id": section.get("number"),
                    "title": section.get("title"),
                    "page": section.get("page"),
                    "type": section.get("type")
                })

            # Check for obligations
            if any(kw in combined for kw in OBLIGATION_KEYWORDS):
                key_sections["obligations"].append({
                    "section_id": section.get("number"),
                    "title": section.get("title"),
                    "page": section.get("page"),
                    "type": section.get("type")
                })

            # Check for conditions
            if any(kw in combined for kw in CONDITION_KEYWORDS):
                key_sections["conditions"].append({
                    "section_id": section.get("number"),
                    "title": section.get("title"),
                    "page": section.get("page"),
                    "type": section.get("type")
                })

            # Check for evaluation criteria
            if any(kw in combined for kw in CRITERIA_KEYWORDS):
                key_sections["evaluation_criteria"].append({
                    "section_id": section.get("number"),
                    "title": section.get("title"),
                    "page": section.get("page"),
                    "type": section.get("type")
                })

        return key_sections

    def _extract_reference_numbers(self, text: str) -> list[str]:
        """Extract tender reference numbers."""
        # Common French tender reference patterns
        patterns = [
            r'\b\d{4}[-/]\d{2,4}[-/]\w+\b',  # 2024/123/AO
            r'\bAO[-/]?\d{4}[-/]?\d+\b',      # AO-2024-123
            r'\bMarché\s+n°\s*[\w-]+\b',      # Marché n° 2024-123
        ]

        references = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            references.extend(matches)

        return list(set(references))

    def _extract_deadlines(self, text: str) -> list[Dict[str, str]]:
        """Extract deadline dates."""
        # Common French date patterns
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        deadline_keywords = [
            "date limite",
            "avant le",
            "échéance",
            "remise des offres",
            "dépôt des candidatures"
        ]

        deadlines = []
        lines = text.split("\n")

        for line in lines:
            line_lower = line.lower()
            for keyword in deadline_keywords:
                if keyword in line_lower:
                    dates = re.findall(date_pattern, line)
                    for date in dates:
                        deadlines.append({
                            "date": date,
                            "context": line.strip()[:100]
                        })

        return deadlines

    def _extract_organizations(self, text: str) -> list[str]:
        """Extract organization names."""
        # TODO: Implement NER or pattern matching for organizations
        return []

    def _extract_emails(self, text: str) -> list[str]:
        """Extract email addresses."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return list(set(emails))

    def _extract_phones(self, text: str) -> list[str]:
        """Extract phone numbers."""
        # French phone number patterns
        phone_pattern = r'\b(?:0|\+33)[1-9](?:[\s.-]?\d{2}){4}\b'
        phones = re.findall(phone_pattern, text)
        return list(set(phones))

    def _format_table(self, table: list) -> str:
        """Format extracted table as text."""
        if not table:
            return ""

        formatted_rows = []
        for row in table:
            if row:
                formatted_row = " | ".join([str(cell) if cell else "" for cell in row])
                formatted_rows.append(formatted_row)

        return "\n".join(formatted_rows)

    # ========== SYNCHRONOUS METHODS FOR CELERY TASKS ==========

    def extract_from_pdf_sync(
        self,
        file_content: bytes,
        use_ocr: bool = False
    ) -> Dict[str, Any]:
        """
        Extract text and metadata from PDF with enhanced structure (sync version for Celery tasks).

        Args:
            file_content: PDF file content as bytes
            use_ocr: Whether to use OCR for scanned PDFs

        Returns:
            Extracted content and metadata including tables and sections
        """
        pdf_file = io.BytesIO(file_content)

        # IMPROVED: Use pdfplumber for better extraction
        extraction = self._extract_with_pdfplumber_enhanced_sync(pdf_file)

        # If no text found, try OCR
        if not extraction["text"].strip() and use_ocr:
            pdf_file.seek(0)
            extraction["text"] = self._extract_with_ocr_sync(pdf_file)

        # Extract metadata
        pdf_file.seek(0)
        metadata = self._extract_metadata_sync(pdf_file)

        # Extract structured information (ENHANCED)
        structured_data = self._extract_structured_info_enhanced_sync(
            extraction["text"],
            extraction["tables"],
            extraction["sections"]
        )

        return {
            "text": extraction["text"],
            "tables": extraction["tables"],  # NEW: structured tables
            "sections": extraction["sections"],  # NEW: detected sections
            "metadata": metadata,
            "structured": structured_data,
            "page_count": metadata.get("page_count", 0),
            "extraction_method": "pdfplumber_enhanced"
        }

    def _extract_text_pypdf2_sync(self, pdf_file: io.BytesIO) -> str:
        """Extract text using PyPDF2 (sync)."""
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            text_parts = []

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            return "\n\n".join(text_parts)
        except Exception as e:
            print(f"PyPDF2 extraction error: {e}")
            return ""

    def _extract_with_ocr_sync(self, pdf_file: io.BytesIO) -> str:
        """Extract text using OCR for scanned PDFs (sync)."""
        try:
            # TODO: Implement OCR extraction
            # Would require pdf2image and pytesseract
            return "OCR extraction not yet implemented"
        except Exception as e:
            print(f"OCR extraction error: {e}")
            return ""

    def _extract_metadata_sync(self, pdf_file: io.BytesIO) -> Dict[str, Any]:
        """Extract PDF metadata (sync)."""
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            metadata = reader.metadata or {}

            return {
                "page_count": len(reader.pages),
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "producer": metadata.get("/Producer", ""),
                "creation_date": metadata.get("/CreationDate", ""),
            }
        except Exception as e:
            print(f"Metadata extraction error: {e}")
            return {}

    def _extract_structured_info_sync(self, text: str) -> Dict[str, Any]:
        """
        Extract structured information from text (sync).

        Args:
            text: Extracted text content

        Returns:
            Structured data (deadlines, reference numbers, etc.)
        """
        structured = {
            "reference_numbers": self._extract_reference_numbers(text),
            "deadlines": self._extract_deadlines(text),
            "organizations": self._extract_organizations(text),
            "email_addresses": self._extract_emails(text),
            "phone_numbers": self._extract_phones(text),
        }

        return structured

    def _extract_with_pdfplumber_enhanced_sync(
        self,
        pdf_file: io.BytesIO
    ) -> Dict[str, Any]:
        """
        Enhanced extraction with pdfplumber (sync version for Celery) with full section content.

        Returns:
            {
                "text": str,
                "tables": List[Dict],
                "sections": List[Dict]  # With full content
            }
        """
        try:
            text_parts = []
            tables = []
            sections = []
            pages_text = {}  # Store text by page for content extraction

            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                        pages_text[page_num] = page_text

                        # Detect sections in text
                        detected_sections = self._detect_sections(page_text, page_num)
                        sections.extend(detected_sections)

                    # Extract tables as STRUCTURED data
                    page_tables = page.extract_tables()
                    for table_idx, table_data in enumerate(page_tables):
                        if table_data and len(table_data) > 0:
                            # Clean empty cells
                            cleaned_table = [
                                [cell.strip() if cell else "" for cell in row]
                                for row in table_data
                            ]

                            # Skip empty tables
                            if any(any(cell for cell in row) for row in cleaned_table):
                                structured_table = {
                                    "id": f"table_p{page_num}_{table_idx}",
                                    "page": page_num,
                                    "headers": cleaned_table[0] if len(cleaned_table) > 0 else [],
                                    "rows": cleaned_table[1:] if len(cleaned_table) > 1 else [],
                                    "row_count": len(cleaned_table) - 1,
                                    "col_count": len(cleaned_table[0]) if cleaned_table else 0
                                }
                                tables.append(structured_table)

            # IMPROVED: Extract full content for sections
            sections = self._extract_section_content_from_pages(sections, pages_text)

            # Build parent-child hierarchy
            sections = self._build_section_hierarchy(sections)

            return {
                "text": "\n\n".join(text_parts),
                "tables": tables,
                "sections": sections
            }
        except Exception as e:
            print(f"Enhanced pdfplumber extraction error (sync): {e}")
            return {
                "text": "",
                "tables": [],
                "sections": []
            }

    def _extract_structured_info_enhanced_sync(
        self,
        text: str,
        tables: list[Dict[str, Any]],
        sections: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Enhanced structured information extraction (sync version for Celery).

        Args:
            text: Extracted text
            tables: Structured tables
            sections: Detected sections

        Returns:
            Enhanced structured data with section context
        """
        # Basic extraction
        basic_info = {
            "reference_numbers": self._extract_reference_numbers(text),
            "deadlines": self._extract_deadlines(text),
            "organizations": self._extract_organizations(text),
            "email_addresses": self._extract_emails(text),
            "phone_numbers": self._extract_phones(text),
        }

        # Enhanced with sections context
        enhanced_info = {
            **basic_info,
            "section_summary": {
                "total_sections": len(sections),
                "parts": len([s for s in sections if s["type"] == "PART"]),
                "articles": len([s for s in sections if s["type"] == "ARTICLE"]),
                "subsections": len([s for s in sections if s["type"] == "SECTION"]),
            },
            "table_summary": {
                "total_tables": len(tables),
                "total_rows": sum(t["row_count"] for t in tables),
                "tables_by_page": self._group_tables_by_page(tables),
            },
            "key_sections": self._identify_key_sections(sections),
        }

        return enhanced_info


# Global instance
parser_service = ParserService()
