"""
SQLAlchemy model for Past Proposals (winning tender responses).
"""
from datetime import datetime, date
from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, Date, DateTime, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class PastProposal(Base):
    """Past tender responses (won/lost) stored for reuse"""

    __tablename__ = "past_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kb_document_id = Column(UUID(as_uuid=True), ForeignKey('kb_documents.id', ondelete='CASCADE'), nullable=False)

    # Tender information
    tender_title = Column(String(500), nullable=False)
    organization = Column(String(200), nullable=False)
    submission_date = Column(Date, nullable=False, index=True)

    # Results
    result = Column(String(20), nullable=False, index=True)
    our_rank = Column(Integer)
    total_candidates = Column(Integer)
    our_score = Column(Numeric(5, 2))
    winner_score = Column(Numeric(5, 2))
    contract_value = Column(Numeric(15, 2))

    # Content structure
    sections = Column(JSONB, default=[])
    criteria_responses = Column(JSONB, default=[])

    # Analysis
    winning_factors = Column(Text)
    lessons_learned = Column(Text)
    reusable_sections = Column(JSONB, default=[])

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Bidirectional link to historical tender
    historical_tender_id = Column(UUID(as_uuid=True), ForeignKey('historical_tenders.id', ondelete='SET NULL'))

    # Relationships
    kb_document = relationship("KBDocument", back_populates="past_proposal")
    historical_tender = relationship("HistoricalTender", foreign_keys=[historical_tender_id], back_populates="our_proposal")

    __table_args__ = (
        CheckConstraint(
            "result IN ('won', 'lost', 'abandoned')",
            name="check_result"
        ),
    )

    def __repr__(self):
        return f"<PastProposal {self.result} '{self.tender_title[:50]}'>"
