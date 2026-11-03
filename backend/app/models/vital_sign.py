"""
Vital Sign Estimate and Biomarker Results Database Model.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class VitalSignEstimate(Base):
    __tablename__ = "vital_sign_estimates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("measurement_sessions.id"), unique=True, nullable=False, index=True)

    # 1. Heart Rate (HR)
    hr_bpm = Column(Float, nullable=True)
    hr_confidence = Column(Float, default=0.0)
    hr_status = Column(String(32), default="UNRELIABLE")  # EXCELLENT, GOOD, FAIR, UNRELIABLE
    snr_db = Column(Float, default=-99.0)
    time_domain_bpm = Column(Float, nullable=True)
    rmssd_ms = Column(Float, nullable=True)

    # 2. Respiratory Rate (RR)
    rr_brpm = Column(Float, nullable=True)
    rr_confidence = Column(Float, default=0.0)
    rr_status = Column(String(32), default="UNAVAILABLE")  # GOOD, FAIR, LOW_CONFIDENCE, UNAVAILABLE

    # 3. Peripheral Oxygen Saturation (SpO2) - Research Module
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

    # Signal Quality Index (SQI)
    sqi_score = Column(Float, default=0.0)
    sqi_status = Column(String(32), default="POOR")
    motion_stability = Column(Float, default=0.0)
    illumination_stability = Column(Float, default=0.0)
    quality_guidance = Column(Text, nullable=True)

    # Ground Truth Reference Values (for clinical/dataset validation)
    reference_hr = Column(Float, nullable=True)
    reference_rr = Column(Float, nullable=True)
    reference_spo2 = Column(Float, nullable=True)
    reference_sbp = Column(Float, nullable=True)
    reference_dbp = Column(Float, nullable=True)

    # Serialized Signal Curves for Interactive Visualizations
    rppg_waveform_json = Column(Text, nullable=True)  # Downsampled points [v1, v2, ...]
    psd_frequencies_json = Column(Text, nullable=True)
    psd_power_json = Column(Text, nullable=True)
    ibi_series_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("MeasurementSession", back_populates="vital_signs")
