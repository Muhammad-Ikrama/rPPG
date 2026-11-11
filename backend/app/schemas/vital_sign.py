"""
Pydantic Schemas for Vital Signs, Dual-Reading Comparison, and Session History.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class VitalSignMetric(BaseModel):
    value: Optional[float] = None
    unit: str
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    status: str
    uncertainty_range: Optional[str] = None
    is_experimental: bool = False
    is_calibrated: bool = False
    disclaimer: Optional[str] = None


class ManualReferenceSummary(BaseModel):
    hr_bpm: Optional[float] = None
    rr_brpm: Optional[float] = None
    spo2_percent: Optional[float] = None
    sbp_mmhg: Optional[float] = None
    dbp_mmhg: Optional[float] = None
    measured_at: Optional[datetime] = None
    monitor_device_name: Optional[str] = None
    operator_notes: Optional[str] = None
    is_verified: bool = False


class DashboardVitalSigns(BaseModel):
    session_id: str
    timestamp: datetime
    camera_type: str
    status: str

    # Phase 4 & 6 Context
    subject_id: Optional[str] = None
    subject_code: Optional[str] = None
    session_code: Optional[str] = None
    experimental_condition: Optional[str] = None
    drive_sync_status: Optional[str] = None
    monitor_image_uploaded: bool = False
    manual_reference: Optional[ManualReferenceSummary] = None
    roi_diagnostics: Optional[Dict[str, Any]] = None

    # 4 Dedicated Measurement Cards
    heart_rate: VitalSignMetric
    respiratory_rate: VitalSignMetric
    oxygen_saturation: VitalSignMetric
    blood_pressure_sbp: VitalSignMetric
    blood_pressure_dbp: VitalSignMetric

    # Quality Assessment
    signal_quality_score: float
    signal_quality_status: str
    motion_stability: float
    illumination_stability: float
    quality_guidance: str

    # Waveforms for Interactive Graphs
    rppg_waveform: List[float] = []
    frequencies_hz: List[float] = []
    psd_power: List[float] = []


class SessionSummaryResponse(BaseModel):
    session_id: str
    session_code: Optional[str] = None
    subject_id: Optional[str] = None
    subject_code: Optional[str] = None
    status: str
    error_message: Optional[str] = None

    # Experimental Condition Metadata (Phase 6)
    experimental_condition: str
    condition_other_detail: Optional[str] = None
    activity_duration_min: Optional[float] = None
    ambient_lighting: Optional[str] = None
    device_model: Optional[str] = None
    device_os: Optional[str] = None
    consent_verified: bool
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    # Channel A: Camera & Video Metadata
    camera_type: str
    resolution: str
    fps: float
    duration_sec: float
    total_frames: int
    dropped_frames: int
    has_video: bool
    video_filename: Optional[str] = None
    video_sha256: Optional[str] = None
    video_size_bytes: int = 0

    # Channel B: Monitor Image Metadata
    has_monitor_image: bool
    monitor_image_filename: Optional[str] = None
    monitor_image_sha256: Optional[str] = None
    monitor_image_size_bytes: int = 0
    monitor_image_captured_at: Optional[datetime] = None
    monitor_device_name: Optional[str] = None

    # Estimates & Manual Reference
    rppg_vitals: Optional[DashboardVitalSigns] = None
    manual_reference: Optional[ManualReferenceSummary] = None
    comparison_deltas: Dict[str, Optional[float]] = {}

    # Phase 5: Sync Tracking
    drive_sync_status: str
    drive_folder_id: Optional[str] = None
    drive_video_file_id: Optional[str] = None
    drive_monitor_image_file_id: Optional[str] = None
    drive_reference_csv_file_id: Optional[str] = None
    drive_metadata_json_file_id: Optional[str] = None
    sheets_synced: bool = False
    last_sync_error: Optional[str] = None
    synced_at: Optional[datetime] = None


class SessionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_code: Optional[str] = None
    session_code: Optional[str] = None
    experimental_condition: Optional[str] = None
    created_at: datetime
    camera_type: str
    duration_sec: float
    status: str
    hr_bpm: Optional[float] = None
    rr_brpm: Optional[float] = None
    spo2_percent: Optional[float] = None
    sbp_mmhg: Optional[float] = None
    dbp_mmhg: Optional[float] = None
    reference_hr: Optional[float] = None
    has_monitor_image: bool = False
    drive_sync_status: Optional[str] = None
    sqi_status: str


class MeasurementHistoryResponse(BaseModel):
    total_count: int
    sessions: List[SessionListItem]
