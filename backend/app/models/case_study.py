"""
SQLAlchemy model for Case Studies (client references).
"""
from datetime import datetime, date
from uuid import uuid4
from sqlalchemy import Column, String, Text, Date, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class CaseStudy(Base):
    """Client references and success stories"""

    __tablename__ = "case_studies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kb_document_id = Column(UUID(as_uuid=True), ForeignKey('kb_documents.id', ondelete='CASCADE'), nullable=False)

    # Client information
    client_name = Column(String(200), nullable=False)
    client_sector = Column(String(100), index=True)
    client_size = Column(String(50))

    # Project information
    project_title = Column(String(500), nullable=False)
    project_description = Column(Text)
    services_provided = Column(JSONB, default=[])
    technologies_used = Column(JSONB, default=[])

    # Project details
    challenges = Column(Text)
    solutions = Column(Text)
    results = Column(Text)
    metrics = Column(JSONB, default={})

    # Testimonial
    testimonial = Column(Text)
    testimonial_author = Column(String(200))

    # Timeline & value
    start_date = Column(Date)
    end_date = Column(Date)
    contract_value = Column(Numeric(15, 2))

    # Confidentiality
    is_confidential = Column(Boolean, default=False)
    can_use_client_name = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    kb_document = relationship("KBDocument", back_populates="case_study")

    def __repr__(self):
        client = self.client_name if self.can_use_client_name else "[Confidential]"
        return f"<CaseStudy '{self.project_title[:30]}' for {client}>"
