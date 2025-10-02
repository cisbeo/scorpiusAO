"""
SQLAlchemy models for Tender Documents.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class TenderDocument(Base):
    """Documents uploaded for a tender (CCTP, RC, AE, etc.)"""

    __tablename__ = "tender_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_id = Column(UUID(as_uuid=True), ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False, index=True)

    # File information
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # MinIO/S3 path
    file_size = Column(Integer)  # In bytes
    mime_type = Column(String(100))

    # Document type
    document_type = Column(String(50), index=True)  # CCTP, RC, AE, BPU, DUME, ANNEXE

    # Extraction status
    extraction_status = Column(String(50), default="pending", index=True)  # pending, processing, completed, failed
    extracted_text = Column(Text)
    page_count = Column(Integer)

    # Extraction metadata
    extraction_method = Column(String(20))  # text, ocr
    extraction_meta_data = Column(JSON)
    extraction_error = Column(Text)

    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    processed_at = Column(DateTime(timezone=True))

    # Relationships
    #     tender = relationship("Tender", back_populates="documents")
    sections = relationship("DocumentSection", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TenderDocument {self.filename}>"
