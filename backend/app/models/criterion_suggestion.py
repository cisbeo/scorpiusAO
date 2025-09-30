"""
SQLAlchemy models for Criterion Suggestions.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class CriterionSuggestion(Base):
    """Content suggestions for tender response criteria"""

    __tablename__ = "criterion_suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    criterion_id = Column(UUID(as_uuid=True), ForeignKey('tender_criteria.id', ondelete='CASCADE'), nullable=False, index=True)

    # Source information
    source_type = Column(String(50), index=True)  # past_proposal, certification, reference, case_study, documentation
    source_id = Column(UUID(as_uuid=True))
    source_document = Column(String(255))

    # Suggested content
    suggested_text = Column(Text, nullable=False)
    relevance_score = Column(Float, nullable=False)

    # Additional metadata
    modifications_needed = Column(Text)
    context = Column(JSON)  # Additional context about why this is relevant

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    #     criterion = relationship("TenderCriterion", back_populates="suggestions")

    def __repr__(self):
        return f"<CriterionSuggestion criterion={self.criterion_id} score={self.relevance_score:.2f}>"
