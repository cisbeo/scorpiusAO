"""
Document sections model for storing structured extracted content.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, JSON, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.models.base import Base


class DocumentSection(Base):
    """
    Structured sections extracted from tender documents.

    Stores hierarchical sections (PARTIE, Article, numbered sections)
    with their full content, enabling fast retrieval without re-parsing.
    """

    __tablename__ = "document_sections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey('tender_documents.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Section identification
    section_type = Column(String(50), nullable=False, index=True)  # PARTIE, ARTICLE, SECTION, TOC
    section_number = Column(String(50))  # "1.1", "2.3.4", etc.
    title = Column(Text, nullable=False)

    # Content
    content = Column(Text)
    content_length = Column(Integer, default=0)
    content_truncated = Column(Boolean, default=False)

    # Position in document
    page = Column(Integer, nullable=False, index=True)
    line = Column(Integer)

    # Hierarchy (for nested sections)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('document_sections.id', ondelete='SET NULL'))
    parent_number = Column(String(50))  # Parent section number (e.g., "4.1.4" for section "4.1.4.2")
    level = Column(Integer, default=1)  # Nesting level (1 = top level)

    # Flags
    is_toc = Column(Boolean, default=False, index=True)  # True for table of contents
    is_key_section = Column(Boolean, default=False, index=True)  # Exclusions, obligations, etc.

    # Additional metadata (tags, extracted dates, etc.)
    meta_data = Column(JSON)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("TenderDocument", back_populates="sections")
    children = relationship(
        "DocumentSection",
        backref="parent",
        remote_side=[id],
        cascade="all"
    )

    # Indexes for common queries
    __table_args__ = (
        Index('idx_document_page', 'document_id', 'page'),
        Index('idx_document_type', 'document_id', 'section_type'),
        Index('idx_key_sections', 'document_id', 'is_key_section'),
    )

    def __repr__(self):
        return f"<DocumentSection(id={self.id}, type={self.section_type}, number={self.section_number}, title={self.title[:50]}...)>"
