"""
Secure Video Storage, SHA-256 Hashing, and Video Decoding Service.
"""

from typing import Tuple, List, Dict, Any, Optional
import os
import hashlib
from datetime import datetime, timedelta, timezone
import cv2
import numpy as np
from app.core.config import settings


def compute_file_sha256(filepath: str) -> str:
    """Calculates SHA-256 cryptographic hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


class VideoStorageService:
    @staticmethod
    async def save_upload(session_id: str, file_bytes: bytes, original_filename: str) -> Dict[str, Any]:
        """
        Saves uploaded video file with privacy-conscious naming and computes checksum.
        """
        ext = os.path.splitext(original_filename)[1].lower() or ".mp4"
        safe_filename = f"vid_{session_id}{ext}"
        storage_path = os.path.join(settings.STORAGE_DIR, safe_filename)

        with open(storage_path, "wb") as f:
            f.write(file_bytes)

        file_size = len(file_bytes)
        sha256 = compute_file_sha256(storage_path)
        retention_expires = datetime.now(timezone.utc) + timedelta(days=settings.VIDEO_RETENTION_DAYS)

        return {
            "filename": safe_filename,
            "storage_path": storage_path,
            "size_bytes": file_size,
            "sha256": sha256,
            "retention_expires_at": retention_expires,
        }

    @staticmethod
    def decode_video_frames(
        video_path: str,
        max_duration_sec: float = 60.0,
    ) -> Tuple[List[np.ndarray], Dict[str, Any]]:
        """
        Decodes video file into list of BGR numpy frames, measuring real fps, resolution, and frame drops.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file {video_path}")

        reported_fps = cap.get(cv2.CAP_PROP_FPS)
        reported_fps = float(reported_fps) if (reported_fps and reported_fps > 5.0) else 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_meta_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frames = []
        max_frames = int(reported_fps * max_duration_sec)
        dropped_frames = 0

        while len(frames) < max_frames:
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            frames.append(frame)

        cap.release()

        actual_frames_count = len(frames)
        if total_meta_frames > 0 and total_meta_frames > actual_frames_count:
            dropped_frames = total_meta_frames - actual_frames_count

        duration_sec = actual_frames_count / reported_fps if reported_fps > 0 else 0.0

        meta = {
            "fps": reported_fps,
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}",
            "frames_count": actual_frames_count,
            "duration_sec": round(duration_sec, 2),
            "dropped_frames": dropped_frames,
        }

        return frames, meta

    @staticmethod
    def delete_video_file(storage_path: str) -> bool:
        """Deletes video file securely upon retention expiration or user request."""
        if storage_path and os.path.exists(storage_path):
            try:
                os.remove(storage_path)
                return True
            except OSError:
                return False
        return False
