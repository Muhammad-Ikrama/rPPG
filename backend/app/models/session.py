"""
Measurement Session and Video Metadata Database Model.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class MeasurementSession(Base):
    __tablename__ = "measurement_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # Status: QUEUED, PROCESSING, COMPLETED, FAILED
    status = Column(String(32), default="QUEUED", index=True, nullable=False)
    error_message = Column(Text, nullable=True)

    # Camera & Video Acquisition Metadata
    camera_type = Column(String(64), default="front_camera")  # front, webcam, external, recorded_file
    resolution = Column(String(32), default="1280x720")
    fps = Column(Float, default=30.0)
    duration_sec = Column(Float, default=0.0)
    total_frames = Column(Integer, default=0)
    dropped_frames = Column(Integer, default=0)

    # Video Storage & Retention Metadata
    video_filename = Column(String(255), nullable=True)
    video_sha256 = Column(String(64), nullable=True)
    video_size_bytes = Column(Integer, default=0)
    storage_path = Column(String(512), nullable=True)
    is_deleted = Column(Boolean, default=False)
    retention_expires_at = Column(DateTime, nullable=True)

    # Algorithm details
    algorithm_version = Column(String(64), default="POS-v1.0.0")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")
    vital_signs = relationship("VitalSignEstimate", back_populates="session", uselist=False, cascade="all, delete-orphan")
