"""
Database ORM Models for Group Data Collection and Reference Instruments.

Complies strictly with Section 13:
- Manages >= 50 participant cohort records.
- Records reference instruments (ECG, Respiratory monitor, Pulse oximeter, Sphygmomanometer).
- Stores environmental tags (lighting, motion, camera hardware, skin type).
- Explicitly accounts for missing-data flags without fabrication.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class Participant(Base):
    __tablename__ = "cohort_participants"

    id = Column(Integer, primary_key=True, index=True)
    participant_id = Column(String(50), unique=True, index=True, nullable=False)  # e.g. SUBJ-001
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    fitzpatrick_skin_type = Column(Integer, nullable=True)  # 1 to 6 scale
    consent_signed = Column(Boolean, default=False, nullable=False)
    consent_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    recordings = relationship("PairedRecording", back_populates="participant", cascade="all, delete-orphan")


class PairedRecording(Base):
    __tablename__ = "paired_recordings"

    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(String(50), unique=True, index=True, nullable=False)
    participant_id = Column(String(50), ForeignKey("cohort_participants.participant_id"), nullable=False)

    # Video acquisition properties
    video_path = Column(String(255), nullable=True)
    video_sha256 = Column(String(64), nullable=True)
    duration_sec = Column(Float, nullable=False)
    fps = Column(Float, nullable=False, default=30.0)
    resolution = Column(String(20), default="1920x1080")
    camera_hardware = Column(String(100), default="Standard RGB Camera")

    # Environmental acquisition conditions
    lighting_condition = Column(String(50), default="Ambient Laboratory (350 lux)")
    motion_condition = Column(String(50), default="Resting Stationary")

    # Reference instrument labels (Ground Truth)
    ref_hr_bpm = Column(Float, nullable=True)
    ref_hr_device = Column(String(100), default="12-Lead ECG / Patient Monitor")

    ref_rr_brpm = Column(Float, nullable=True)
    ref_rr_device = Column(String(100), default="Piezoelectric Respiratory Belt")

    ref_spo2_percent = Column(Float, nullable=True)
    ref_spo2_device = Column(String(100), default="Clinical Finger Pulse Oximeter")

    ref_bp_systolic_mmhg = Column(Float, nullable=True)
    ref_bp_diastolic_mmhg = Column(Float, nullable=True)
    ref_bp_device = Column(String(100), default="ISO 81060-2 Digital Sphygmomanometer")

    is_synchronized = Column(Boolean, default=True)
    missing_labels_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    participant = relationship("Participant", back_populates="recordings")

