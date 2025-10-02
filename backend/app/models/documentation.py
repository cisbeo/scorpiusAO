"""
SQLAlchemy model for Internal Documentation (processes, methodologies, etc.).
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class Documentation(Base):
    """Internal documentation (ITIL processes, methodologies, capabilities)"""

    __tablename__ = "documentation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kb_document_id = Column(UUID(as_uuid=True), ForeignKey('kb_documents.id', ondelete='CASCADE'), nullable=False)

    # Document classification
    doc_category = Column(String(100), nullable=False, index=True)
    doc_subcategory = Column(String(100))

    # Process/framework details
    process_framework = Column(String(50), index=True)
    process_name = Column(String(200))
    version = Column(String(20))
    language = Column(String(10), default='fr')

    # Metadata
    target_audience = Column(String(100))
    related_certifications = Column(JSONB, default=[])
    keywords = Column(JSONB, default=[])

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    kb_document = relationship("KBDocument", back_populates="documentation")

    __table_args__ = (
        CheckConstraint(
            "doc_category IN ('process', 'methodology', 'capability', 'policy', 'standard', 'guide')",
            name="check_doc_category"
        ),
        CheckConstraint(
            "process_framework IN ('ITIL', 'ISO20000', 'ISO27001', 'Agile', 'PRINCE2', 'DevOps', 'custom')",
            name="check_process_framework"
        ),
    )

    def __repr__(self):
        return f"<Documentation {self.doc_category} - {self.process_framework or 'N/A'}: {self.process_name or 'N/A'}>"
