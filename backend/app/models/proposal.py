"""
SQLAlchemy models for Proposal entities.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class Proposal(Base):
    """Proposal model representing a tender response."""

    __tablename__ = "proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    sections = Column(JSON, default={})
    compliance_score = Column(String(10))
    status = Column(String(50), default="draft", index=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    #     tender = relationship("Tender", back_populates="proposals")

    def __repr__(self):
        return f"<Proposal {self.id} for Tender {self.tender_id}>"
