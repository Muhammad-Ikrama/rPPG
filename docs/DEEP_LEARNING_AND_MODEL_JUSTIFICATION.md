# Deep Learning Architectures, Justification, and Training Framework

## 1. Overview and Scientific Motivation

Remote Photoplethysmography (rPPG) from facial video has traditionally relied on color space projections (such as **POS**, **CHROM**, and **ICA**). While computationally lightweight, traditional methods operate on spatially averaged RGB traces, which discard micro-spatial vascular dynamics and suffer degradation under rigid head rotation, facial expressions, and rapid ambient illumination shifts.

To overcome these constraints, this project integrates end-to-end deep learning spatio-temporal architectures:
1. **PhysNet (3D-CNN)**: Spatio-temporal convolutional network for direct 3D video volume pulse extraction (*Yu et al., BMVC 2019*).
2. **MTTS-CAN**: Multi-Task Temporal Shift Convolutional Attention Network for simultaneous on-device Heart Rate and Respiratory Rate estimation (*Liu et al., NeurIPS 2020*).

---

## 2. Architecture 1: PhysNet (Spatio-Temporal 3D-CNN)

### 2.1 Theoretical Rationale & Architecture
PhysNet treats facial video as a continuous 3D spatio-temporal volume $\mathbf{X} \in \mathbb{R}^{B \times C \times T \times H \times W}$ ($C=3$ RGB channels, $T$ frames, spatial resolution $H \times W$).
* **Stem Block**: $1 \times 5 \times 5$ spatial 3D convolution preserving temporal resolution while filtering high-frequency camera sensor noise.
* **Spatio-Temporal Residual Stages**: Cascaded $3 \times 3 \times 3$ 3D convolutions with Exponential Linear Unit (ELU) activations and Batch Normalization.
* **Spatial Shrinkage with Temporal Preservation**: MaxPool3d layers with kernel $(1, 2, 2)$ and stride $(1, 2, 2)$ progressively downsample spatial dimensions ($32 \times 32 \to 16 \times 16 \to 8 \times 8 \to 4 \times 4$) while keeping temporal length $T$ intact.
* **Global Spatial Average Pooling**: Collapses spatial dimensions over $H$ and $W$ via $\text{mean}_{H, W}$ to obtain latent temporal feature representation $\mathbf{Z} \in \mathbb{R}^{B \times C_{\text{latent}} \times T}$.
* **Temporal Convolutional Head**: $1 \times 1$ and $1 \times 3$ Conv1D projections yielding a continuous 1D pulse wave $\hat{y} \in \mathbb{R}^{B \times T}$.

### 2.2 Learned Physiological Features
PhysNet learns subtle, cardiac-synchronous hemoglobin absorption shifts directly from raw pixel intensity changes across vascular zones (cheeks and forehead) while developing spatial invariance to non-skin regions (eyes, hair, background).

### 2.3 Limitations & Constraints
* High computational complexity: Standard 3D convolutions have cubic parameter and FLOP growth with video resolution.
* Requires spatio-temporal face cropping and spatial resolution standardization ($32 \times 32$ or $64 \times 64$).
* Primarily predicts cardiac pulsatile waveforms (HR); does not directly predict arterial blood pressure or oxygen saturation without secondary calibrated heads.

---

## 3. Architecture 2: MTTS-CAN (Multi-Task Temporal Shift Attention Network)

### 3.1 Theoretical Rationale & Architecture
To enable real-time inference and mobile edge transitions, **MTTS-CAN** (*Liu et al. 2020*) replaces heavy 3D convolutions with 2D spatial convolutions augmented by the **Temporal Shift Module (TSM)**:
* **Temporal Shift Module (TSM)**: Shifts $1/4$ of feature channels backward in time ($-1$) and $1/4$ forward in time ($+1$) along the sequence dimension with **zero extra parameters and zero additional FLOPs**.
* **Dual Branch Structure**:
  1. **Appearance Branch**: Takes static video frames $A_t$ to predict continuous spatial attention masks $M_t$. The mask dynamically assigns higher weights to highly vascularized dermal tissue while suppressing shadows and motion boundaries.
  2. **Motion Branch**: Processes normalized temporal frame differences $D_t = (A_{t+1} - A_t) / (A_{t+1} + A_t)$ element-wise gated by $M_t$.
* **Multi-Task Latent Projection**: Dual regression heads output:
  - Cardiac pulse derivative $\to$ integrated into continuous Blood Volume Pulse (BVP) for **Heart Rate**.
  - Respiratory derivative $\to$ integrated into continuous respiratory wave for **Respiratory Rate**.

---

## 4. Biomedical Loss Functions

Standard Mean Squared Error (MSE) is ineffective for rPPG training because arbitrary phase offsets or DC illumination biases dominate the loss. We implement a multi-objective loss:

### 4.1 Negative Pearson Correlation Loss
$$\mathcal{L}_{\text{Pearson}}(\hat{y}, y) = 1.0 - \frac{\sum_{t=1}^T (\hat{y}_t - \bar{\hat{y}})(y_t - \bar{y})}{\sqrt{\sum_{t=1}^T (\hat{y}_t - \bar{\hat{y}})^2 \sum_{t=1}^T (y_t - \bar{y})^2 + \epsilon}}$$
Bounded strictly in $[0.0, 2.0]$. Encourages optimal morphological and phase alignment between the predicted pulse and the ground-truth contact PPG reference.

### 4.2 Frequency-Domain Spectral Loss
$$\mathcal{L}_{\text{Spectral}}(\hat{y}, y) = 1.0 - \text{CosineSimilarity}\left(|\text{RFFT}(\hat{y})|^2, |\text{RFFT}(y)|^2\right)$$
Penalizes discrepancy in spectral peak energy within the physiological cardiac band ($0.7 - 3.5\text{ Hz}$).

### 4.3 Composite Multi-Objective Loss
$$\mathcal{L}_{\text{Total}} = 1.0 \cdot \mathcal{L}_{\text{Pearson}} + 0.1 \cdot \mathcal{L}_{\text{Spectral}} + 0.2 \cdot \text{MSE}(\Delta \hat{y}, \Delta y)$$

---

## 5. Training Protocol and Data Leakage Prevention

Per **Section 8** and **Section 12**:
1. **Zero Participant Leakage**: Participants are partitioned strictly into **Train (70%)**, **Validation (15%)**, and **Test (15%)** sets. No participant's video clips ever cross partition boundaries.
2. **Experiment Tracking**: Every training run automatically logs:
   - Unique Experiment ID (`EXP-PHYSNET-XXXX`)
   - Architecture and hyperparameter configuration (learning rate, weight decay, batch size, seed)
   - Per-epoch training and validation loss curves
   - Checkpoint artifact paths (`.pt`)
   - ONNX export artifact paths (`.onnx`)
3. **No Fabricated Results**: If a training run has not been executed, it is explicitly marked as `PENDING_CHECKPOINT`.

