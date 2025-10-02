"""
SQLAlchemy model for Templates (reusable content sections).
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class Template(Base):
    """Reusable content templates for tender responses"""

    __tablename__ = "templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    kb_document_id = Column(UUID(as_uuid=True), ForeignKey('kb_documents.id', ondelete='CASCADE'), nullable=False)

    # Template details
    template_type = Column(String(100), nullable=False, index=True)
    section_name = Column(String(200))
    template_content = Column(Text, nullable=False)

    # Customization
    variables = Column(JSONB, default=[])
    placeholders = Column(JSONB, default={})
    usage_context = Column(Text)
    customization_instructions = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    kb_document = relationship("KBDocument", back_populates="template")

    __table_args__ = (
        CheckConstraint(
            "template_type IN ('company_presentation', 'methodology', 'team_composition', 'security_measures', 'quality_assurance', 'project_management', 'technical_solution', 'custom')",
            name="check_template_type"
        ),
    )

    def __repr__(self):
        return f"<Template {self.template_type}: {self.section_name or 'Untitled'}>"
