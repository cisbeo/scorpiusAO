"""
Pydantic schemas for BOAMP API endpoints.
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, UUID4


class BOAMPPublicationBase(BaseModel):
    """Base schema for BOAMP publication"""
    boamp_id: str
    title: str
    organization: Optional[str] = None
    publication_date: date
    deadline: Optional[date] = None
    type_annonce: Optional[str] = None
    montant: Optional[float] = None
    lieu_execution: Optional[str] = None
    cpv_codes: List[str] = Field(default_factory=list)
    descripteurs: List[str] = Field(default_factory=list)


class BOAMPPublicationCreate(BOAMPPublicationBase):
    """Schema for creating a BOAMP publication"""
    raw_data: dict


class BOAMPPublicationResponse(BOAMPPublicationBase):
    """Schema for BOAMP publication API response"""
    id: UUID4
    status: str
    matched_tender_id: Optional[UUID4] = None
    imported_at: Optional[datetime] = None
    created_at: datetime
    days_until_deadline: Optional[int] = None

    class Config:
        from_attributes = True


class BOAMPPublicationList(BaseModel):
    """Paginated list of BOAMP publications"""
    items: List[BOAMPPublicationResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class BOAMPSyncRequest(BaseModel):
    """Request schema for manual BOAMP sync"""
    days_back: int = Field(default=7, ge=1, le=30, description="Number of days to look back")
    limit: int = Field(default=100, ge=1, le=500, description="Maximum number of records to fetch")
    force: bool = Field(default=False, description="Force sync even if recently completed")


class BOAMPSyncResponse(BaseModel):
    """Response schema for BOAMP sync"""
    status: str
    task_id: Optional[str] = None
    fetched: Optional[int] = None
    filtered: Optional[int] = None
    saved: Optional[int] = None
    duplicates: Optional[int] = None
    message: Optional[str] = None


class BOAMPImportRequest(BaseModel):
    """Request schema for importing BOAMP publication as Tender"""
    pass  # Empty body, just trigger


class BOAMPImportResponse(BaseModel):
    """Response schema for BOAMP import"""
    status: str
    task_id: Optional[str] = None
    tender_id: Optional[UUID4] = None
    message: Optional[str] = None


class BOAMPStatsResponse(BaseModel):
    """Statistics about BOAMP publications"""
    total_publications: int
    new_count: int
    imported_count: int
    ignored_count: int
    error_count: int
    publications_last_24h: int
    publications_last_7d: int
    avg_days_to_deadline: Optional[float] = None
    total_montant: Optional[float] = None
