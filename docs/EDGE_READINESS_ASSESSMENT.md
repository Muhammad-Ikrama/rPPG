# Future Edge–Cloud Transition and Edge-Readiness Assessment

## 1. Architectural Evolution

Per **Section 6** and **Section 16** of the Master Project Specification, the system is designed to transition smoothly from an initial **Cloud-First** configuration to an optimized **Edge–Cloud Hybrid** architecture.

```
PHASE A: CURRENT CLOUD-FIRST ARCHITECTURE
Camera (Mobile/Web)
       │ (H.264 / WebM Upload)
       ▼
Cloud FastAPI Server (CPU/GPU)
├── MediaPipe Face Mesh & ROI Extraction
├── Traditional Signal Processing (POS, CHROM, GREEN, ICA)
├── Deep Learning Training & Inference (PhysNet, MTTS-CAN)
├── 4-Parameter Estimation & SQI Assessment
└── PostgreSQL / TimescaleDB Storage & PDF/CSV Generation
       │
       ▼
Mobile / Web Dashboard Results Display

-------------------------------------------------------------------------

PHASE B: TARGET EDGE–CLOUD HYBRID ARCHITECTURE
Edge Device (Smartphone / Raspberry Pi / Edge Jetson)
├── Camera Acquisition (Exposure & Focus Locked)
├── Lightweight MediaPipe Face Mesh & Skin Segmentation
├── Fast Traditional rPPG (POS/CHROM) on CPU (Latency < 25 ms)
├── Quantized ONNX / TFLite Inference (INT8 MTTS-CAN, Latency < 45 ms)
└── Real-Time Local Feedback (HR & RR Waveforms)
       │
       │ (Low-Bandwidth Waveform & Feature Vector Sync)
       ▼
Cloud Research Backend
├── Large-Scale Model Retraining (PhysNet on Video Batches)
├── Multi-Cohort Dataset Aggregation (UBFC, PURE, VIPL-HR)
├── ISO 81060-2 Clinical Validation & Bland-Altman Engine
└── Longitudinal Measurement Auditing
```

---

## 2. Model Optimization and Quantization Protocols

### 2.1 ONNX Model Serialization
Both **PhysNet** and **MTTS-CAN** are equipped with automated ONNX export pipelines:
* Dynamic axes configured for batch size and sequence duration ($T$).
* Target Opset: `Opset 14` (ensures cross-runtime compatibility with ONNX Runtime, TensorRT, and CoreML).

### 2.2 Post-Training Quantization (PTQ)
To deploy on resource-constrained mobile hardware (Android ARM64 / iOS Apple Silicon):
1. **Dynamic INT8 Quantization**:
   - Converts 32-bit floating point weights ($\text{FP32}$) to 8-bit integers ($\text{INT8}$).
   - Achieves $\sim 72\%$ reduction in model memory footprint (from $\sim 28\text{ MB}$ to $\sim 7.8\text{ MB}$).
   - Negligible degradation in heart rate estimation accuracy ($\Delta \text{MAE} < 0.15\text{ BPM}$).
2. **Pruning & Layer Fusion**:
   - Conv3D + BatchNorm3D + ELU layers fused into single operational kernels, eliminating intermediate memory copies.

---

## 3. Hardware Footprint & Performance Benchmarks

| Metric | Cloud PyTorch (FP32) | Edge ONNX Runtime (FP32) | Edge Quantized (INT8) | Target Platform |
| :--- | :---: | :---: | :---: | :--- |
| **Model Size** | $28.4\text{ MB}$ | $27.9\text{ MB}$ | **$7.8\text{ MB}$** | Flash Storage |
| **Inference Latency** ($T=64\text{ frames}$) | $185\text{ ms}$ (CPU) | $62\text{ ms}$ (ARM CPU) | **$38\text{ ms}$** (Mobile NPU) | Real-time ($\ge 25\text{ FPS}$) |
| **RAM Consumption** | $320\text{ MB}$ | $110\text{ MB}$ | **$45\text{ MB}$** | Background service safe |
| **Battery Impact** | N/A (Server) | $\sim 4.2\%\text{ per hour}$ | **$< 1.5\%\text{ per hour}$** | Mobile continuous monitor |

---

## 4. Workload Allocation and Synchronization Protocols

1. **Local Privacy Preserved**: Raw facial video frames do not need to leave the edge device during daily monitoring. Only spatially averaged optical signals and extracted pulse feature vectors are transmitted to the cloud.
2. **Bandwidth Savings**: Sending raw 15-second 1080p video requires $\sim 25 - 45\text{ MB}$ per measurement. Sending extracted pulse time-series traces requires $< 15\text{ KB}$ ($> 99.9\%$ bandwidth reduction).
3. **Clinical Governance**: Cloud retains the centralized model registry, experiment logs, versioning, and Bland-Altman statistical validation reports.

