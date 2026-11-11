"""
Vital Sign Estimate, Signal Diagnostics, and Manual Reference Measurement Model.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class VitalSignEstimate(Base):
    __tablename__ = "vital_sign_estimates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("measurement_sessions.id"), unique=True, nullable=False, index=True)

    # 1. Heart Rate (HR)
    hr_bpm = Column(Float, nullable=True)
    hr_confidence = Column(Float, default=0.0)
    hr_status = Column(String(32), default="UNRELIABLE")
    snr_db = Column(Float, default=-99.0)
    time_domain_bpm = Column(Float, nullable=True)
    rmssd_ms = Column(Float, nullable=True)

    # 2. Respiratory Rate (RR)
    rr_brpm = Column(Float, nullable=True)
    rr_confidence = Column(Float, default=0.0)
    rr_status = Column(String(32), default="UNAVAILABLE")

    # 3. Peripheral Oxygen Saturation (SpO2) - Experimental Research Module
    spo2_percent = Column(Float, nullable=True)
    spo2_confidence = Column(Float, default=0.0)
    spo2_status = Column(String(64), default="EXPERIMENTAL_UNCALIBRATED")
    spo2_ratio_of_ratios = Column(Float, nullable=True)
    spo2_is_calibrated = Column(Boolean, default=False)

    # 4. Blood Pressure (SBP / DBP) - Experimental Research Module
    sbp_mmhg = Column(Float, nullable=True)
    dbp_mmhg = Column(Float, nullable=True)
    bp_confidence = Column(Float, default=0.0)
    bp_status = Column(String(64), default="EXPERIMENTAL_RESEARCH")
    bp_is_calibrated = Column(Boolean, default=False)

    # Signal Quality Index (SQI) & ROI Diagnostics
    sqi_score = Column(Float, default=0.0)
    sqi_status = Column(String(32), default="POOR")
    motion_stability = Column(Float, default=0.0)
    illumination_stability = Column(Float, default=0.0)
    quality_guidance = Column(Text, nullable=True)
    valid_face_ratio = Column(Float, default=0.0)
    mean_motion_px = Column(Float, default=0.0)
    actual_fps = Column(Float, nullable=True)

    # Channel B: Manually Verified Reference Values (Patient Monitor)
    reference_hr = Column(Float, nullable=True)
    reference_rr = Column(Float, nullable=True)
    reference_spo2 = Column(Float, nullable=True)
    reference_sbp = Column(Float, nullable=True)
    reference_dbp = Column(Float, nullable=True)
    reference_measured_at = Column(DateTime(timezone=True), nullable=True)
    reference_operator_notes = Column(Text, nullable=True)
    is_manual_reference_verified = Column(Boolean, default=False, nullable=False)

    # Serialized Signal Curves for Interactive Visualizations
    rppg_waveform_json = Column(Text, nullable=True)
    psd_frequencies_json = Column(Text, nullable=True)
    psd_power_json = Column(Text, nullable=True)
    ibi_series_json = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("MeasurementSession", back_populates="vital_signs")
