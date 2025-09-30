"""
Pydantic schemas for Proposal entities.
"""
from datetime import datetime
from uuid import UUID
from typing import Dict, Any
from pydantic import BaseModel


class ProposalBase(BaseModel):
    """Base proposal schema."""
    tender_id: UUID
    user_id: UUID


class ProposalCreate(ProposalBase):
    """Schema for creating a proposal."""
    sections: Dict[str, Any] = {}


class ProposalResponse(ProposalBase):
    """Schema for proposal responses."""
    id: UUID
    sections: Dict[str, Any]
    compliance_score: float | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SectionGenerateRequest(BaseModel):
    """Schema for section generation request."""
    section_type: str
    context: Dict[str, Any] = {}
    max_tokens: int = 2000
