# Public rPPG Dataset Compatibility and Modality Matrix

This document provides a comprehensive, scientifically verified analysis of publicly available facial video datasets for Remote Photoplethysmography (rPPG).

## 1. Summary Matrix

| Dataset | Subjects | Camera Hardware | Acquisition Conditions | Ground Truth Device | Heart Rate (HR) | Respiratory Rate (RR) | SpO2 | Blood Pressure (BP) | Primary Research Utility |
| :--- | :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **UBFC-rPPG** | 42 | Logitech C920 (640x480 @ 30 fps, uncompressed 8-bit) | Indoor office, ambient fluorescent, resting & math stress | Contec CMS50E Pulse Oximeter | **YES** (BVP + HR) | **NO** | **YES** (Discrete baseline) | **NO** | Standard baseline for POS algorithm HR accuracy |
| **PURE** | 10 | Eco274CVGE industrial RGB (640x480 @ 30 fps, PNG) | Halogen lighting, 6 tasks (steady, speech, rotation) | CMS50E Finger Pulse Oximeter | **YES** (60 Hz BVP) | **NO** | **YES** (60 Hz SpO2) | **NO** | Head motion robustness and optical ratio analysis |
| **COHFACE** | 40 | Logitech HD C525 (640x480 @ 20 fps, MPEG-4) | Studio light & natural window light | Thought Tech BioGraph Infiniti (PPG + Chest Belt) | **YES** (256 Hz PPG) | **YES** (Respiration Belt) | **NO** | **NO** | Video compression impact and respiratory rate validation |
| **VIPL-HR** | 107 | Webcam, smartphone, RealSense F200 (RGB-D) | 9 scenarios (bright, dim, uneven, motion) | Contec CMS60C Sensor | **YES** (50 Hz BVP) | **NO** | **YES** (Pulse oximeter) | **NO** | Cross-sensor generalizability & low-illumination performance |
| **MMPD** | 33 | Samsung Galaxy S22 Ultra (1280x720 @ 30 fps) | 4 lights, 4 motions, mobile optics | HKH-11C Finger Pulse Sensor | **YES** (200 Hz PPG) | **YES** (Derived) | **YES** (Pulse oximeter) | **NO** | Fitzpatrick skin tone diversity (Types 3–6) on mobile phones |

---

## 2. Critical Findings Regarding Blood Pressure & Respiratory Reference Labels

### 2.1 Absence of Continuous Blood Pressure Ground Truth in Public Video Cohorts
None of the canonical public rPPG datasets (**UBFC-rPPG**, **PURE**, **COHFACE**, **VIPL-HR**, or **MMPD**) contain paired continuous arterial blood pressure (ABP) or automated oscillometric cuff measurements.
* **Biomedical Implication**: Validating non-contact blood pressure requires a specialized paired protocol where reference sphygmomanometer readings are recorded synchronously with facial video.
* **System Safeguard**: Our system flags all optical blood pressure outputs as `EXPERIMENTAL_RESEARCH` per ISO 81060-2 and requires individual baseline calibration.

### 2.2 Respiratory Rate Reference Ground Truth
* **COHFACE** is the primary public dataset providing true thoracic strain-gauge respiration belt data.
* Datasets lacking respiratory reference labels cannot be used for independent RR validation.

---

## 3. Dataset Integration & Evaluation Commands

The backend includes a dedicated evaluation pipeline:
```bash
# Run automated benchmark evaluation on POS algorithm
curl -X POST "http://localhost:8000/api/v1/datasets/benchmark-run" \
     -H "Content-Type: application/json" \
     -d '{"test_bpm_values": [55.0, 68.0, 75.0, 88.0, 102.0, 120.0], "snr_db": 10.0, "duration_sec": 15.0}'
```
Returns:
* **Mean Absolute Error (MAE)** (BPM)
* **Root Mean Square Error (RMSE)** (BPM)
* **Pearson Correlation Coefficient ($r$)**
* **Bland-Altman 95% Limits of Agreement**
