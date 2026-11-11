"""
Measurement Session, Experimental Condition, Dual Reading Media, and Sync Metadata Model.
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

    # Phase 4: Subject-Wise & Idempotency Tracking
    subject_id = Column(String(36), ForeignKey("subjects.id"), nullable=True, index=True)
    subject_code = Column(String(32), nullable=True, index=True)   # e.g., SUBJECT_001
    session_code = Column(String(32), nullable=True, index=True)   # e.g., SESSION_001
    client_session_id = Column(String(64), unique=True, nullable=True, index=True)

    # Status: CREATED, QUEUED, PROCESSING, COMPLETED, FAILED
    status = Column(String(32), default="QUEUED", index=True, nullable=False)
    error_message = Column(Text, nullable=True)

    # Phase 6: Experimental Condition Form
    experimental_condition = Column(String(64), default="Normal Resting", nullable=False)
    condition_other_detail = Column(String(255), nullable=True)
    activity_duration_min = Column(Float, nullable=True)
    ambient_lighting = Column(String(64), nullable=True)
    device_model = Column(String(128), nullable=True)
    device_os = Column(String(64), nullable=True)
    consent_verified = Column(Boolean, default=False, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Channel A: Camera & Video Acquisition Metadata
    camera_type = Column(String(64), default="front_camera")
    resolution = Column(String(32), default="1280x720")
    fps = Column(Float, default=30.0)
    duration_sec = Column(Float, default=0.0)
    total_frames = Column(Integer, default=0)
    dropped_frames = Column(Integer, default=0)

    video_filename = Column(String(255), nullable=True)
    video_sha256 = Column(String(64), nullable=True)
    video_size_bytes = Column(Integer, default=0)
    storage_path = Column(String(512), nullable=True)
    is_deleted = Column(Boolean, default=False)
    retention_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Channel B: Patient Monitor Image Metadata
    monitor_image_filename = Column(String(255), nullable=True)
    monitor_image_path = Column(String(512), nullable=True)
    monitor_image_sha256 = Column(String(64), nullable=True)
    monitor_image_size_bytes = Column(Integer, default=0)
    monitor_image_captured_at = Column(DateTime(timezone=True), nullable=True)
    monitor_device_name = Column(String(128), nullable=True)

    # Phase 5: Google Drive & Google Sheets Sync Tracking
    drive_sync_status = Column(String(32), default="PENDING", nullable=False)
    drive_folder_id = Column(String(128), nullable=True)
    drive_video_file_id = Column(String(128), nullable=True)
    drive_monitor_image_file_id = Column(String(128), nullable=True)
    drive_reference_csv_file_id = Column(String(128), nullable=True)
    drive_metadata_json_file_id = Column(String(128), nullable=True)
    sheets_synced = Column(Boolean, default=False, nullable=False)
    last_sync_error = Column(Text, nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=True)

    # Algorithm details
    algorithm_version = Column(String(64), default="POS-v1.1.0")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")
    subject = relationship("Subject", back_populates="sessions")
    vital_signs = relationship("VitalSignEstimate", back_populates="session", uselist=False, cascade="all, delete-orphan")
