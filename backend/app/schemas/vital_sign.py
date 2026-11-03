"""
Pydantic Schemas for Vital Signs and Measurement Results.
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


class DashboardVitalSigns(BaseModel):
    session_id: str
    timestamp: datetime
    camera_type: str
    status: str

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


class SessionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    camera_type: str
    duration_sec: float
    status: str
    hr_bpm: Optional[float] = None
    rr_brpm: Optional[float] = None
    spo2_percent: Optional[float] = None
    sbp_mmhg: Optional[float] = None
    dbp_mmhg: Optional[float] = None
    sqi_status: str


class MeasurementHistoryResponse(BaseModel):
    total_count: int
    sessions: List[SessionListItem]
