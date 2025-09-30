"""
Pydantic schemas for Analysis results.
"""
from typing import List, Dict, Any
from uuid import UUID
from pydantic import BaseModel


class CriterionResponse(BaseModel):
    """Schema for a single evaluation criterion."""
    id: UUID
    criterion_type: str
    description: str
    weight: float
    is_mandatory: bool
    metadata: Dict[str, Any] = {}


class AnalysisResponse(BaseModel):
    """Schema for tender analysis results."""
    tender_id: UUID
    summary: str
    key_requirements: List[str]
    deadlines: List[Dict[str, Any]]
    risks: List[str]
    mandatory_documents: List[str]
    estimated_complexity: str
    recommendations: List[str]


class CriteriaExtractionResponse(BaseModel):
    """Schema for extracted criteria."""
    tender_id: UUID
    criteria: List[CriterionResponse]
    total_weight: float
