"""
SQLAlchemy models for Tender entities.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class Tender(Base):
    """Tender model representing an appel d'offre."""

    __tablename__ = "tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(500), nullable=False, index=True)
    organization = Column(String(200), index=True)
    reference_number = Column(String(100), index=True)
    deadline = Column(DateTime(timezone=True))
    raw_content = Column(Text)
    parsed_content = Column(JSON)
    status = Column(String(50), default="new", index=True)
    source = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    #     # proposals = relationship("Proposal", back_populates="tender", cascade="all, delete-orphan")  # Not yet implemented
    #     # criteria = relationship("TenderCriterion", back_populates="tender", cascade="all, delete-orphan")
    #     # documents = relationship("TenderDocument", back_populates="tender", cascade="all, delete-orphan")
    #     # analysis = relationship("TenderAnalysis", back_populates="tender", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tender {self.title[:50]}>"


class TenderCriterion(Base):
    """Evaluation criteria extracted from tender."""

    __tablename__ = "tender_criteria"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False, index=True)
    criterion_type = Column(String(50))
    description = Column(Text)
    weight = Column(String(20))  # Store as string to handle percentages
    is_mandatory = Column(String(10), default="false")
    meta_data = Column(JSON)

    # Relationships
    #     # tender = relationship("Tender", back_populates="criteria")
    #     # suggestions = relationship("CriterionSuggestion", back_populates="criterion", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TenderCriterion {self.criterion_type}>"
