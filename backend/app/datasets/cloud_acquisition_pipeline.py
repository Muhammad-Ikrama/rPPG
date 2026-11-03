"""
Automated Cloud Dataset Acquisition, Drive Organization, and Verification Engine.

Enforces Project Constraints:
- Designed to execute entirely within Google Colab / Kaggle cloud runtimes.
- Saves all datasets directly into user's Google Drive (5 TB storage tier).
- Zero local machine storage used; zero local GPU compute.
- Automatic creation of the standard RPPG_FYP folder hierarchy.
- Resumable downloading, SHA-256 verification, and OpenCV frame auditing.
"""

from typing import Dict, Any, List, Optional, Tuple
import os
import sys
import shutil
import hashlib
import json
import time
from datetime import datetime, timezone
import urllib.request
import urllib.error
import cv2


STANDARD_FOLDER_STRUCTURE = [
    "01_RAW_DATASETS",
    "02_DATASET_METADATA",
    "03_PROCESSED_DATASETS",
    "04_TRAINING_DATA",
    "05_MODELS",
    "06_EXPERIMENTS",
    "07_VALIDATION_RESULTS",
    "08_DOCUMENTATION",
]

TARGET_DATASETS = [
    "UBFC-rPPG",
    "PURE",
    "COHFACE",
    "VIPL-HR",
    "MMPD",
    "BP4D_PLUS",
]


class CloudDatasetAcquisitionEngine:
    """
    Automates dataset staging, integrity checking, and Google Drive organization.
    """

    def __init__(self, drive_root: str = "/content/drive/MyDrive/RPPG_FYP"):
        self.drive_root = drive_root

    def setup_google_drive_structure(self) -> Dict[str, str]:
        """
        Creates the standardized 8-folder research hierarchy on Google Drive,
        including individual raw dataset destination folders.
        """
        folder_paths = {}
        os.makedirs(self.drive_root, exist_ok=True)

        for folder in STANDARD_FOLDER_STRUCTURE:
            full_path = os.path.join(self.drive_root, folder)
            os.makedirs(full_path, exist_ok=True)
            folder_paths[folder] = full_path

        # Create subfolders under 01_RAW_DATASETS for each specific dataset
        raw_dir = folder_paths["01_RAW_DATASETS"]
        for ds in TARGET_DATASETS:
            ds_path = os.path.join(raw_dir, ds)
            os.makedirs(ds_path, exist_ok=True)
            folder_paths[f"RAW_{ds}"] = ds_path

        return folder_paths

    @staticmethod
    def check_drive_storage(drive_path: str = "/content/drive/MyDrive") -> Dict[str, Any]:
        """
        Queries disk usage to confirm available storage on the 5 TB Google Drive account.
        """
        if not os.path.exists(drive_path):
            return {
                "mounted": False,
                "message": f"Path '{drive_path}' does not exist. Mount Google Drive first.",
            }

        total, used, free = shutil.disk_usage(drive_path)
        return {
            "mounted": True,
            "path": drive_path,
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "free_gb": round(free / (1024 ** 3), 2),
            "total_tb": round(total / (1024 ** 4), 2),
            "free_tb": round(free / (1024 ** 4), 2),
            "status": "HEALTHY_5TB_CAPACITY" if (total / (1024 ** 4)) >= 2.0 else "STANDARD_QUOTA",
        }

    @staticmethod
    def compute_sha256(filepath: str) -> str:
        """Computes SHA-256 hash of a file for cryptographic verification."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(1048576), b""):  # 1 MB blocks
                sha256.update(chunk)
        return sha256.hexdigest()

    def download_file_resumable(
        self,
        url: str,
        dest_path: str,
        expected_sha256: Optional[str] = None,
        max_retries: int = 5,
        timeout_sec: int = 60,
    ) -> Tuple[bool, str]:
        """
        Resumable download with HTTP Range header support and retry logic.
        Avoids re-downloading if complete file already exists and passes SHA-256.
        """
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        if os.path.exists(dest_path) and expected_sha256:
            calc_hash = self.compute_sha256(dest_path)
            if calc_hash.lower() == expected_sha256.lower():
                return True, f"File already exists and passed SHA-256 verification: {dest_path}"

        for attempt in range(1, max_retries + 1):
            try:
                downloaded_bytes = 0
                open_mode = "wb"
                headers = {"User-Agent": "Mozilla/5.0 (rPPG Research FYP Cloud Downloader)"}

                if os.path.exists(dest_path):
                    downloaded_bytes = os.path.getsize(dest_path)
                    if downloaded_bytes > 0:
                        headers["Range"] = f"bytes={downloaded_bytes}-"
                        open_mode = "ab"

                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout_sec) as response, open(dest_path, open_mode) as out_file:
                    content_length = response.getheader("Content-Length")
                    total_expected = (int(content_length) + downloaded_bytes) if content_length else None

                    block_size = 1048576  # 1 MB
                    while True:
                        chunk = response.read(block_size)
                        if not chunk:
                            break
                        out_file.write(chunk)

                # Checksum verification if expected
                if expected_sha256:
                    calc_hash = self.compute_sha256(dest_path)
                    if calc_hash.lower() != expected_sha256.lower():
                        if attempt < max_retries:
                            time.sleep(2)
                            continue
                        return False, f"SHA-256 mismatch: expected {expected_sha256}, got {calc_hash}"

                return True, f"Download successful: {dest_path}"

            except Exception as e:
                if attempt == max_retries:
                    return False, f"Download failed after {max_retries} attempts: {str(e)}"
                time.sleep(attempt * 2)

        return False, "Unknown download termination"

    def audit_downloaded_dataset(self, dataset_dir: str) -> Dict[str, Any]:
        """
        Scans a downloaded dataset directory on Google Drive:
        - Counts total video files and reference files
        - Tests video decodability with OpenCV
        - Calculates total directory size
        """
        if not os.path.exists(dataset_dir):
            return {"exists": False, "status": "NOT_DOWNLOADED"}

        video_exts = {".avi", ".mp4", ".mov", ".mkv", ".png"}
        label_exts = {".txt", ".csv", ".mat", ".json", ".h5"}

        total_bytes = 0
        video_files = []
        label_files = []
        corrupted_videos = []
        valid_videos = []

        for root, _, files in os.walk(dataset_dir):
            for file in files:
                f_path = os.path.join(root, file)
                total_bytes += os.path.getsize(f_path)
                ext = os.path.splitext(file)[1].lower()

                if ext in video_exts:
                    video_files.append(f_path)
                    # Verify decodability for video containers
                    if ext != ".png":
                        cap = cv2.VideoCapture(f_path)
                        if cap.isOpened():
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                valid_videos.append(f_path)
                            else:
                                corrupted_videos.append(f_path)
                            cap.release()
                        else:
                            corrupted_videos.append(f_path)
                    else:
                        valid_videos.append(f_path)

                elif ext in label_exts:
                    label_files.append(f_path)

        return {
            "exists": True,
            "path": dataset_dir,
            "total_size_mb": round(total_bytes / (1024 ** 2), 2),
            "total_size_gb": round(total_bytes / (1024 ** 3), 3),
            "video_count": len(video_files),
            "valid_videos_count": len(valid_videos),
            "corrupted_videos_count": len(corrupted_videos),
            "label_count": len(label_files),
            "integrity_status": "VERIFIED_VALID" if len(corrupted_videos) == 0 and len(valid_videos) > 0 else (
                "CORRUPTIONS_FOUND" if len(corrupted_videos) > 0 else "EMPTY_OR_NO_VIDEOS"
            ),
        }

