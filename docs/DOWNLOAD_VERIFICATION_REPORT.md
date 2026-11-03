# DOWNLOAD VERIFICATION & DATA INTEGRITY REPORT
**Project Title:** Development and Validation of an rPPG-Based System for Non-Contact Vital Sign Monitoring  
**Document Code:** BME-FYP-VERIF-001  
**Storage Tier:** Google Drive (`RPPG_FYP/02_DATASET_METADATA/download_verification_report.json`)  

---

## 1. Quality Assurance & Verification Methodology

To guarantee research reproducibility and prevent training failures caused by truncated video files or corrupted ground truth, all dataset downloads into Google Drive execute through a strict 5-stage verification protocol:

```
[ Download Stream ]
        │
        ▼
[ Stage 1: Cryptographic SHA-256 Checksum ]  ───► Match official publisher digest?
        │
        ▼
[ Stage 2: Container Decodability Check ]     ───► OpenCV cv2.VideoCapture() probe
        │
        ▼
[ Stage 3: Frame Rate & Drop Auditing ]       ───► Decoded frames vs. container headers
        │
        ▼
[ Stage 4: Ground Truth Pairing Audit ]       ───► BVP/PPG signal paired for every video?
        │
        ▼
[ Stage 5: Google Drive Atomic Move ]         ───► Persist to 01_RAW_DATASETS/{Dataset}/
```

---

## 2. Verification Protocol Details

### 2.1 Cryptographic SHA-256 Checksum Verification
* **Objective:** Detect silent network bit corruption and incomplete archive downloads.
* **Implementation:** The file is streamed through `hashlib.sha256()` in $1\text{ MB}$ chunks. The resulting 64-character hexadecimal digest is compared against the published archive manifest.
* **Failure Handling:** If the digest does not match, the file is retained in ephemeral staging, an automated retry is triggered up to 5 times with HTTP range offsets, and if still failing, the file is quarantined.

### 2.2 OpenCV Container Decodability Audit
* **Objective:** Ensure video containers (AVI, MP4, MOV) are fully decodable by standard computer vision pipelines.
* **Implementation:** The script instantiates `cv2.VideoCapture()` on the cloud runtime, verifies `cap.isOpened() == True`, and reads the initial and terminal frames.
* **Failure Handling:** Files that fail to open or yield zero decodable frames are flagged as `CORRUPTED_CONTAINER` in the inventory CSV and excluded from training dataloaders.

### 2.3 Dropped Frame & Timestamp Monotonicity Auditing
* **Objective:** Detect frame drops that disrupt the Nyquist sampling criterion for heart rate ($f_s \ge 2 \cdot f_{\max} = 2 \cdot 3.5\text{ Hz} = 7\text{ Hz}$) and distort respiratory frequency analysis.
* **Implementation:** The total decoded frame count is compared with the duration reported in the video header ($\Delta N = N_{\text{container}} - N_{\text{decoded}}$). Any discrepancy $> 1.0\%$ is recorded as a data quality flag.

### 2.4 Ground-Truth Pairing Audit
* **Objective:** Verify that every video file is matched with a corresponding physiological ground truth file.
* **Implementation:** A pairing scanner verifies that for each `video_xxx`, a corresponding `ground_truth_xxx.txt` or `.mat` file exists in the directory. Missing labels are explicitly recorded as `MISSING_GROUND_TRUTH` rather than being filled with synthetic estimates.

---

## 3. Machine-Readable Download Verification Report Schema

The automated Google Colab acquisition pipeline records its findings into `RPPG_FYP/02_DATASET_METADATA/download_verification_report.json`:

```json
{
  "timestamp": "2026-03-01T12:00:00Z",
  "storage_destination": "/content/drive/MyDrive/RPPG_FYP/01_RAW_DATASETS",
  "drive_capacity": {
    "total_tb": 5.0,
    "free_tb": 4.82,
    "status": "HEALTHY_5TB_CAPACITY"
  },
  "dataset_audits": {
    "UBFC-rPPG": {
      "exists": true,
      "total_size_gb": 15.2,
      "video_count": 42,
      "valid_videos_count": 42,
      "corrupted_videos_count": 0,
      "label_count": 42,
      "integrity_status": "VERIFIED_VALID"
    },
    "MMPD": {
      "exists": true,
      "total_size_gb": 18.4,
      "video_count": 660,
      "valid_videos_count": 660,
      "corrupted_videos_count": 0,
      "label_count": 660,
      "integrity_status": "VERIFIED_VALID"
    }
  }
}
```

