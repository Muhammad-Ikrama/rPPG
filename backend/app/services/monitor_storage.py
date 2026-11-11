"""
Patient Monitor Image Validation and Storage Service (Channel B - Phase 3).
Validates image integrity with Pillow and computes SHA-256 checksums without discarding or inventing data.
"""

import io
import os
import hashlib
from typing import Dict, Any
from PIL import Image, UnidentifiedImageError

from app.core.config import settings


ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


class MonitorImageStorageService:
    @staticmethod
    async def save_monitor_image(
        session_id: str,
        image_bytes: bytes,
        original_filename: str = "monitor.jpg",
    ) -> Dict[str, Any]:
        if not image_bytes or len(image_bytes) < 256:
            raise ValueError("Monitor image file is empty or too small.")

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img.verify()
            with Image.open(io.BytesIO(image_bytes)) as img2:
                img_format = (img2.format or "JPEG").upper()
                width, height = img2.size
        except (UnidentifiedImageError, Exception) as exc:
            raise ValueError(f"Invalid or corrupted image file: {exc}")

        if img_format not in ALLOWED_IMAGE_FORMATS:
            raise ValueError(f"Unsupported image format '{img_format}'. Allowed: {sorted(ALLOWED_IMAGE_FORMATS)}")

        ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
        ext = ext_map.get(img_format, ".jpg")
        safe_filename = f"mon_{session_id}{ext}"
        storage_path = os.path.join(settings.MONITOR_IMAGES_DIR, safe_filename)

        with open(storage_path, "wb") as f:
            f.write(image_bytes)

        sha256 = hashlib.sha256(image_bytes).hexdigest()
        return {
            "filename": safe_filename,
            "storage_path": storage_path,
            "size_bytes": len(image_bytes),
            "sha256": sha256,
            "width": width,
            "height": height,
            "format": img_format,
        }

    @staticmethod
    def delete_monitor_image(storage_path: str) -> bool:
        if storage_path and os.path.exists(storage_path):
            try:
                os.remove(storage_path)
                return True
            except OSError:
                return False
        return False
