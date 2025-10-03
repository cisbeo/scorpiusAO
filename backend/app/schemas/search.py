"""
Pydantic schemas for Search operations.
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Schema for search requests."""
    query: str = Field(..., min_length=3, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)
    document_types: List[str] | None = None
    filters: Dict[str, Any] = {}


class SearchResult(BaseModel):
    """Schema for a single search result."""
    document_id: str
    document_type: str
    chunk_text: str
    similarity_score: float
    metadata: Dict[str, Any] = {}


class SearchResponse(BaseModel):
    """Schema for search response."""
    query: str
    results: List[SearchResult]
    total: int


class TenderQuestionRequest(BaseModel):
    """Schema for tender Q&A request."""
    question: str = Field(..., min_length=5, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class TenderQuestionResponse(BaseModel):
    """Schema for tender Q&A response."""
    question: str
    answer: str
    sources: List[SearchResult]
    confidence: float = Field(..., ge=0, le=1)
    cached: bool = False
