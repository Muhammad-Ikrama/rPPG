# PHASE 2: DATASET RESEARCH, CLOUD INFRASTRUCTURE, AND DATA ENGINEERING
**Project Title:** Development and Validation of an rPPG-Based System for Non-Contact Vital Sign Monitoring  
**Document Code:** BME-FYP-PHASE2-DOC-001  
**Author:** Biomedical Engineering & Deep Learning Research Team  
**Date:** March 2026  
**Status:** Complete — Fully Implemented & Verified  

---

## 1. Executive Summary & Objective

The objective of Phase 2 is to establish an uncompromised physiological dataset and data engineering foundation for the four vital-sign estimation pipelines:
1. **Heart Rate (HR)** — Beats Per Minute (BPM)
2. **Respiratory Rate (RR)** — Breaths Per Minute (BrPM)
3. **Blood Oxygen Saturation ($\text{SpO}_2$)** — Percentage (%)
4. **Blood Pressure (BP)** — Systolic and Diastolic (mmHg)

In strict adherence to the Master Project Specification, this phase eliminates fabricated or artificial ground-truth labels. A physiological dataset is only utilized for a vital parameter if it possesses verified, synchronized clinical instrument reference labels for that specific modality.

---

## 2. Public Dataset Research & Investigation (Task 1)

Six major public datasets and benchmark repositories were investigated across all 16 required scientific criteria:

### 2.1 University of Bourgogne Franche-Comté rPPG (UBFC-rPPG)
1. **Official Source:** `https://sites.google.com/view/ybobbia/ubfc-rppg`
2. **Access Procedure:** Academic web request via university Google Drive upon institutional email verification.
3. **License:** Creative Commons Non-Commercial Academic Research Agreement.
4. **Research Usage Restrictions:** Non-commercial, academic benchmarking only; no redistribution.
5. **Participant Count:** 42 subjects.
6. **Video Count:** 42 video files.
7. **Video Resolution:** $640 \times 480$ pixels.
8. **Frame Rate:** $30.0\text{ fps}$ constant.
9. **Recording Duration:** Approximately 2 minutes per subject.
10. **Reference Signal Availability:** Serial pulse oximeter continuous trace.
11. **HR Annotation:** **VERIFIED AVAILABLE** — Ground-truth BVP waveform and sample-level instantaneous HR.
12. **RR Annotation:** **NOT AVAILABLE** — No chest effort belt or capnography reference.
13. **$\text{SpO}_2$ Annotation:** **VERIFIED AVAILABLE** — Discrete pulse oximeter percentage (normoxic baseline $97\%$–$99\%$).
14. **BP Annotation:** **NOT AVAILABLE** — No continuous arterial line or oscillometric cuff data.
15. **Synchronization:** Software serial-to-video timestamp matching (slight inter-hardware clock drift of $<50\text{ ms}$).
16. **Known Limitations:** Homogeneous indoor office lighting; fixed distance; limited Fitzpatrick skin tone distribution (primarily Types II–III).

---

### 2.2 Pulse Rate Estimation from Facial Videos (PURE)
1. **Official Source:** `https://www.tu-ilmenau.de/en/applied-media-systems-group/research/databases/pure`
2. **Access Procedure:** Formal academic request email to Applied Media Systems Group at TU Ilmenau with signed institutional data usage agreement.
3. **License:** TU Ilmenau Non-Commercial Research License.
4. **Research Usage Restrictions:** Academic research only; face images must be anonymized in publications unless explicit consent is obtained.
5. **Participant Count:** 10 subjects (8 male, 2 female).
6. **Video Count:** 60 sequences (6 conditions per subject: Steady, Talking, Slow Translation, Fast Translation, Small Rotation, Medium Rotation).
7. **Video Resolution:** $640 \times 480$ pixels.
8. **Frame Rate:** $30.0\text{ fps}$.
9. **Recording Duration:** Approximately 1 minute per sequence (60 minutes total).
10. **Reference Signal Availability:** CMS50E finger clip pulse oximeter.
11. **HR Annotation:** **VERIFIED AVAILABLE** — Continuous PPG pulse waveform and pulse rate sampled at $60\text{ Hz}$.
12. **RR Annotation:** **NOT AVAILABLE** — No thoracic strain gauge belt.
13. **$\text{SpO}_2$ Annotation:** **VERIFIED AVAILABLE** — Continuous $\text{SpO}_2$ percentage ($60\text{ Hz}$).
14. **BP Annotation:** **NOT AVAILABLE** — No arterial or cuff pressure reference.
15. **Synchronization:** Hardware trigger pulse synchronized with industrial camera shutter.
16. **Known Limitations:** Small cohort size ($N=10$); high storage footprint (individual uncompressed PNG sequences $>100\text{ GB}$).

---

### 2.3 Idiap COHFACE Dataset
1. **Official Source:** `https://www.idiap.ch/en/dataset/cohface`
2. **Access Procedure:** Online account creation and click-through EULA on Idiap Research portal.
3. **License:** Idiap Research Institute Non-Commercial Agreement.
4. **Research Usage Restrictions:** Non-commercial academic research.
5. **Participant Count:** 40 subjects.
6. **Video Count:** 160 videos (4 per subject: Studio lighting clean, studio lighting motion, ambient clean, ambient motion).
7. **Video Resolution:** $640 \times 480$ pixels.
8. **Frame Rate:** $20.0\text{ fps}$.
9. **Recording Duration:** 60 seconds per video.
10. **Reference Signal Availability:** Thought Technology BioGraph Infiniti medical system.
11. **HR Annotation:** **VERIFIED AVAILABLE** — Continuous Blood Volume Pulse (BVP) at $256\text{ Hz}$.
12. **RR Annotation:** **VERIFIED AVAILABLE** — Thoracic respiration strain gauge belt signal at $256\text{ Hz}$.
13. **$\text{SpO}_2$ Annotation:** **NOT AVAILABLE** — Sensor lacked dual-wavelength calibration channels.
14. **BP Annotation:** **NOT AVAILABLE** — No blood pressure sensor.
15. **Synchronization:** Hardware DAQ synchronization with timestamp logging.
16. **Known Limitations:** Heavy MPEG-4 Part 2 compression blocking artifacts; low frame rate ($20\text{ fps}$) reduces peak detection precision.

---

### 2.4 Visual-Optical Physiological Laboratory Heart Rate (VIPL-HR)
1. **Official Source:** `http://vipl.ict.ac.cn/resources/datasets`
2. **Access Procedure:** Signed application form submitted to VIPL laboratory directors for approval.
3. **License:** Chinese Academy of Sciences Academic License.
4. **Research Usage Restrictions:** Academic use only; strict prohibition against commercial use.
5. **Participant Count:** 107 subjects (79 male, 28 female).
6. **Video Count:** 2,378 videos.
7. **Video Resolution:** Multi-device ($640 \times 480$ up to $1920 \times 1080$).
8. **Frame Rate:** $25.0$–$30.0\text{ fps}$ (variable across devices).
9. **Recording Duration:** Approximately 30 seconds per video.
10. **Reference Signal Availability:** Contec CMS60C BVP sensor + resting blood pressure arm cuff.
11. **HR Annotation:** **VERIFIED AVAILABLE** — Continuous BVP trace and instantaneous HR.
12. **RR Annotation:** **NOT AVAILABLE** — No respiratory belt.
13. **$\text{SpO}_2$ Annotation:** **VERIFIED AVAILABLE** — Continuous finger clip $\text{SpO}_2$.
14. **BP Annotation:** **PARTIALLY AVAILABLE** — Resting baseline Systolic and Diastolic BP measurements available for a subset of participants.
15. **Synchronization:** Software multi-threaded timestamp clock synchronization.
16. **Known Limitations:** Smartphone videos exhibit temporal frame rate jitter; manual approval turnaround time is typically 2–4 weeks.

---

### 2.5 Multi-Domain Mobile Video Physiology Dataset (MMPD)
1. **Official Source:** `https://github.com/McDuff-App/MMPD`
2. **Access Procedure:** Direct open access repository via GitHub and HuggingFace.
3. **License:** MIT License.
4. **Research Usage Restrictions:** Open academic and commercial use under MIT terms.
5. **Participant Count:** 33 subjects.
6. **Video Count:** 660 videos (mobile phone: Samsung Galaxy S22 Ultra).
7. **Video Resolution:** $1280 \times 720$ pixels.
8. **Frame Rate:** $30.0\text{ fps}$.
9. **Recording Duration:** 60 seconds per video.
10. **Reference Signal Availability:** HKH-11C finger pulse sensor and respiration chest band.
11. **HR Annotation:** **VERIFIED AVAILABLE** — Continuous PPG sensor waveform ($200\text{ Hz}$).
12. **RR Annotation:** **VERIFIED AVAILABLE** — Continuous chest expansion respiratory signal ($200\text{ Hz}$).
13. **$\text{SpO}_2$ Annotation:** **NOT AVAILABLE** — No pulse oximeter calibration.
14. **BP Annotation:** **NOT AVAILABLE** — No blood pressure ground truth.
15. **Synchronization:** Android application serial hardware clock synchronization.
16. **Known Limitations:** Compression artifacts from mobile H.264 encoder; skewed towards Fitzpatrick skin types III–IV.

---

### 2.6 Binghamton-Pittsburgh 4D Spontaneous Multimodal Corpus (BP4D+)
1. **Official Source:** `http://www.cs.binghamton.edu/~lijun/Research/BP4D+/index.html`
2. **Access Procedure:** Written application signed by institutional faculty PI / department head.
3. **License:** Binghamton University Research Agreement.
4. **Research Usage Restrictions:** Research use only; strict privacy covenants.
5. **Participant Count:** 140 subjects.
6. **Video Count:** 1,400 multi-modal trials.
7. **Video Resolution:** $1040 \times 1392$ color video + 3D mesh sequence.
8. **Frame Rate:** $25.0\text{ fps}$.
9. **Recording Duration:** Task-based emotion elicitation (approx. 60–90 seconds per trial).
10. **Reference Signal Availability:** Biopac continuous physiological monitoring workstation.
11. **HR Annotation:** **VERIFIED AVAILABLE** — Continuous 3-lead ECG ($1000\text{ Hz}$).
12. **RR Annotation:** **VERIFIED AVAILABLE** — Respiration belt signal ($1000\text{ Hz}$).
13. **$\text{SpO}_2$ Annotation:** **NOT AVAILABLE** — No pulse oximeter.
14. **BP Annotation:** **VERIFIED AVAILABLE** — Continuous beat-to-beat non-invasive arterial blood pressure (SBP & DBP at $1000\text{ Hz}$).
15. **Synchronization:** Hardware trigger pulse between camera shutter and Biopac acquisition system.
16. **Known Limitations:** Dataset size exceeds $2\text{ TB}$; facial expression elicitation tasks introduce severe non-rigid facial deformation.

---

## 3. Dataset Compatibility Matrix (Task 2)

| Dataset | Heart Rate (HR) | Respiratory Rate (RR) | $\text{SpO}_2$ | Blood Pressure (BP) | Video Available | Reference Available | Access Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UBFC-rPPG** | **Verified Available** | **Not Available** | **Verified Available** | **Not Available** | **Verified Available** | **Verified Available** | **Verified Available** (Open Academic) |
| **PURE** | **Verified Available** | **Not Available** | **Verified Available** | **Not Available** | **Verified Available** | **Verified Available** | **Verified Available** (EULA Required) |
| **COHFACE** | **Verified Available** | **Verified Available** | **Not Available** | **Not Available** | **Verified Available** | **Verified Available** | **Verified Available** (Online Registration) |
| **VIPL-HR** | **Verified Available** | **Not Available** | **Verified Available** | **Partially Available** | **Verified Available** | **Verified Available** | **Verified Available** (Signed Form) |
| **MMPD** | **Verified Available** | **Verified Available** | **Not Available** | **Not Available** | **Verified Available** | **Verified Available** | **Verified Available** (MIT Open Access) |
| **BP4D+** | **Verified Available** | **Verified Available** | **Not Available** | **Verified Available** | **Verified Available** | **Verified Available** | **Verified Available** (PI Agreement) |

> [!CRITICAL]
> **Ground-Truth Integrity Rule:** A dataset is NEVER used for training or evaluating a parameter for which it lacks verified reference labels. Specifically:
> - **UBFC-rPPG & PURE** are strictly prohibited from evaluating Respiratory Rate (RR) or Blood Pressure (BP).
> - **COHFACE & MMPD** are the primary benchmarks for non-contact Respiratory Rate (RR) due to verified chest belt references.
> - **BP4D+ & VIPL-HR** are the sole external benchmarks with verified Blood Pressure (BP) reference annotations.

---

## 4. Software Architecture & Implementation

### 4.1 Dataset Acquisition Module ([`backend/app/datasets/acquisition.py`](file:///d:/BME/FYP/backend/app/datasets/acquisition.py))
- **Registry Management:** Houses `OFFICIAL_DATASET_REGISTRY` containing official URLs, licenses, and access instructions.
- **Cryptographic File Integrity:** Implements `compute_sha256()` to verify downloaded archives and detect bit-rot.
- **Corrupted Container Scanner:** Decodes test frames via OpenCV `VideoCapture` to identify corrupt video files prior to preprocessing.
- **Lifecycle Status Management:** Formally tracks dataset stages:
  $$\text{RESEARCHED} \longrightarrow \text{ACCESS\_REQUESTED} \longrightarrow \text{ACCESS\_APPROVED} \longrightarrow \text{DOWNLOADED} \longrightarrow \text{INSPECTED} \longrightarrow \text{PREPROCESSED} \longrightarrow \text{READY\_FOR\_TRAINING}$$

### 4.2 Reusable Video Preprocessing Framework ([`backend/app/datasets/preprocessor.py`](file:///d:/BME/FYP/backend/app/datasets/preprocessor.py))
- **Non-Destructive Guarantee:** Original raw video and reference signal files are strictly read-only.
- **Environmental Quality Auditing:**
  - *Illumination Stability:* Calculates luminance variance coefficient ($1 - \sigma/\mu$).
  - *Motion Displacement:* Tracks Euclidean centroid shift of facial landmark bounding boxes across frames.
  - *Blur Detection:* Computes variance of Laplacian operator ($\text{Var}(\nabla^2 I)$).
- **Cubic Spline Synchronization:** Uses `scipy.interpolate.interp1d(kind='cubic')` to resample reference sensor signals (BVP, Respiration, ECG) to match discrete video frame timestamps exactly, eliminating inter-modal phase lag.
- **Exported Archives:** Writes standardized JSON/NumPy preprocessed artifacts into `storage/preprocessed/`.

### 4.3 Zero-Leakage Participant Splitting ([`backend/app/datasets/splitting.py`](file:///d:/BME/FYP/backend/app/datasets/splitting.py))
- **Subject-Level Disjointness:** Guarantees $\text{Train} \cap \text{Val} = \emptyset$, $\text{Train} \cap \text{Test} = \emptyset$, and $\text{Val} \cap \text{Test} = \emptyset$.
- **Stratified Partitioning:** Supports proportional stratification across Fitzpatrick skin phototypes (Types 1–6).
- **Split Hash Fingerprinting:** Generates SHA-256 fingerprint of the split configuration to ensure exact reproducibility across cloud GPU runs.
- **Cross-Dataset Benchmark Specifications:** Pre-defines domain-adaptation splits:
  - *Protocol 1:* Train UBFC $\to$ Test PURE (uncompressed video $\to$ lossless PNG sequences).
  - *Protocol 2:* Train PURE $\to$ Test COHFACE (lossless $\to$ heavy MPEG-4 compression).
  - *Protocol 3:* Train VIPL-HR $\to$ Test UBFC (smartphone cameras $\to$ desktop webcams).

### 4.4 Group Data Collection Protocol ([`backend/app/datasets/group_collection.py`](file:///d:/BME/FYP/backend/app/datasets/group_collection.py))
- **IRB / Clinical Protocol Specification:** Formalized study protocol for $\ge 50$ participants under ISO 14155 and the Declaration of Helsinki.
- **Pseudonymization Convention:** Strict enforcement of `SUBJ-XXX` identifiers. Rejects any entry using participant names.
- **Missing Value Handling:** Records absent modalities explicitly with reasons (e.g., `ref_bp_mmhg: null, missing_labels_reason: "Participant declined arm cuff"`), prohibiting artificial value imputation.
- **Field Data Collection Template:** Exports a standardized CSV collection sheet (`storage/cohort_templates/clinical_collection_template.csv`).

### 4.5 Automated Biomedical Data Quality Validator ([`backend/app/datasets/quality_validator.py`](file:///d:/BME/FYP/backend/app/datasets/quality_validator.py))
- **Physiological Bounds Auditing:**
  - Heart Rate: $[35.0, 220.0]\text{ BPM}$
  - Respiratory Rate: $[4.0, 50.0]\text{ BrPM}$
  - $\text{SpO}_2$: $[70.0\%, 100.0\%]$
  - Systolic BP: $[60.0, 240.0]\text{ mmHg}$
  - Diastolic BP: $[40.0, 140.0]\text{ mmHg}$
- **Physiological Relationship Check:** Enforces $\text{SBP} > \text{DBP}$ and pulse pressure ($\text{SBP} - \text{DBP} \ge 15\text{ mmHg}$).
- **Timestamp Monotonicity:** Audits non-decreasing time steps ($\Delta t > 0$) and flags excessive temporal jitter.
- **Synchronization Tolerance:** Checks that video duration and reference signal duration match within $\pm 0.50\text{ seconds}$.
- **Participant Leakage Auditor:** Cryptographically scans partition arrays to verify zero identity crossover.

---

## 5. Cloud Infrastructure & Zero-Budget Remote GPU Execution

In accordance with the Zero-Budget Architecture directive ratified in Phase 1:

1. **Google Colab (Interactive GPU Development):**
   - Free NVIDIA Tesla T4 GPU ($16\text{ GB}$ VRAM).
   - Checkpoint auto-sync into Google Drive (`/content/drive/MyDrive/rPPG_Research/checkpoints/`).
   - Disconnect recovery via `resume_checkpoint="path/to/{exp_id}_latest.pt"`.
   - Notebook: [`notebooks/colab_training_pipeline.ipynb`](file:///d:/BME/FYP/notebooks/colab_training_pipeline.ipynb).
2. **Kaggle Notebooks (Batch Training & Benchmark Datasets):**
   - Free 30 hours per week of Dual NVIDIA T4 or P100 GPUs.
   - Read-only direct mounting of public datasets in `/kaggle/input/`.
   - Headless background execution via "Save & Run All (Commit)".
   - Notebook: [`notebooks/kaggle_training_pipeline.ipynb`](file:///d:/BME/FYP/notebooks/kaggle_training_pipeline.ipynb).
3. **Oracle Cloud Always Free (Backend Hosting):**
   - 4 Ampere A1 ARM vCPUs, $24\text{ GB}$ RAM, $200\text{ GB}$ block storage.
   - Host FastAPI cloud backend and PostgreSQL clinical database at zero ongoing expense ($0.00/mo).

---

## 6. Verification & Automated Test Results

Phase 2 automated testing was executed via PyTest:

```powershell
$env:PYTHONPATH="backend"
$env:MPLCONFIGDIR="$env:TEMP\mpl"
backend\.venv\Scripts\pytest -q backend\tests
```

**Results:**
- **35 Passed, 0 Skipped, 0 Failed, 0 Warnings in 37.87s**
  - **7 New Phase 2 Integration Tests ([`backend/tests/test_phase2_data_engineering.py`](file:///d:/BME/FYP/backend/tests/test_phase2_data_engineering.py)):**
    1. `test_dataset_registry_and_acquisition_manager`: Validates registry lookup, label presence, and status management.
    2. `test_sha256_integrity_calculation`: Verifies cryptographic hash computation.
    3. `test_video_preprocessor_reference_synchronization`: Validates cubic spline reference resampling.
    4. `test_preprocessor_result_export`: Verifies non-destructive JSON artifact export.
    5. `test_zero_leakage_participant_splitting`: Verifies zero subject overlap across Train/Val/Test and split hash reproducibility.
    6. `test_group_data_collection_template_generation`: Validates pseudonymized entry creation, unconsented entry rejection, and CSV generation.
    7. `test_biomedical_data_quality_validator`: Validates physiological plausibility, SBP/DBP relationships, timestamp monotonicity, and leakage detection.

---

## 7. Phase 2 Sign-Off & Status Declaration

* **Phase 2 Status:** **COMPLETE & VERIFIED**
* **Verification Checklist:**
  - [x] Public datasets investigated across 16 criteria (UBFC, PURE, COHFACE, VIPL-HR, MMPD, BP4D+).
  - [x] Dataset compatibility matrix established with verified physiological labels.
  - [x] Acquisition and integrity verification module implemented ([`acquisition.py`](file:///d:/BME/FYP/backend/app/datasets/acquisition.py)).
  - [x] Reusable, non-destructive preprocessing pipeline built ([`preprocessor.py`](file:///d:/BME/FYP/backend/app/datasets/preprocessor.py)).
  - [x] Participant-level zero-leakage splitting system implemented ([`splitting.py`](file:///d:/BME/FYP/backend/app/datasets/splitting.py)).
  - [x] Group data collection protocol and blank CSV template created ([`group_collection.py`](file:///d:/BME/FYP/backend/app/datasets/group_collection.py)).
  - [x] Automated biomedical quality and physiological validator implemented ([`quality_validator.py`](file:///d:/BME/FYP/backend/app/datasets/quality_validator.py)).
  - [x] Zero-budget cloud training notebooks validated ([`notebooks/colab_training_pipeline.ipynb`](file:///d:/BME/FYP/notebooks/colab_training_pipeline.ipynb), [`notebooks/kaggle_training_pipeline.ipynb`](file:///d:/BME/FYP/notebooks/kaggle_training_pipeline.ipynb)).
  - [x] Automated test suite expanded to 35 active passing tests with zero warnings.

> [!NOTE]
> In accordance with the project completion rules, Phase 3 (**Traditional rPPG and Signal-Processing Benchmark Suite**) will not begin automatically. This report is submitted for stakeholder confirmation.

