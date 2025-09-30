"""
Pydantic schemas for Tender entities.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field


class TenderBase(BaseModel):
    """Base tender schema."""
    title: str = Field(..., max_length=500)
    organization: Optional[str] = Field(None, max_length=200)
    reference_number: Optional[str] = Field(None, max_length=100)
    deadline: Optional[datetime] = None
    source: Optional[str] = None


class TenderCreate(TenderBase):
    """Schema for creating a tender."""
    raw_content: Optional[str] = None


class TenderResponse(TenderBase):
    """Schema for tender responses."""
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    message: Optional[str] = None

    class Config:
        from_attributes = True


class TenderList(BaseModel):
    """Simplified tender schema for listing."""
    id: UUID
    title: str
    organization: Optional[str]
    deadline: Optional[datetime]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
