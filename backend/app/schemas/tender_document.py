"""
Pydantic schemas for Tender Documents.
"""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TenderDocumentBase(BaseModel):
    """Base schema for tender documents."""
    document_type: str = Field(..., description="Type of document: CCTP, CCAP, RC, AE, BPU, DUME, ANNEXE")


class TenderDocumentUpload(TenderDocumentBase):
    """Schema for uploading a document."""
    pass


class TenderDocumentResponse(TenderDocumentBase):
    """Schema for tender document responses."""
    id: UUID
    tender_id: UUID
    filename: str
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    extraction_status: str
    page_count: Optional[int]
    uploaded_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class TenderDocumentWithContent(TenderDocumentResponse):
    """Schema with extracted text content."""
    extracted_text: Optional[str]
    extraction_method: Optional[str]
    extraction_meta_data: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True
