"""
Live Camera Frame Streaming and Face Positioning Guidance API.
"""

from typing import Dict, Any
import base64
import numpy as np
import cv2
from fastapi import APIRouter
from pydantic import BaseModel
from app.rppg.face_roi import FaceROIExtractor

router = APIRouter(prefix="/stream", tags=["Live Stream & Positioning"])
roi_extractor = FaceROIExtractor()


class FrameAnalyzeRequest(BaseModel):
    image_base64: str  # Base64 data URL or raw base64 string


@router.post("/analyze-frame")
async def analyze_live_frame(payload: FrameAnalyzeRequest) -> Dict[str, Any]:
    """
    Analyzes a single video frame sent from the mobile or web camera preview.

    Returns:
    - face_detected: Boolean
    - guidance: Clear instructional feedback (Center face, hold steady, optimal, etc.)
    - bounding_box: [x, y, w, h] of face
    - zones: Bounding boxes for forehead, left cheek, right cheek
    - quality_score: [0.0 - 1.0]
    - motion_magnitude: Motion index in pixels
    """
    raw_str = payload.image_base64
    if "," in raw_str:
        raw_str = raw_str.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(raw_str)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return {"face_detected": False, "guidance": "Could not decode frame image."}
    except Exception as e:
        return {"face_detected": False, "guidance": f"Frame decoding error: {str(e)}"}

    h, w = frame.shape[:2]
    res = roi_extractor.extract_from_frame(frame)

    if not res["face_detected"]:
        return {
            "face_detected": False,
            "guidance": "No face detected. Please position your face inside the camera frame.",
            "quality_score": 0.0,
            "bbox": None,
            "zones": None,
        }

    bbox = res["bbox"]
    motion = res["motion_magnitude"]
    quality = res["quality_score"]
    skin_pixels = res.get("skin_pixels", 0)

    # Check face sizing and centering
    fx, fy, fw, fh = bbox
    face_area_ratio = (fw * fh) / (w * h + 1e-6)
    center_x = fx + fw / 2.0
    center_y = fy + fh / 2.0
    dist_from_center_x = abs(center_x - (w / 2.0)) / w

    guidance = "Face detected."
    if face_area_ratio < 0.08:
        guidance = "Move closer to the camera."
    elif face_area_ratio > 0.65:
        guidance = "Move slightly further back from the camera."
    elif dist_from_center_x > 0.20:
        guidance = "Center your face in the oval guide."
    elif motion > 8.0:
        guidance = "Hold still. Minimize facial and head movement."
    elif skin_pixels < 200:
        guidance = "Ensure your face is well-lit from the front."
    else:
        guidance = "Optimal face position! You may start recording."

    return {
        "face_detected": True,
        "guidance": guidance,
        "quality_score": quality,
        "motion_magnitude": motion,
        "frame_width": w,
        "frame_height": h,
        "bbox": bbox,
        "zones": res.get("zones"),
        "method": res.get("method"),
    }
