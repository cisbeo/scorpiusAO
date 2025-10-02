"""
SQLAlchemy models for Knowledge Base documents.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, BigInteger, Float, DateTime, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class KBDocument(Base):
    """Central registry for all Knowledge Base documents"""

    __tablename__ = "kb_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_type = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Content
    content = Column(Text, nullable=False)
    content_format = Column(String(20), default="text")
    word_count = Column(Integer)

    # File metadata
    file_name = Column(String(255))
    file_path = Column(String(500))
    file_size_bytes = Column(BigInteger)
    file_mime_type = Column(String(100))
    file_hash = Column(String(64), index=True)

    # Metadata
    tags = Column(JSONB, default=[])
    meta = Column("metadata", JSONB, default={})

    # Status
    status = Column(String(20), default="active", index=True)
    quality_score = Column(Float)
    usage_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime(timezone=True))
    created_by = Column(UUID(as_uuid=True))

    # Relationships
    past_proposal = relationship("PastProposal", back_populates="kb_document", uselist=False)
    case_study = relationship("CaseStudy", back_populates="kb_document", uselist=False)
    certification = relationship("Certification", back_populates="kb_document", uselist=False)
    documentation = relationship("Documentation", back_populates="kb_document", uselist=False)
    template = relationship("Template", back_populates="kb_document", uselist=False)
    historical_tender = relationship("HistoricalTender", back_populates="kb_document", uselist=False)
    usage_logs = relationship("KBUsageLog", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "document_type IN ('past_proposal', 'case_study', 'certification', 'documentation', 'template', 'historical_tender')",
            name="check_document_type"
        ),
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1)",
            name="check_quality_score"
        ),
    )

    def __repr__(self):
        return f"<KBDocument {self.document_type} '{self.title[:50]}'>"
