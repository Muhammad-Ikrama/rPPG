"""
Pydantic Schemas for Session Initialization, Experimental Conditions (Phase 6),
and Dual-Channel Acquisition (Channel A Video & Channel B Patient Monitor).
"""

from enum import Enum
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, model_validator


class ExperimentalCondition(str, Enum):
    NORMAL_RESTING = "Normal Resting"
    BEFORE_EATING = "Before Eating"
    AFTER_EATING = "After Eating"
    BEFORE_EXERCISE = "Before Exercise"
    IMMEDIATELY_AFTER_EXERCISE = "Immediately After Exercise"
    AFTER_EXERCISE_RECOVERY = "After Exercise Recovery"
    BEFORE_REST = "Before Rest"
    AFTER_REST = "After Rest"
    REPEATABILITY_TEST = "Repeatability Test"
    OTHER = "Other"


class SessionCreate(BaseModel):
    subject_id: Optional[str] = Field(
        None,
        description="UUID or canonical subject_code (e.g. SUBJECT_001) to associate session with",
    )
    client_session_id: Optional[str] = Field(
        None,
        max_length=64,
        description="Client-generated UUID idempotency key to prevent duplicate session creation on retries",
    )
    experimental_condition: ExperimentalCondition = ExperimentalCondition.NORMAL_RESTING
    condition_other_detail: Optional[str] = Field(None, max_length=255)
    activity_duration_min: Optional[float] = Field(None, ge=0.0, le=1440.0)
    ambient_lighting: Optional[str] = Field("Indoor Ambient", max_length=64)
    device_model: Optional[str] = Field(None, max_length=128)
    device_os: Optional[str] = Field(None, max_length=64)
    consent_verified: bool = Field(
        True,
        description="Participant session consent verification flag",
    )
    started_at: Optional[datetime] = None

    camera_type: str = "front_camera"  # front_camera, webcam, external, file
    resolution: str = "1280x720"
    fps: float = Field(30.0, gt=0)

    # Optional pre-seeded references (Channel B dedicated endpoint is preferred)
    reference_hr: Optional[float] = Field(None, ge=25.0, le=240.0)
    reference_rr: Optional[float] = Field(None, ge=4.0, le=60.0)
    reference_spo2: Optional[float] = Field(None, ge=50.0, le=100.0)
    reference_sbp: Optional[float] = Field(None, ge=60.0, le=260.0)
    reference_dbp: Optional[float] = Field(None, ge=30.0, le=180.0)

    @model_validator(mode="after")
    def validate_condition_and_consent(self):
        if self.experimental_condition == ExperimentalCondition.OTHER:
            if not self.condition_other_detail or not self.condition_other_detail.strip():
                raise ValueError("condition_other_detail is required when experimental_condition is 'Other'.")
        if not self.consent_verified:
            raise ValueError("Participant consent must be verified prior to starting a session.")
        return self


class SessionResponse(BaseModel):
    session_id: str
    session_code: Optional[str] = None
    subject_id: Optional[str] = None
    subject_code: Optional[str] = None
    experimental_condition: str
    status: str
    created_at: datetime
    message: str
    is_duplicate: bool = False


class ManualReferenceReadingRequest(BaseModel):
    """
    Channel B: Manual entry of patient monitor ground-truth reference vitals.
    Never automatically invented or inferred from monitor images.
    """

    hr_bpm: Optional[float] = Field(None, ge=25.0, le=240.0)
    rr_brpm: Optional[float] = Field(None, ge=4.0, le=60.0)
    spo2_percent: Optional[float] = Field(None, ge=50.0, le=100.0)
    sbp_mmhg: Optional[float] = Field(None, ge=60.0, le=260.0)
    dbp_mmhg: Optional[float] = Field(None, ge=30.0, le=180.0)
    measured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    monitor_device_name: Optional[str] = Field(None, max_length=128)
    operator_notes: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode="after")
    def validate_manual_entry(self):
        if all(
            v is None
            for v in (self.hr_bpm, self.rr_brpm, self.spo2_percent, self.sbp_mmhg, self.dbp_mmhg)
        ):
            raise ValueError("At least one manually verified patient monitor parameter must be provided.")
        if self.sbp_mmhg is not None and self.dbp_mmhg is not None:
            if self.sbp_mmhg <= self.dbp_mmhg:
                raise ValueError("Systolic BP must be strictly greater than Diastolic BP.")
            if (self.sbp_mmhg - self.dbp_mmhg) < 10.0:
                raise ValueError("Pulse pressure (SBP - DBP) must be at least 10 mmHg.")
        return self


class LiveFrameProcessRequest(BaseModel):
    frame_base64: str
    frame_index: int
    timestamp_ms: float
