"""
Pydantic schemas for Tender Analysis.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class AnalysisDeadline(BaseModel):
    """Deadline information."""
    type: str  # submission, questions, visit, etc.
    date: str
    description: Optional[str]


class TenderAnalysisResponse(BaseModel):
    """Schema for tender analysis results."""
    id: UUID
    tender_id: UUID
    summary: Optional[str]
    key_requirements: Optional[List[str]]
    deadlines: Optional[List[Dict[str, Any]]]
    risks: Optional[List[str]]
    mandatory_documents: Optional[List[str]]
    complexity_level: Optional[str]
    recommendations: Optional[List[str]]
    structured_data: Optional[Dict[str, Any]]
    analysis_status: str
    processing_time_seconds: Optional[int]
    analyzed_at: Optional[datetime]

    class Config:
        from_attributes = True


class AnalysisStatusResponse(BaseModel):
    """Schema for analysis status tracking."""
    tender_id: UUID
    status: str  # pending, processing, completed, failed
    current_step: Optional[str]
    progress: int  # 0-100
    steps_completed: List[Dict[str, Any]]
    estimated_time_remaining: Optional[str]
    error_message: Optional[str]
