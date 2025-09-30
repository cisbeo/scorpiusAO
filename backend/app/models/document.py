"""
SQLAlchemy models for Document embeddings.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.models.base import Base


class DocumentEmbedding(Base):
    """Document embeddings for RAG search."""

    __tablename__ = "document_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), index=True)
    document_type = Column(String(50), index=True)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<DocumentEmbedding {self.document_id}>"
