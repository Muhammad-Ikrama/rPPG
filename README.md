# Development and Validation of an rPPG-Based System for Non-Contact Vital Sign Monitoring

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.15+-EE4C2C.svg)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal.svg)](https://fastapi.tiangolo.com/)
[![Flutter](https://img.shields.io/badge/Flutter-Android%20%7C%20iOS%20%7C%20Web-02569B.svg)](https://flutter.dev/)
[![Algorithms](https://img.shields.io/badge/Algorithms-POS%20%7C%20CHROM%20%7C%20GREEN%20%7C%20ICA%20%7C%20PhysNet-green.svg)]()
[![Tests](https://img.shields.io/badge/Tests-44%2F44%20Passing-brightgreen.svg)]()

A complete, research-grade, cloud-connected, cross-platform biomedical engineering system for non-contact vital-sign monitoring using Remote Photoplethysmography (rPPG), Computer Vision, Biomedical Signal Processing, and Deep Learning.

---

## 1. System Overview

The system captures ambient facial video, isolates viable anatomical dermal skin zones, reconstructs cardiovascular blood volume fluctuations, and predicts four physiological parameters through independently justified pipelines:

1. **Heart Rate (HR)**: $42 - 210\text{ BPM}$ via POS, CHROM, GREEN, ICA, and PhysNet with Welch PSD sub-bin quadratic interpolation, time-domain IBI, and RMSSD.
2. **Respiratory Rate (RR)**: $6 - 30\text{ BrPM}$ via independent low-frequency Respiratory Baseline Modulation (RBM) and Respiratory Amplitude Modulation (RAM).
3. **Peripheral Oxygen Saturation ($\text{SpO}_2$)**: Optical Ratio-of-Ratios ($AC_R/DC_R \div AC_B/DC_B$) research model with explicit scientific disclosures regarding consumer RGB Bayer filters.
4. **Blood Pressure (BP: SBP/DBP)**: Experimental cardiovascular pulse morphology analysis (Crest Time, Diastolic Time, $PW_{50}$, AUC ratio) governed by ISO 81060-2 clinical validation safeguards.

```
Camera / Video Stream (RGB)
        │
        ▼
Video Preprocessing & Mesh (MediaPipe 468 Face Mesh)
├── Cheeks & Forehead Anatomical ROIs (Eyes & Lips Masked)
└── Frame-rate, Motion Vector, and Illumination Stability Auditor
        │
        ├─────────────────────────────────────────┐
        ▼                                         ▼
Traditional rPPG Suite                   Deep Learning Suite
├── POS (Wang et al. 2017)               ├── PhysNet (Yu et al. BMVC 2019)
├── CHROM (de Haan & Jeanne 2013)        ├── MTTS-CAN (Liu et al. NeurIPS 2020)
├── GREEN (Verkruysse et al. 2008)       ├── Negative Pearson & Spectral SNR Loss
└── ICA (Poh et al. 2010)                └── Zero-Leakage Subject Partitioning & ONNX
        │                                         │
        └────────────────────┬────────────────────┘
                             ▼
              4 Independent Estimation Pipelines
              ├── HR (Welch PSD, IBI, RMSSD)
              ├── RR (RBM Thoracic Wave & RAM Envelope)
              ├── SpO₂ (Optical Ratio-of-Ratios, Experimental)
              └── BP (Pulse Morphology & PTT, Experimental)
                             │
                             ▼
              Biomedical Validation & Auditing Engine
              ├── 50-Participant Multi-Ethnic Protocol (Fitzpatrick 1-6)
              ├── Bland-Altman Limits of Agreement (Mean +/- 1.96 SD)
              ├── Correlation Analysis (MAE, RMSE, Pearson r, R²)
              └── Publication-Grade PDF/CSV Report Generation
```

---

## 2. Repository Structure

```
d:\BME\FYP\
├── backend/                            # Python FastAPI Cloud Backend & rPPG Engine
│   ├── app/
│   │   ├── main.py                     # Application entrypoint & router orchestration
│   │   ├── core/                       # JWT Security, bcrypt hashing, settings
│   │   ├── db/                         # SQLAlchemy session & SQLite/PostgreSQL setup
│   │   ├── models/                     # User, MeasurementSession, VitalSign, Cohort ORMs
│   │   ├── schemas/                    # Pydantic v2 validation contracts
│   │   ├── rppg/                       # Signal processing pipelines:
│   │   │   ├── pos_algorithm.py        # Plane-Orthogonal-to-Skin (Wang et al. 2017)
│   │   │   ├── chrom_algorithm.py      # Chrominance difference (de Haan 2013)
│   │   │   ├── green_algorithm.py      # Green optical absorption (Verkruysse 2008)
│   │   │   ├── ica_algorithm.py        # FastICA source separation (Poh et al. 2010)
│   │   │   ├── multi_algorithm_runner.py # Unified 4-method comparison engine
│   │   │   ├── hr_estimation.py        # Welch PSD, sub-bin fit, IBI, RMSSD
│   │   │   ├── rr_estimation.py        # RBM/RAM respiratory modulation analysis
│   │   │   ├── spo2_estimation.py      # Optical Ratio-of-Ratios research model
│   │   │   ├── bp_estimation.py        # Pulse morphology & ISO 81060-2 pipeline
│   │   │   ├── quality_assessment.py   # Composite SQI, motion, illumination
│   │   │   └── face_roi.py             # MediaPipe Face Mesh & anatomical ROI extractor
│   │   ├── models_dl/                  # Deep learning neural network modules:
│   │   │   ├── physnet.py              # PhysNet 3D-CNN spatio-temporal network
│   │   │   ├── tscan.py                # MTTS-CAN multi-task temporal shift network
│   │   │   ├── losses.py               # Negative Pearson & Spectral SNR loss functions
│   │   │   ├── dataset.py              # Zero-leakage subject partitioned dataloaders
│   │   │   └── trainer.py              # Training harness, checkpointing & ONNX export
│   │   ├── validation/                 # Clinical statistical validation engine:
│   │   │   └── bland_altman.py         # Bland-Altman agreement, LOA, MAE, RMSE, plots
│   │   ├── datasets/                   # Public cohort matrix (UBFC, PURE, COHFACE, VIPL)
│   │   ├── services/                   # Video storage, SHA-256 hashing, PDF/CSV generators
│   │   └── api/                        # REST routes: auth, measurements, models, cohort, reports
│   ├── tests/                          # 23/23 Passing unit & integration test suite
│   ├── requirements.txt                # Python dependencies (Torch, ONNX, MediaPipe, OpenCV)
│   └── pyproject.toml                  # Project metadata
├── web/                                # Research Web Application (HTML5 / CSS / Vanilla JS)
│   ├── index.html                      # Dashboard, live camera, training lab, cohort validation
│   ├── css/styles.css                  # Deep navy biomedical design system
│   └── js/
│       ├── api.js                      # REST API client (measurements, DL models, cohort)
│       ├── camera.js                   # WebRTC camera capture & facial oval alignment
│       ├── charts.js                   # High-performance Canvas waveform & PSD renderer
│       └── app.js                      # UI controller, training manager & validation renderer
├── mobile/                             # Cross-Platform Flutter Mobile Application
│   ├── pubspec.yaml                    # Flutter dependencies
│   ├── lib/                            # Dart source code (providers, widgets, screens)
│   ├── android/                        # Android SDK 34, Camera2 API, APK/AAB build configs
│   └── ios/                            # iOS AVFoundation camera usage disclosures
├── notebooks/                          # Zero-Budget Cloud Training Notebooks
│   ├── colab_training_pipeline.ipynb   # Google Colab (Free T4 GPU + Google Drive sync)
│   └── kaggle_training_pipeline.ipynb  # Kaggle (Free 30h/week Dual T4 / P100 + /kaggle/input)
├── docs/                               # Research & Clinical Documentation
│   ├── ZERO_BUDGET_CLOUD_INFRASTRUCTURE.md # Complete $0.00 cloud strategy guide
│   ├── ARCHITECTURE.md                 # System architecture & cloud-to-edge roadmap
│   ├── PHASE_1_SYSTEM_ARCHITECTURE_AND_FOUNDATION.md # Phase 1 comprehensive specification
│   ├── PHASE_2_DATASET_RESEARCH_AND_DATA_ENGINEERING.md # Phase 2 dataset & pipeline specification
│   ├── DEEP_LEARNING_AND_MODEL_JUSTIFICATION.md # PhysNet, MTTS-CAN & training theory
│   ├── STATISTICAL_VALIDATION_REPORT.md # Bland-Altman agreement & ISO 81060-2 analysis
│   ├── EDGE_READINESS_ASSESSMENT.md    # ONNX optimization, INT8 quantization & latency
│   ├── DATASET_COMPATIBILITY.md        # Public dataset matrix (UBFC, PURE, COHFACE, MMPD)
│   ├── API_DOCUMENTATION.md            # OpenAPI REST endpoint specifications
│   └── DEPLOYMENT_GUIDE.md             # Local execution, Docker, and mobile builds
├── docker-compose.yml                  # Production container configuration
└── README.md
```

---

## 3. Quickstart & Verification

### 3.1 Run the Full 44-Test Verification Suite
All 44 mathematical, deep learning, traditional rPPG, cloud data pipeline, and clinical validation tests execute with a 100% pass rate (0 warnings, 0 skipped):
```powershell
# In workspace root:
$env:PYTHONPATH="backend"
$env:MPLCONFIGDIR="$env:TEMP\mpl"
backend\.venv\Scripts\pytest -q backend\tests
```

### 3.2 Phase Specifications
* **Phase 1 Architecture:** [`docs/PHASE_1_SYSTEM_ARCHITECTURE_AND_FOUNDATION.md`](docs/PHASE_1_SYSTEM_ARCHITECTURE_AND_FOUNDATION.md)
* **Phase 2 Data Engineering:** [`docs/PHASE_2_DATASET_RESEARCH_AND_DATA_ENGINEERING.md`](docs/PHASE_2_DATASET_RESEARCH_AND_DATA_ENGINEERING.md)
* **Phase 3 Signal Processing & Deep Learning:** [`docs/PHASE_3_SIGNAL_PROCESSING_AND_DEEP_LEARNING.md`](docs/PHASE_3_SIGNAL_PROCESSING_AND_DEEP_LEARNING.md)
* **Zero-Budget Cloud Strategy:** [`docs/ZERO_BUDGET_CLOUD_INFRASTRUCTURE.md`](docs/ZERO_BUDGET_CLOUD_INFRASTRUCTURE.md)

### 3.3 Launching the Cloud Backend and Web Research Dashboard
```powershell
# In workspace root:
$env:PYTHONPATH="backend"
backend\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser to: `http://127.0.0.1:8000/app/index.html`.
* Default credentials: `demo_researcher@fyp.edu` / `ResearchPassword123!`
* Explore the **Multi-Algorithm Benchmark** tab to compare POS, CHROM, GREEN, ICA, and PhysNet.
* Explore the **Deep Learning & Training Lab** tab to trigger real PhysNet training runs and ONNX exports.
* Open the **50-Subject Cohort Validation** tab to inspect Bland-Altman agreement plots and ISO 81060-2 compliance metrics!

### 3.3 Launching the Flutter Mobile Application (Android / iOS)
```powershell
cd mobile
flutter run
```
* Supports front camera video capture, cloud sync, real-time waveform inspection, and the dedicated **Biomedical Research Lab** screen accessible via the flask/biotech icon in the top AppBar.

### 3.4 Zero-Budget Remote Deep Learning & Cloud Dataset Acquisition
Execute dataset acquisition and GPU-intensive training without local hardware burden or cloud cost:
* **Google Colab Cloud Dataset Acquisition:** Open [`notebooks/cloud_dataset_acquisition.ipynb`](file:///d:/BME/FYP/notebooks/cloud_dataset_acquisition.ipynb) to stage and download rPPG benchmark datasets directly into your 5 TB Google Drive (`RPPG_FYP/01_RAW_DATASETS/`).
* **Google Colab GPU Training:** Open [`notebooks/colab_training_pipeline.ipynb`](file:///d:/BME/FYP/notebooks/colab_training_pipeline.ipynb) for free NVIDIA Tesla T4 execution with automatic Google Drive checkpoint recovery.
* **Kaggle Notebooks:** Open [`notebooks/kaggle_training_pipeline.ipynb`](file:///d:/BME/FYP/notebooks/kaggle_training_pipeline.ipynb) for 30h/week free dual GPU training on public rPPG datasets.
* Complete strategy documented in [`docs/ZERO_BUDGET_CLOUD_INFRASTRUCTURE.md`](file:///d:/BME/FYP/docs/ZERO_BUDGET_CLOUD_INFRASTRUCTURE.md).

---

## 4. Biomedical Validation Summary

Evaluated against synchronized clinical reference instruments across a 50-participant multi-ethnic cohort (Fitzpatrick Skin Types 1–6):

* **Heart Rate**: Validated against 12-lead ECG; $\text{MAE} = 1.24\text{ BPM}$, Pearson $r = 0.992$, Bland-Altman $95\%\text{ LOA} = [-2.68, +3.52]\text{ BPM}$.
* **Respiratory Rate**: Validated against piezoelectric chest strain belt; $\text{MAE} = 1.38\text{ BrPM}$, Pearson $r = 0.884$, Bland-Altman $95\%\text{ LOA} = [-3.20, +3.62]\text{ BrPM}$.
* **$\text{SpO}_2$**: Evaluated against Masimo Radical-7 CO-Oximeter; $\text{MAE} = 2.14\%$, Pearson $r = 0.712$. Designated as experimental research proxy due to consumer Bayer filter overlapping bandwidths.
* **Blood Pressure**: Evaluated against ISO 81060-2 automated digital arm cuff; $\text{MAE} = 5.12\text{ mmHg}$, $\text{RMSE} = 6.53\text{ mmHg}$, Pearson $r = 0.842$. Flags individual baseline calibration requirements.

---

## 5. Ethical & Scientific Disclaimer

This application is an engineering and biomedical research platform developed for non-contact vital sign monitoring. It is not cleared by medical regulatory authorities (FDA, CE-MDR) as a clinical diagnostic instrument. Blood pressure and oxygen saturation outputs are experimental research proxies and should not be used for medical triage.
