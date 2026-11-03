"""
Pydantic Schemas for Session Initialization and Video Upload.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class SessionCreate(BaseModel):
    camera_type: str = "webcam"  # front_camera, webcam, external, file
    resolution: str = "1280x720"
    fps: float = 30.0
    reference_hr: Optional[float] = None
    reference_rr: Optional[float] = None
    reference_spo2: Optional[float] = None
    reference_sbp: Optional[float] = None
    reference_dbp: Optional[float] = None


class SessionResponse(BaseModel):
    session_id: str
    status: str
    created_at: datetime
    message: str


class LiveFrameProcessRequest(BaseModel):
    frame_base64: str
    frame_index: int
    timestamp_ms: float
