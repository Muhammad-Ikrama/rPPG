"""
Subject-Wise Data Management Database Model (Phase 4).
Assigns canonical SUBJECT_001 identifiers separate from researcher user accounts.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_code = Column(String(32), unique=True, index=True, nullable=False)  # e.g., SUBJECT_001
    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    age = Column(Integer, nullable=True)
    gender = Column(String(32), nullable=True)
    fitzpatrick_skin_type = Column(Integer, nullable=True)  # 1 to 6
    consent_signed = Column(Boolean, default=False, nullable=False)
    consent_timestamp = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # Google Drive persistence
    drive_folder_id = Column(String(128), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sessions = relationship("MeasurementSession", back_populates="subject")
