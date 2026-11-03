# System Architecture: Complete Cross-Platform rPPG Vital Signs Monitoring System

## 1. Architectural Overview

The system implements an end-to-end cloud-connected biomedical telemetry pipeline for non-contact vital sign estimation. All client platforms (**Android**, **iOS**, and **Web**) interface with a unified **Python FastAPI** cloud backend that executes standardized computer vision and Remote Photoplethysmography (rPPG) digital signal processing algorithms.

```
+-----------------------------------------------------------------------------------+
|                                Client Applications                                |
|                                                                                   |
|  [ Android App (Flutter) ]     [ iOS App (Flutter) ]      [ Web App (HTML5/Canvas) ]|
|  - Front Camera (30 fps)       - Front Camera (30 fps)    - getUserMedia Camera    |
|  - Live ROI Overlay Target     - Live ROI Overlay Target  - Real-time Canvas Chart |
|  - Local Video Cache (WebM)    - Local Video Cache (MP4)  - Instant Demo Suite     |
+----------------------------------------+------------------------------------------+
                                         | Secure HTTPS / REST / WebSockets
                                         v
+-----------------------------------------------------------------------------------+
|                             Python FastAPI Cloud Backend                          |
|                                                                                   |
|  [ API Layer ]                                                                    |
|  - /api/v1/auth          : JWT Security, Pseudonymized SUBJ-ID, Biometric Consent |
|  - /api/v1/measurements  : Async Pipeline Queue, Upload, 4-Card Dashboard Results |
|  - /api/v1/stream        : Real-time Camera Frame Face & ROI Positioning Guidance |
|  - /api/v1/reports       : Publication-Grade PDF & Structured CSV Exporters        |
|  - /api/v1/datasets      : Public Cohort Compatibility & Statistical Benchmark     |
+----------------------------------------+------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                           rPPG Signal Processing Engine                           |
|                                                                                   |
| 1. Video Ingestion & Decoding     : OpenCV frame extraction & frame-drop auditing |
| 2. Face Detection & Tracking       : MediaPipe Face Mesh & OpenCV anatomical fall- |
|                                      back with YCrCb biological skin segmentation  |
| 3. Facial ROI Anatomical Isolation: Forehead, Left Cheek, Right Cheek spatial mean|
| 4. POS Projection Algorithm        : Wang et al. (IEEE TBME 2017) skin plane math  |
| 5. Zero-Phase Bandpass Filtering  : 3rd-order Butterworth in [0.7 Hz, 3.5 Hz]     |
| 6. Spectral & Temporal HR Engine   : Welch PSD, quadratic sub-bin fit, IBI & RMSSD|
| 7. Respiratory Rate (RR) Pipeline  : RBM (0.1-0.5 Hz baseline) & RAM envelope     |
| 8. SpO2 Optical RoR Research Module: Dual-channel pulsatile AC/DC decomposition   |
| 9. Blood Pressure Research Module  : Pulse morphology features (CT, PW50, AUC)    |
| 10. Signal Quality Index (SQI)     : Composite SNR, motion, and luminance stability|
+----------------------------------------+------------------------------------------+
                                         |
                 +-----------------------+-----------------------+
                 |                                               |
                 v                                               v
+-----------------------------------+           +-----------------------------------+
|      PostgreSQL 16 Database       |           |       Secure Object Storage       |
|                                   |           |                                   |
| - users                           |           | - storage/videos/                 |
| - measurement_sessions            |           |   (SHA-256 hashed video payloads, |
| - vital_sign_estimates            |           |    7-day configurable retention)  |
| - (Auto-fallback to SQLite local) |           | - storage/reports/ (PDF & CSV)    |
+-----------------------------------+           +-----------------------------------+
```

---

## 2. Component Specifications

### 2.1 Computer Vision & Anatomical ROI Isolation
* **MediaPipe Face Mesh**: Detects 468 3D facial landmarks.
  * **Forehead Zone**: Landmarks `[10, 67, 109, 297, 338, 9, 8, 107, 336]`.
  * **Left Cheek Zone**: Landmarks `[117, 118, 101, 205, 206, 207, 123, 50, 36, 137, 203]`.
  * **Right Cheek Zone**: Landmarks `[346, 347, 330, 425, 426, 427, 352, 280, 266, 366, 423]`.
* **Exclusion Masks**: Convex hull polygons around eyes and lips are strictly subtracted to prevent ocular saccades and speech articulation from contaminating the vascular signal.
* **Biological Skin Filter**: YCrCb color space thresholding ($133 \le C_r \le 173$ and $77 \le C_b \le 127$) rejects hair, eyeglasses, and specular reflections.
* **ROI Stabilization**: Exponential Moving Average (EMA) smoothing ($\alpha = 0.7$) dampens micro-jitter.

### 2.2 Plane-Orthogonal-to-Skin (POS) Algorithm Core
* Formulated directly from Wang et al. (*IEEE Transactions on Biomedical Engineering*, 2017).
* In a sliding window of length $L = 1.6 \text{ s}$ ($L \approx 48$ frames at 30 fps) with unit stride:
  1. Temporal normalization:
     $$C_n(t) = \frac{C(t)}{\mu(C)} = \begin{bmatrix} R(t)/\bar{R} \\ G(t)/\bar{G} \\ B(t)/\bar{B} \end{bmatrix}$$
  2. Projection onto the skin-orthogonal plane:
     $$S_1(t) = G_n(t) - B_n(t)$$
     $$S_2(t) = G_n(t) + B_n(t) - 2 R_n(t)$$
  3. Dynamic alpha weighting:
     $$\alpha = \frac{\sigma(S_1)}{\sigma(S_2)}$$
     $$h(t) = S_1(t) + \alpha \cdot S_2(t)$$
  4. Overlap-add (OLA) window reconstruction across all time indices $t \in [0, N-1]$.
  5. 3rd-order zero-phase Butterworth bandpass filtering: $[0.7 \text{ Hz}, 3.5 \text{ Hz}]$, corresponding to $[42 \text{ BPM}, 210 \text{ BPM}]$.

### 2.3 Vital Sign Estimation Engines
1. **Heart Rate (HR)**:
   * Welch's Power Spectral Density (PSD) with Hanning window and zero-padding.
   * Quadratic sub-bin interpolation for $\pm 0.1 \text{ BPM}$ frequency resolution.
   * Time-domain systolic peak detection yielding Inter-Beat Intervals (IBIs) and RMSSD heart rate variability.
2. **Respiratory Rate (RR)**:
   * Respiratory Baseline Modulation (RBM) low-frequency filtering ($0.1 - 0.5 \text{ Hz}$).
   * Respiratory Amplitude Modulation (RAM) upper systolic peak envelope tracking.
   * Cross-spectral coherence fusion; marks `UNAVAILABLE` if video duration $< 12 \text{ s}$.
3. **Oxygen Saturation (SpO2)**:
   * Optical Ratio-of-Ratios:
     $$R = \frac{AC_R / DC_R}{AC_B / DC_B}$$
   * Transparent limitation disclosure acknowledging consumer RGB Bayer filter limitations compared to dual-wavelength $660 \text{ nm} / 940 \text{ nm}$ medical pulse oximeters.
4. **Blood Pressure (SBP/DBP)**:
   * Pulse waveform morphology: Crest Time (CT), Diastolic Time (DT), Pulse Width at 50% amplitude ($PW_{50}$), Area-Under-Curve ratio.
   * Subject-specific calibration support with ISO 81060-2 compliance disclosures; never emits hardcoded 120/80 values.
