# DATASET METADATA REPORT: rPPG PHYSIOLOGICAL BENCHMARKS
**Project Title:** Development and Validation of an rPPG-Based System for Non-Contact Vital Sign Monitoring  
**Document Code:** BME-FYP-DS-META-001  
**Storage Tier:** Google Drive (`RPPG_FYP/02_DATASET_METADATA/`)  

---

## 1. Overview & Dataset Portfolio

This report documents the physiological ground truth, sensor modalities, video acquisition parameters, and participant demographics across the six target benchmark datasets for the Final Year Project.

```
RPPG_FYP/
├── 01_RAW_DATASETS/
│   ├── UBFC-rPPG/
│   ├── PURE/
│   ├── COHFACE/
│   ├── VIPL-HR/
│   ├── MMPD/
│   └── BP4D_PLUS/
└── 02_DATASET_METADATA/
    ├── Dataset_Inventory.csv
    ├── DATASET_METADATA_REPORT.md
    └── download_verification_report.json
```

---

## 2. In-Depth Dataset Metadata Profiles

### 2.1 UBFC-rPPG (University of Bourgogne Franche-Comté)
* **Citation:** Bobbia et al., "Unsupervised skin tissue segmentation for remote photoplethysmography", *Computer Vision and Image Understanding*, 2019.
* **Camera Sensor:** Logitech C920 HD Pro Webcam.
* **Optical Resolution:** $640 \times 480$ pixels (uncompressed raw 8-bit RGB AVI).
* **Frame Rate:** Constant $30.0\text{ fps}$.
* **Subjects:** $N=42$ participants (undergraduate students).
* **Demographics:** Primarily young adults (18–30 years), Fitzpatrick phototypes II and III.
* **Illumination:** Indoor office fluorescent illumination ($~300\text{ lux}$).
* **Reference Hardware:** Contec Medical CMS50E transmissive finger pulse oximeter.
* **Ground-Truth Modalities:**
  * Heart Rate (HR): Continuous Blood Volume Pulse (BVP) trace and sample-level HR.
  * Respiratory Rate (RR): **Absent**.
  * $\text{SpO}_2$: Discrete percentage values ($97\%$–$99\%$).
  * Blood Pressure (BP): **Absent**.
* **Estimated Dataset Size:** $\sim 15\text{ GB}$.

### 2.2 PURE (Pulse Rate Estimation from Facial Videos)
* **Citation:** Stricker et al., "Non-contact video-based pulse rate measurement on a mobile service robot", *Biomedical Optics Express*, 2014.
* **Camera Sensor:** Eco274CVGE industrial RGB camera (Sony ICX274 CCD sensor).
* **Optical Resolution:** $640 \times 480$ pixels.
* **Video Encoding:** Lossless sequence of 24-bit PNG image frames.
* **Frame Rate:** Exactly $30.0\text{ fps}$ (hardware shutter trigger).
* **Subjects:** $N=10$ participants (8 male, 2 female).
* **Scenarios:** 6 distinct motion conditions per subject (Steady, Talking, Slow/Fast Translation, Small/Medium Head Rotation).
* **Reference Hardware:** CMS50E transmissive pulse oximeter.
* **Ground-Truth Modalities:**
  * Heart Rate (HR): Continuous PPG pulse waveform ($60\text{ Hz}$) and instantaneous pulse rate.
  * Respiratory Rate (RR): **Absent**.
  * $\text{SpO}_2$: Continuous oxygen saturation percentage ($60\text{ Hz}$).
  * Blood Pressure (BP): **Absent**.
* **Estimated Dataset Size:** $\sim 120\text{ GB}$ (uncompressed PNG sequences).

### 2.3 COHFACE (Idiap Research Institute)
* **Citation:** Heusch et al., "Reproducible research in remote photoplethysmography: a benchmark study", *Idiap Research Report*, 2017.
* **Camera Sensor:** Logitech HD C525.
* **Optical Resolution:** $640 \times 480$ pixels.
* **Video Encoding:** MPEG-4 Part 2 compressed AVI.
* **Frame Rate:** $20.0\text{ fps}$.
* **Subjects:** $N=40$ participants.
* **Reference Hardware:** Thought Technology BioGraph Infiniti medical data acquisition system.
* **Ground-Truth Modalities:**
  * Heart Rate (HR): Continuous finger Blood Volume Pulse (BVP) at $256\text{ Hz}$.
  * Respiratory Rate (RR): **Continuous thoracic respiration strain gauge belt signal at $256\text{ Hz}$**.
  * $\text{SpO}_2$: **Absent**.
  * Blood Pressure (BP): **Absent**.
* **Estimated Dataset Size:** $\sim 3\text{ GB}$.

### 2.4 VIPL-HR (Visual-Optical Physiological Laboratory)
* **Citation:** Niu et al., "VIPL-HR: A Multi-modal Database for Remote Physiological Measurement", *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 2019.
* **Camera Sensors:** Three concurrent cameras: Logitech C920 webcam, front/rear smartphone cameras, and Intel RealSense F200 RGB-D camera.
* **Optical Resolution:** $640 \times 480$ up to $1920 \times 1080$.
* **Frame Rate:** $25.0$ to $30.0\text{ fps}$ variable.
* **Subjects:** $N=107$ participants (79 male, 28 female).
* **Illumination Scenarios:** 9 realistic conditions (dim lighting, strong side illumination, exercise, motion).
* **Reference Hardware:** Contec CMS60C BVP/SpO2 sensor and digital blood pressure cuff.
* **Ground-Truth Modalities:**
  * Heart Rate (HR): Continuous BVP and instantaneous pulse rate.
  * Respiratory Rate (RR): **Absent**.
  * $\text{SpO}_2$: Continuous pulse oximeter percentage.
  * Blood Pressure (BP): **Baseline resting Systolic and Diastolic blood pressure measurements available for a subset of participants**.
* **Estimated Dataset Size:** $\sim 70\text{ GB}$.

### 2.5 MMPD (Multi-Domain Mobile Video Physiology Dataset)
* **Citation:** Tang et al., "MMPD: Multi-Domain Mobile Video Physiology Dataset", *NeurIPS*, 2023.
* **Camera Sensor:** Samsung Galaxy S22 Ultra mobile phone front/rear cameras.
* **Optical Resolution:** $1280 \times 720$ pixels.
* **Video Encoding:** H.264 compressed MP4.
* **Frame Rate:** $30.0\text{ fps}$.
* **Subjects:** $N=33$ participants.
* **Illumination Scenarios:** 4 conditions (LED, incandescent, fluorescent, natural daylight) across stationary and motion protocols.
* **Reference Hardware:** HKH-11C high-precision finger pulse sensor and respiration chest band.
* **Ground-Truth Modalities:**
  * Heart Rate (HR): Continuous PPG sensor waveform ($200\text{ Hz}$).
  * Respiratory Rate (RR): **Continuous thoracic respiration waveform ($200\text{ Hz}$)**.
  * $\text{SpO}_2$: **Absent**.
  * Blood Pressure (BP): **Absent**.
* **Estimated Dataset Size:** $\sim 18\text{ GB}$.

### 2.6 BP4D+ (Binghamton-Pittsburgh 4D Spontaneous Multimodal Corpus)
* **Citation:** Zhang et al., "BP4D+: An expanded multimodal database for emotional and physiological analysis", *Image and Vision Computing*, 2016.
* **Camera Sensor:** High-speed 3D stereoscopic and 2D high-definition color imaging system.
* **Optical Resolution:** $1040 \times 1392$ color video.
* **Frame Rate:** $25.0\text{ fps}$.
* **Subjects:** $N=140$ participants.
* **Reference Hardware:** Biopac physiological data acquisition system.
* **Ground-Truth Modalities:**
  * Heart Rate (HR): 3-lead ECG ($1000\text{ Hz}$).
  * Respiratory Rate (RR): Continuous respiratory effort belt ($1000\text{ Hz}$).
  * $\text{SpO}_2$: **Absent**.
  * Blood Pressure (BP): **Continuous beat-to-beat non-invasive arterial blood pressure (SBP & DBP at $1000\text{ Hz}$)**.
* **Estimated Dataset Size:** $\sim 2.2\text{ TB}$.

---

## 3. Physiological Ground Truth Mapping Across the 4 Pipelines

| Physiological Pipeline | Primary Training & Benchmarking Datasets | Reason & Reference Instrument |
| :--- | :--- | :--- |
| **Pipeline 1: Heart Rate (HR)** | UBFC-rPPG, PURE, MMPD, VIPL-HR, COHFACE | Verified continuous PPG / BVP and ECG references across all datasets. |
| **Pipeline 2: Respiratory Rate (RR)** | COHFACE, MMPD, BP4D+ | Synchronized thoracic strain gauge chest effort belt references ($200$–$1000\text{ Hz}$). |
| **Pipeline 3: $\text{SpO}_2$** | UBFC-rPPG, PURE, VIPL-HR | Dual-channel pulse oximeter reference percentages ($60\text{ Hz}$). |
| **Pipeline 4: Blood Pressure (BP)** | BP4D+ (Continuous), VIPL-HR (Resting Subset) | Synchronized beat-to-beat arterial line or oscillometric cuff blood pressure references. |

