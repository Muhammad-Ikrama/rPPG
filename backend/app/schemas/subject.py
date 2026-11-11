"""
Pydantic Schemas for Subject-Wise Research Data Management (Phase 4).
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class SubjectCreate(BaseModel):
    age: Optional[int] = Field(None, ge=18, le=110)
    gender: Optional[str] = Field(None, max_length=32)
    fitzpatrick_skin_type: Optional[int] = Field(None, ge=1, le=6)
    consent_signed: bool = Field(..., description="Participant informed research consent must be signed")
    notes: Optional[str] = Field(None, max_length=1000)


class SubjectUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=18, le=110)
    gender: Optional[str] = Field(None, max_length=32)
    fitzpatrick_skin_type: Optional[int] = Field(None, ge=1, le=6)
    notes: Optional[str] = Field(None, max_length=1000)


class SubjectSessionBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_code: Optional[str] = None
    experimental_condition: str
    status: str
    drive_sync_status: str
    created_at: datetime
    hr_bpm: Optional[float] = None
    rr_brpm: Optional[float] = None
    spo2_percent: Optional[float] = None
    sbp_mmhg: Optional[float] = None
    dbp_mmhg: Optional[float] = None
    sqi_status: Optional[str] = None
    reference_hr: Optional[float] = None
    reference_rr: Optional[float] = None
    reference_spo2: Optional[float] = None
    reference_sbp: Optional[float] = None
    reference_dbp: Optional[float] = None
    has_video: bool = False
    has_monitor_image: bool = False
    is_manual_reference_verified: bool = False


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_code: str
    age: Optional[int] = None
    gender: Optional[str] = None
    fitzpatrick_skin_type: Optional[int] = None
    consent_signed: bool
    consent_timestamp: Optional[datetime] = None
    notes: Optional[str] = None
    drive_folder_id: Optional[str] = None
    created_at: datetime
    session_count: int = 0
    sessions: List[SubjectSessionBrief] = []
