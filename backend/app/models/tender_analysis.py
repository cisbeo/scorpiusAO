"""
SQLAlchemy models for Tender Analysis results.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class TenderAnalysis(Base):
    """AI analysis results for a tender"""

    __tablename__ = "tender_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)

    # Global analysis
    summary = Column(Text)
    key_requirements = Column(JSON)  # List of strings
    deadlines = Column(JSON)  # List of {type, date, description}
    risks = Column(JSON)  # List of strings
    mandatory_documents = Column(JSON)  # List of strings
    complexity_level = Column(String(20))  # faible, moyenne, élevée
    recommendations = Column(JSON)  # List of strings

    # Structured data extracted
    structured_data = Column(JSON)  # Technical specs, budget, contacts, etc.

    # Processing metadata
    analysis_status = Column(String(50), default="pending", index=True)  # pending, processing, completed, failed
    processing_time_seconds = Column(Integer)
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    analyzed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    #     tender = relationship("Tender", back_populates="analysis")

    def __repr__(self):
        return f"<TenderAnalysis tender_id={self.tender_id} status={self.analysis_status}>"
