"""
SQLAlchemy model for Historical Tenders (past opportunities).
"""
from datetime import datetime, date
from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, Date, DateTime, Numeric, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class HistoricalTender(Base):
    """Historical tenders (both won and lost) for learning and analysis"""

    __tablename__ = "historical_tenders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kb_document_id = Column(UUID(as_uuid=True), ForeignKey('kb_documents.id', ondelete='SET NULL'))

    # Tender information
    title = Column(String(500), nullable=False)
    organization = Column(String(200), nullable=False)
    organization_type = Column(String(100))
    reference_number = Column(String(100))
    publication_date = Column(Date)
    deadline = Column(Date, nullable=False)

    # Context
    sector = Column(String(100), index=True)
    geographic_zone = Column(String(200))

    # Scope
    estimated_users = Column(Integer)
    estimated_sites = Column(Integer)
    estimated_budget = Column(Numeric(15, 2))

    # Requirements
    services = Column(JSONB, default=[])
    evaluation_criteria = Column(JSONB)
    mandatory_certifications = Column(JSONB, default=[])

    # Our participation
    participated = Column(Boolean, default=True)
    result = Column(String(20), index=True)
    our_rank = Column(Integer)
    total_candidates = Column(Integer)
    our_score = Column(Numeric(5, 2))
    winner_score = Column(Numeric(5, 2))

    # Link to our response
    our_proposal_id = Column(UUID(as_uuid=True), ForeignKey('past_proposals.id', ondelete='SET NULL'))

    # Analysis
    lessons_learned = Column(Text)
    competitive_analysis = Column(Text)
    difficulty_level = Column(String(20))

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    kb_document = relationship("KBDocument", back_populates="historical_tender")
    our_proposal = relationship("PastProposal", foreign_keys=[our_proposal_id], back_populates="historical_tender")

    __table_args__ = (
        CheckConstraint(
            "result IN ('won', 'lost', 'abandoned', 'disqualified', 'not_submitted')",
            name="check_historical_result"
        ),
        CheckConstraint(
            "difficulty_level IN ('low', 'medium', 'high', 'very_high')",
            name="check_difficulty_level"
        ),
    )

    def __repr__(self):
        return f"<HistoricalTender {self.result or 'N/A'}: {self.title[:50]}>"
