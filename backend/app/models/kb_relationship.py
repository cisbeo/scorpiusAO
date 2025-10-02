"""
SQLAlchemy model for KB Relationships (document links).
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class KBRelationship(Base):
    """Relationships between Knowledge Base documents"""

    __tablename__ = "kb_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_document_id = Column(UUID(as_uuid=True), ForeignKey('kb_documents.id', ondelete='CASCADE'), nullable=False, index=True)
    target_document_id = Column(UUID(as_uuid=True), ForeignKey('kb_documents.id', ondelete='CASCADE'), nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False, index=True)
    strength = Column(Float)
    context = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('references', 'complements', 'supersedes', 'requires', 'similar_to', 'derived_from')",
            name="check_relationship_type"
        ),
        CheckConstraint(
            "strength IS NULL OR (strength >= 0 AND strength <= 1)",
            name="check_strength"
        ),
    )

    def __repr__(self):
        return f"<KBRelationship {self.relationship_type}: {self.source_document_id} -> {self.target_document_id}>"
