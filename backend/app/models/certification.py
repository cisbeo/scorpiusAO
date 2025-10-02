"""
SQLAlchemy model for Certifications (ISO, etc.).
"""
from datetime import datetime, date
from uuid import uuid4
from sqlalchemy import Column, String, Text, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class Certification(Base):
    """Company certifications (ISO 27001, ISO 9001, HDS, etc.)"""

    __tablename__ = "certifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kb_document_id = Column(UUID(as_uuid=True), ForeignKey('kb_documents.id', ondelete='CASCADE'), nullable=False)

    # Certification details
    certification_name = Column(String(200), nullable=False)
    certification_type = Column(String(100), index=True)
    issuing_authority = Column(String(200))
    certificate_number = Column(String(100))

    # Validity
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, index=True)

    # Scope & details
    scope = Column(Text)
    accreditation_body = Column(String(200))
    related_processes = Column(JSONB, default=[])
    compliance_areas = Column(JSONB, default=[])

    # Status
    is_active = Column(Boolean, default=True, index=True)
    renewal_status = Column(String(50))

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    kb_document = relationship("KBDocument", back_populates="certification")

    def __repr__(self):
        status = "active" if self.is_active else "inactive"
        return f"<Certification {self.certification_name} ({status})>"
