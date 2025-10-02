"""
SQLAlchemy model for KB Tags (standardized taxonomy).
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Text, Integer, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class KBTag(Base):
    """Standardized tags for Knowledge Base organization"""

    __tablename__ = "kb_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tag_name = Column(String(100), nullable=False, unique=True)
    tag_category = Column(String(50), index=True)
    description = Column(Text)
    usage_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "tag_category IN ('sector', 'technology', 'process', 'certification', 'service', 'skill', 'custom')",
            name="check_tag_category"
        ),
    )

    def __repr__(self):
        return f"<KBTag {self.tag_category}: {self.tag_name}>"
