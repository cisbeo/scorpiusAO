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

    async def extract_from_pdf(
        self,
        file_content: bytes,
        use_ocr: bool = False
    ) -> Dict[str, Any]:
        """
        Extract text and metadata from PDF.

        Args:
            file_content: PDF file content as bytes
            use_ocr: Whether to use OCR for scanned PDFs

        Returns:
            Extracted content and metadata
        """
        pdf_file = io.BytesIO(file_content)

        # Try text extraction first
        text = await self._extract_text_pypdf2(pdf_file)

        # If no text found, try OCR
        if not text.strip() and use_ocr:
            pdf_file.seek(0)
            text = await self._extract_with_ocr(pdf_file)

        # Extract metadata
        pdf_file.seek(0)
        metadata = await self._extract_metadata(pdf_file)

        # Extract structured information
        structured_data = await self._extract_structured_info(text)

        return {
            "text": text,
            "metadata": metadata,
            "structured": structured_data,
            "page_count": metadata.get("page_count", 0),
            "extraction_method": "ocr" if use_ocr else "text"
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
        Extract text and metadata from PDF (sync version for Celery tasks).

        Args:
            file_content: PDF file content as bytes
            use_ocr: Whether to use OCR for scanned PDFs

        Returns:
            Extracted content and metadata
        """
        pdf_file = io.BytesIO(file_content)

        # Try text extraction first
        text = self._extract_text_pypdf2_sync(pdf_file)

        # If no text found, try OCR
        if not text.strip() and use_ocr:
            pdf_file.seek(0)
            text = self._extract_with_ocr_sync(pdf_file)

        # Extract metadata
        pdf_file.seek(0)
        metadata = self._extract_metadata_sync(pdf_file)

        # Extract structured information
        structured_data = self._extract_structured_info_sync(text)

        return {
            "text": text,
            "metadata": metadata,
            "structured": structured_data,
            "page_count": metadata.get("page_count", 0),
            "extraction_method": "ocr" if use_ocr else "text"
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


# Global instance
parser_service = ParserService()
