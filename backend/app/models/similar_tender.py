"""
SQLAlchemy models for Similar Tenders.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class SimilarTender(Base):
    """Similar past tenders found via RAG similarity search"""

    __tablename__ = "similar_tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False, index=True)
    similar_tender_id = Column(UUID(as_uuid=True), ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False, index=True)

    # Similarity metrics
    similarity_score = Column(Float, nullable=False)
    was_won = Column(Boolean)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    tender = relationship("Tender", foreign_keys=[tender_id], backref="similar_tenders_found")
    similar_to = relationship("Tender", foreign_keys=[similar_tender_id])

    def __repr__(self):
        return f"<SimilarTender {self.tender_id} → {self.similar_tender_id} (score={self.similarity_score:.2f})>"
