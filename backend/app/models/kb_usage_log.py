"""
SQLAlchemy model for KB Usage Logs (analytics tracking).
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class KBUsageLog(Base):
    """Usage tracking for Knowledge Base documents"""

    __tablename__ = "kb_usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('kb_documents.id', ondelete='CASCADE'), nullable=False, index=True)
    used_in_tender_id = Column(UUID(as_uuid=True), ForeignKey('tenders.id', ondelete='SET NULL'), index=True)
    used_in_proposal_id = Column(UUID(as_uuid=True))
    usage_type = Column(String(50), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True))
    relevance_score = Column(Float)
    user_feedback = Column(String(20))
    context = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    document = relationship("KBDocument", back_populates="usage_logs")

    __table_args__ = (
        CheckConstraint(
            "usage_type IN ('rag_suggestion', 'manual_search', 'auto_insert', 'reference_check', 'compliance_proof')",
            name="check_usage_type"
        ),
        CheckConstraint(
            "user_feedback IN ('helpful', 'not_helpful', 'partially_helpful')",
            name="check_user_feedback"
        ),
    )

    def __repr__(self):
        return f"<KBUsageLog {self.usage_type} for doc {self.document_id}>"
