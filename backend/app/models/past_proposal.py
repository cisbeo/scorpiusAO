"""
SQLAlchemy model for Past Proposals.

A PastProposal represents our company's submitted proposal for a historical tender.
It stores the proposal content, our score, rank, and lessons learned for future
use in RAG Knowledge Base.

Relationship: Many PastProposals → One HistoricalTender
"""
from datetime import datetime
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import Column, String, Text, Integer, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from sqlalchemy.orm import relationship

from app.models.base import Base


class PastProposal(Base):
    """
    Past Proposal model for archived winning/losing proposals.

    Stores our company's proposal for a historical tender.
    Used for RAG Knowledge Base to retrieve winning proposal sections
    and generate similar responses for new tenders.
    """

    __tablename__ = "past_proposals"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique identifier for past proposal"
    )

    # Foreign Key to HistoricalTender
    historical_tender_id = Column(
        UUID(as_uuid=True),
        ForeignKey("historical_tenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the historical tender"
    )

    # Company Information (for multi-tenancy support)
    our_company_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Our company ID (for multi-tenancy if needed)"
    )

    our_company_name = Column(
        String(200),
        default="ScorpiusAO Client",
        comment="Our company name at time of proposal"
    )

    # Proposal Status
    status = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Status: 'won', 'lost', 'shortlisted', 'withdrawn'"
    )

    # Scores and Ranking
    score_obtained = Column(
        Numeric(5, 2),
        comment="Final score obtained (e.g., 85.50 out of 100)"
    )

    max_score = Column(
        Numeric(5, 2),
        default=Decimal("100.00"),
        comment="Maximum possible score (usually 100.00)"
    )

    rank = Column(
        Integer,
        comment="Rank among all bidders (1 = winner, 2 = runner-up, etc.)"
    )

    total_bidders = Column(
        Integer,
        comment="Total number of bidders for this tender"
    )

    # Proposal Content (from original Proposal model)
    sections = Column(
        JSON,
        nullable=False,
        default={},
        comment="Complete proposal sections (same structure as Proposal.sections)"
    )

    # Post-Mortem Analysis (manually filled by bid manager)
    lessons_learned = Column(
        Text,
        comment="Lessons learned from this proposal (what worked, what didn't)"
    )

    win_factors = Column(
        ARRAY(String),
        default=[],
        comment="Key factors that contributed to win/loss (e.g., ['price_competitive', 'strong_references', 'weak_technical_memo'])"
    )

    improvement_areas = Column(
        ARRAY(String),
        default=[],
        comment="Areas for improvement identified in post-mortem"
    )

    # Financial Information
    proposed_amount = Column(
        Numeric(12, 2),
        comment="Total amount proposed in our bid (EUR)"
    )

    winning_amount = Column(
        Numeric(12, 2),
        comment="Winning bid amount (if we lost, to track competition)"
    )

    # Metadata - renamed to avoid SQLAlchemy reserved word
    meta_data = Column(
        JSON,
        default={},
        comment="Stores original_proposal_id, evaluator_comments, etc."
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    historical_tender = relationship(
        "HistoricalTender",
        back_populates="past_proposals"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            'historical_tender_id',
            'our_company_id',
            name='uq_past_proposal_tender_company'
        ),
    )

    def __repr__(self):
        return f"<PastProposal {self.status} for HistoricalTender {self.historical_tender_id}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "historical_tender_id": str(self.historical_tender_id),
            "our_company_id": str(self.our_company_id),
            "our_company_name": self.our_company_name,
            "status": self.status,
            "score_obtained": float(self.score_obtained) if self.score_obtained else None,
            "max_score": float(self.max_score) if self.max_score else None,
            "rank": self.rank,
            "total_bidders": self.total_bidders,
            "lessons_learned": self.lessons_learned,
            "win_factors": self.win_factors,
            "improvement_areas": self.improvement_areas,
            "proposed_amount": float(self.proposed_amount) if self.proposed_amount else None,
            "winning_amount": float(self.winning_amount) if self.winning_amount else None,
            "sections_count": len(self.sections) if self.sections else 0,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @property
    def win_rate_percentage(self):
        """Calculate win rate percentage (for display)."""
        if not self.score_obtained or not self.max_score:
            return None
        return float((self.score_obtained / self.max_score) * 100)

    @property
    def is_winning_proposal(self):
        """Check if this was a winning proposal."""
        return self.status == "won" or self.rank == 1
