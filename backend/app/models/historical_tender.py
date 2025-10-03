"""
SQLAlchemy model for Historical Tenders.

A HistoricalTender represents an archived tender (appel d'offre) that has been
completed and awarded. It stores metadata about the tender and links to our
past proposal(s) for that tender.

Relationship: One HistoricalTender → Many PastProposals
(One tender can have multiple proposals from different companies,
but we only store OUR company's proposal(s))
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, Date, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base


class HistoricalTender(Base):
    """
    Historical Tender model for archived tenders.

    Stores tenders that have been completed, evaluated, and awarded.
    Used for RAG Knowledge Base to retrieve similar past tenders
    and winning proposal patterns.
    """

    __tablename__ = "historical_tenders"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique identifier for historical tender"
    )

    # Tender Information (from original Tender model)
    title = Column(
        String(500),
        nullable=False,
        index=True,
        comment="Title of the tender (e.g., 'Infogérance infrastructure IT')"
    )

    organization = Column(
        String(200),
        index=True,
        comment="Organization that published the tender (e.g., 'Vallée Sud Grand Paris')"
    )

    reference_number = Column(
        String(100),
        unique=True,
        index=True,
        comment="Official tender reference number (e.g., '25TIC06')"
    )

    # Dates
    publication_date = Column(
        Date,
        comment="Date when tender was published on BOAMP/AWS PLACE"
    )

    deadline = Column(
        Date,
        comment="Deadline for proposal submission"
    )

    award_date = Column(
        Date,
        index=True,
        comment="Date when tender was awarded to winner"
    )

    # Award Information
    total_amount = Column(
        Numeric(12, 2),
        comment="Total contract amount in EUR (e.g., 500000.00 for 500k€)"
    )

    winner_company = Column(
        String(200),
        comment="Name of company that won the tender (if not us)"
    )

    status = Column(
        String(50),
        default="awarded",
        index=True,
        comment="Status: 'awarded', 'cancelled', 'deserted'"
    )

    # Archive Information
    archived_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        index=True,
        comment="Timestamp when tender was archived"
    )

    archived_by = Column(
        UUID(as_uuid=True),
        comment="User ID who archived this tender"
    )

    # Metadata (stores original tender data) - renamed to avoid SQLAlchemy reserved word
    meta_data = Column(
        JSON,
        default={},
        comment="Stores original_tender_id, raw_content, parsed_content, etc."
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
    past_proposals = relationship(
        "PastProposal",
        back_populates="historical_tender",
        cascade="all, delete-orphan",
        lazy="selectin"  # Eager load proposals when querying tenders
    )

    def __repr__(self):
        return f"<HistoricalTender {self.reference_number}: {self.title[:50]}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "title": self.title,
            "organization": self.organization,
            "reference_number": self.reference_number,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "award_date": self.award_date.isoformat() if self.award_date else None,
            "total_amount": float(self.total_amount) if self.total_amount else None,
            "winner_company": self.winner_company,
            "status": self.status,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "metadata": self.meta_data,
            "created_at": self.created_at.isoformat(),
            "past_proposals_count": len(self.past_proposals) if self.past_proposals else 0
        }
