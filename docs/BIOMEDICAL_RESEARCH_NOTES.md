# Biomedical Research Notes: Optical Principles and Algorithmic Validation

## 1. Biophysical Principles of Remote Photoplethysmography (rPPG)

Remote Photoplethysmography (rPPG) measures volumetric variations in cutaneous microvascular blood volume by recording backscattered ambient light from human facial skin.

### 1.1 Modified Beer-Lambert Law in Cutaneous Tissue
When incident ambient light $I_0(\lambda)$ illuminates the face, light traverses multiple epidermal and dermal layers before backscattering into the camera sensor:

$$I(\lambda, t) = I_0(\lambda) \cdot e^{-(\mu_{a,base}(\lambda) + \mu_{s}(\lambda)) d} \cdot e^{-\Delta \mu_a(\lambda, t) \cdot \Delta l(t)}$$

Where:
* $\mu_{a,base}(\lambda)$ is the baseline absorption coefficient of melanin and static tissue.
* $\mu_s(\lambda)$ is the scattering coefficient of the dermis.
* $\Delta \mu_a(\lambda, t) = \epsilon_{HbO_2}(\lambda) \cdot C_{HbO_2}(t) + \epsilon_{Hb}(\lambda) \cdot C_{Hb}(t)$ represents the pulsatile absorption of oxygenated ($HbO_2$) and deoxygenated ($Hb$) hemoglobin.
* $\Delta l(t)$ is the microvascular optical path length dilation during cardiac systole.

Because blood volume increases during cardiac systole, reflected intensity *decreases* inversely with arterial pulse expansion. In RGB sensors:
* **Green Band (520–560 nm)**: Coincides with the peak extinction coefficients of hemoglobin ($\epsilon \approx 3 \times 10^4 \text{ cm}^{-1}/\text{M}$). It possesses the highest signal-to-noise ratio for cardiac pulsation.
* **Red Band (600–650 nm)**: Penetrates deeper into the reticular dermis; exhibits lower absorption fluctuation and is sensitive to oxygenation changes.
* **Blue Band (450–480 nm)**: Dominated by superficial epidermal melanin absorption and high Rayleigh scattering; useful for noise subtraction.

---

## 2. Mathematical Principles of the Plane-Orthogonal-to-Skin (POS) Algorithm

The POS algorithm (Wang et al., *IEEE Transactions on Biomedical Engineering*, 2017) overcomes motion artifacts by projecting normalized color variations onto a plane orthogonal to the skin-tone reflection vector.

### 2.1 Color Space Decomposition
Under the dichromatic reflection model, the observed camera color signal $\vec{C}(t) = [R(t), G(t), B(t)]^T$ is decomposed into:
1. Diffuse reflection containing blood volume pulse $\vec{v}_{ppg}(t)$.
2. Specular reflection representing illumination intensity shifts $\vec{v}_{spec}(t)$.
3. Quantization and sensor noise $\vec{n}(t)$.

Temporal normalization within a sliding temporal window of length $L$ ($1.6 \text{ s}$ duration) yields:

$$\vec{C}_n(t) = \frac{\vec{C}(t)}{\mu(\vec{C})} = \begin{bmatrix} R(t)/\bar{R} \\ G(t)/\bar{G} \\ B(t)/\bar{B} \end{bmatrix}$$

In normalized RGB space, the unit skin-tone vector is:
$$\vec{u}_s = \frac{1}{\sqrt{3}} [1, 1, 1]^T$$

### 2.2 Orthogonal Projection Matrix
A 2D plane orthogonal to $\vec{u}_s$ is spanned by the projection matrix:
$$P = \begin{bmatrix} 0 & 1 & -1 \\ -2 & 1 & 1 \end{bmatrix}$$

Applying projection $P$ to $\vec{C}_n(t)$ yields two orthogonal signals:
$$S_1(t) = G_n(t) - B_n(t)$$
$$S_2(t) = G_n(t) + B_n(t) - 2 R_n(t)$$

### 2.3 Dynamic Alpha Tuning and Overlap-Add Reconstruction
Because the exact orientation of specular reflection depends on facial morphology and light angle, the signals are dynamically combined via their standard deviations:

$$\alpha = \frac{\sigma(S_1)}{\sigma(S_2)}$$
$$h(t) = S_1(t) + \alpha \cdot S_2(t)$$

Windows are combined using Overlap-Add (OLA) reconstruction and filtered using a zero-phase 3rd-order Butterworth bandpass filter ($0.7 - 3.5 \text{ Hz}$).

---

## 3. Respiratory Rate (RR) Modulation Mechanisms

Respiration modulates the facial photoplethysmogram through three distinct cardiopulmonary interactions:
1. **Respiratory Baseline Modulation (RBM)**: Intrathoracic pressure changes during inspiration increase venous return, fluctuating central venous pressure and facial venous pooling at respiratory frequencies ($0.1 - 0.5 \text{ Hz}$ or $6 - 30 \text{ BrPM}$).
2. **Respiratory Amplitude Modulation (RAM)**: Decreased ventricular filling during deep inspiration modulates cardiac stroke volume, causing systolic peak-to-trough amplitude variation.
3. **Respiratory Frequency Modulation (RFM)**: Mediated by Respiratory Sinus Arrhythmia (RSA), where vagal efferent activity accelerates the heart rate during inspiration and decelerates it during expiration.

---

## 4. Optical Limitations of Consumer RGB Cameras for SpO2

Standard clinical pulse oximetry relies on the Ratio-of-Ratios (RoR) between two calibrated narrowband optical emitters:
* Red LED: $660 \text{ nm}$ (where deoxygenated hemoglobin absorbs more strongly).
* Infrared LED: $940 \text{ nm}$ (where oxygenated hemoglobin absorbs more strongly).

$$R = \frac{(AC_{660} / DC_{660})}{(AC_{940} / DC_{940})}$$

### 4.1 Consumer Hardware Constraints
* **IR-Cut Filters**: Consumer webcams and smartphones possess integrated optical infrared-blocking filters ($< 700 \text{ nm}$).
* **Broadband Overlap**: Bayer RGB filters have broad spectral transmission curves (Full-Width at Half-Maximum $\approx 100 \text{ nm}$) with cross-channel leakage.
* **Ambient Lighting Spectrum**: Fluorescent and white LED room lights have irregular spectral emission profiles without $940 \text{ nm}$ irradiance.

**Scientific Conclusion**: Uncalibrated RGB-based SpO2 is an experimental proxy and cannot replace clinical dual-wavelength pulse oximetry. The system explicitly discloses this limitation.

---

## 5. Blood Pressure (SBP/DBP) & ISO 81060-2 Standards

Pulse Wave Analysis (PWA) on facial rPPG signals extracts morphological parameters reflecting vascular tone:
* **Crest Time (CT)**: Pulse onset to systolic peak duration; inversely correlated with arterial stiffness.
* **Pulse Width at 50% Amplitude ($PW_{50}$)**: Reflects total peripheral vascular resistance.
* **Area Ratio**: Ratio of systolic to diastolic areas under the pulse curve.

**ISO 81060-2 Standard Requirements**:
Clinical sphygmomanometers must undergo paired reference validation against auscultatory mercury or arterial catheter measurements:
* Mean error $\le \pm 5 \text{ mmHg}$.
* Standard deviation $\le 8 \text{ mmHg}$.

Without subject-specific reference cuff calibration, non-contact optical blood pressure predictions cannot be certified for diagnostic use and are strictly presented as experimental research indices.
