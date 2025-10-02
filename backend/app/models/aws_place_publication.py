"""
AWS PLACE Publication Model
Represents procurement publications from AWS PLACE (Plateforme des Achats de l'État)
"""
from sqlalchemy import Column, String, Text, Date, DateTime, Integer, Boolean, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import date, datetime
from app.models.base import Base


class AWSPlacePublication(Base):
    """
    Model for AWS PLACE (Plateforme des Achats de l'État) procurement publications.

    AWS PLACE is the main French government procurement platform, containing higher-value
    IT infrastructure and services contracts compared to BOAMP.
    """
    __tablename__ = "aws_place_publications"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Unique identifier from AWS PLACE
    place_id = Column(String(100), nullable=False, unique=True, index=True)

    # Basic information
    title = Column(Text, nullable=False)
    reference = Column(String(200))
    organization = Column(String(500))

    # Dates
    publication_date = Column(Date, nullable=False, index=True)
    deadline = Column(DateTime(timezone=True), index=True)

    # Description
    description = Column(Text)

    # Classification
    cpv_codes = Column(JSONB, nullable=False, default=list)  # List of CPV codes
    consultation_type = Column(String(100))  # Type de consultation
    procedure_type = Column(String(100))  # Type de procédure

    # Financial information
    estimated_amount = Column(Numeric(15, 2))  # Montant estimé
    currency = Column(String(10), default="EUR")

    # Location & scope
    execution_location = Column(String(500))  # Lieu d'exécution
    nuts_codes = Column(JSONB, default=list)  # NUTS codes (nomenclature européenne des régions)

    # Contract details
    duration_months = Column(Integer)
    renewal_possible = Column(Boolean, default=False)

    # Status tracking
    status = Column(String(50), default="new", index=True, nullable=False)
    # Status values: 'new', 'imported', 'ignored', 'error'

    # Link to created tender
    matched_tender_id = Column(UUID(as_uuid=True), ForeignKey('tenders.id', ondelete='SET NULL'))

    # Raw data & metadata
    raw_data = Column(JSONB, nullable=False)  # Store complete API response
    url = Column(String(500))  # URL to the consultation on AWS PLACE
    documents_url = Column(String(500))  # URL to download documents

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    matched_tender = relationship("Tender", foreign_keys=[matched_tender_id])

    @property
    def days_until_deadline(self) -> int | None:
        """Calculate days remaining until deadline"""
        if not self.deadline:
            return None
        deadline_date = self.deadline.date() if isinstance(self.deadline, datetime) else self.deadline
        return (deadline_date - date.today()).days

    @property
    def is_urgent(self) -> bool:
        """Check if deadline is within 7 days"""
        days = self.days_until_deadline
        return days is not None and 0 < days <= 7

    @property
    def is_expired(self) -> bool:
        """Check if deadline has passed"""
        days = self.days_until_deadline
        return days is not None and days < 0

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses"""
        return {
            "id": str(self.id),
            "place_id": self.place_id,
            "title": self.title,
            "reference": self.reference,
            "organization": self.organization,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "description": self.description,
            "cpv_codes": self.cpv_codes or [],
            "consultation_type": self.consultation_type,
            "procedure_type": self.procedure_type,
            "estimated_amount": float(self.estimated_amount) if self.estimated_amount else None,
            "currency": self.currency,
            "execution_location": self.execution_location,
            "nuts_codes": self.nuts_codes or [],
            "duration_months": self.duration_months,
            "renewal_possible": self.renewal_possible,
            "status": self.status,
            "matched_tender_id": str(self.matched_tender_id) if self.matched_tender_id else None,
            "url": self.url,
            "documents_url": self.documents_url,
            "days_until_deadline": self.days_until_deadline,
            "is_urgent": self.is_urgent,
            "is_expired": self.is_expired,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<AWSPlacePublication(place_id='{self.place_id}', title='{self.title[:50]}...', status='{self.status}')>"
