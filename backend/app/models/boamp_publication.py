"""
SQLAlchemy model for BOAMP Publications (Bulletin Officiel des Annonces des Marchés Publics).
"""
from datetime import datetime, date
from uuid import uuid4
from sqlalchemy import Column, String, Text, Date, DateTime, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class BOAMPPublication(Base):
    """
    BOAMP publication representing a public procurement notice.

    Data source: https://boamp-datadila.opendatasoft.com/
    """

    __tablename__ = "boamp_publications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    boamp_id = Column(String(100), nullable=False, unique=True, index=True)

    # Core tender information
    title = Column(Text, nullable=False)
    organization = Column(String(500))
    publication_date = Column(Date, nullable=False, index=True)
    deadline = Column(Date)

    # BOAMP-specific fields
    type_annonce = Column(String(100))
    objet = Column(Text)
    montant = Column(Numeric(15, 2))
    lieu_execution = Column(String(500))

    # Classification (European CPV codes + BOAMP descriptors)
    cpv_codes = Column(JSONB, default=[])
    descripteurs = Column(JSONB, default=[])

    # Raw data from BOAMP API (complete JSON response)
    raw_data = Column(JSONB, nullable=False)

    # Processing status
    status = Column(String(50), default='new', index=True)
    matched_tender_id = Column(UUID(as_uuid=True), ForeignKey('tenders.id', ondelete='SET NULL'))
    imported_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    matched_tender = relationship("Tender", foreign_keys=[matched_tender_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'imported', 'ignored', 'error')",
            name="check_boamp_status"
        ),
    )

    def __repr__(self):
        return f"<BOAMPPublication {self.boamp_id}: {self.title[:50]}>"

    @property
    def is_imported(self) -> bool:
        """Check if publication has been imported as a Tender."""
        return self.status == 'imported' and self.matched_tender_id is not None

    @property
    def days_until_deadline(self) -> int | None:
        """Calculate days remaining until deadline."""
        if not self.deadline:
            return None
        delta = self.deadline - date.today()
        return delta.days

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "boamp_id": self.boamp_id,
            "title": self.title,
            "organization": self.organization,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "type_annonce": self.type_annonce,
            "montant": float(self.montant) if self.montant else None,
            "lieu_execution": self.lieu_execution,
            "cpv_codes": self.cpv_codes,
            "descripteurs": self.descripteurs,
            "status": self.status,
            "matched_tender_id": str(self.matched_tender_id) if self.matched_tender_id else None,
            "imported_at": self.imported_at.isoformat() if self.imported_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "days_until_deadline": self.days_until_deadline,
        }
