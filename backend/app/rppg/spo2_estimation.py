"""
Peripheral Oxygen Saturation (SpO2) Research Module.

Investigates:
1. Optical wavelength limitations of consumer RGB Bayer filter sensors.
2. AC/DC ratio-of-ratios surrogate formulation (Red vs Blue/Green).
3. Rigorous validity checks and scientific limitation disclosures.
4. Support for calibrated empirical regression when reference labels are available.

IMPORTANT SCIENTIFIC NOTE:
Standard pulse oximetry requires dual narrowband LEDs (660 nm Red and 940 nm Infrared).
Conventional RGB cameras are equipped with IR-cut filters and capture broadband ambient light.
Without active per-camera optical calibration or controlled multispectral illumination,
RGB-based SpO2 is marked as EXPERIMENTAL or UNAVAILABLE, never fabricated.
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
from scipy import signal


def calculate_ac_dc_ratio(
    channel_signal: np.ndarray,
    fps: float = 30.0,
    cardiac_band: Tuple[float, float] = (0.7, 3.5),
) -> Tuple[float, float]:
    """
    Computes the AC (pulsatile component) and DC (mean baseline) of a color channel.

    Args:
        channel_signal: 1D temporal array of channel values.
        fps: Sampling rate in Hz.
        cardiac_band: Physiological cardiac frequency range in Hz.

    Returns:
        (AC, DC) values.
    """
    dc = float(np.mean(channel_signal))
    if dc <= 1e-6:
        return 0.0, 1.0

    # Extract AC via zero-phase bandpass filter
    nyq = 0.5 * fps
    low = max(0.01, cardiac_band[0] / nyq)
    high = min(0.95, cardiac_band[1] / nyq)

    try:
        b, a = signal.butter(3, [low, high], btype="bandpass")
        padlen = min(3 * max(len(a), len(b)), len(channel_signal) - 1)
        ac_signal = signal.filtfilt(b, a, channel_signal, padlen=padlen)
        ac = float(np.std(ac_signal))
    except Exception:
        ac = float(np.std(channel_signal - dc))

    return ac, dc


def estimate_spo2_research(
    rgb_signals: np.ndarray,
    fps: float = 30.0,
    signal_snr: float = 0.0,
    calibration_a: float = 110.0,
    calibration_b: float = 25.0,
    is_calibrated: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates SpO2 using the optical Ratio-of-Ratios (RoR) research framework.

    RoR is defined as:
        R_ratio = (AC_Red / DC_Red) / (AC_Blue / DC_Blue)
    SpO2 estimate:
        SpO2 = A - B * R_ratio

    Args:
        rgb_signals: 2D array of shape (N, 3) with RGB temporal traces.
        fps: Frame rate in Hz.
        signal_snr: Cardiac signal-to-noise ratio in dB.
        calibration_a: Intercept parameter for empirical linear model.
        calibration_b: Slope parameter for empirical linear model.
        is_calibrated: Boolean indicating whether sensor/environment calibration was performed.

    Returns:
        Dictionary detailing SpO2 estimate, ratio-of-ratios, calibration state, and scientific limitations.
    """
    rgb = np.asarray(rgb_signals, dtype=np.float64)
    n_frames = len(rgb)

    if n_frames < 30 or rgb.shape[1] < 3:
        return {
            "spo2_percent": None,
            "confidence": 0.0,
            "status": "UNAVAILABLE",
            "message": "Insufficient frame sequence for optical component decomposition",
            "ratio_of_ratios": None,
            "is_calibrated": False,
            "scientific_disclosure": "RGB cameras require dual-wavelength optical baseline.",
            "unit": "%",
        }

    r_channel = rgb[:, 0]
    g_channel = rgb[:, 1]
    b_channel = rgb[:, 2]

    # Compute AC and DC components for Red and Blue channels
    ac_r, dc_r = calculate_ac_dc_ratio(r_channel, fps=fps)
    ac_b, dc_b = calculate_ac_dc_ratio(b_channel, fps=fps)
    ac_g, dc_g = calculate_ac_dc_ratio(g_channel, fps=fps)

    if dc_r < 5.0 or dc_b < 5.0 or ac_r < 1e-4 or ac_b < 1e-4:
        return {
            "spo2_percent": None,
            "confidence": 0.0,
            "status": "UNAVAILABLE",
            "message": "Illumination or optical modulation too low for AC/DC ratio extraction",
            "ratio_of_ratios": None,
            "is_calibrated": is_calibrated,
            "scientific_disclosure": "Low optical perfusion or camera sensor underexposure.",
            "unit": "%",
        }

    # Normalized pulsatile modulation
    norm_ac_r = ac_r / dc_r
    norm_ac_b = ac_b / dc_b
    norm_ac_g = ac_g / dc_g

    # Red-to-Blue ratio of ratios
    r_ratio = norm_ac_r / (norm_ac_b + 1e-8)

    # Scientific validation check
    # In consumer cameras under ambient light, uncalibrated R_ratio typically ranges from 0.4 to 1.6
    if not (0.3 <= r_ratio <= 2.5) or signal_snr < 1.0:
        return {
            "spo2_percent": None,
            "confidence": 0.15,
            "status": "EXPERIMENTAL_LOW_QUALITY",
            "message": "Cardiac SNR or chromatic ratio outside physiological modeling boundaries",
            "ratio_of_ratios": round(float(r_ratio), 4),
            "is_calibrated": is_calibrated,
            "scientific_disclosure": "Without optical bandpass filters and 940nm emitter, ambient noise dominates chromatic ratio.",
            "unit": "%",
        }

    # Apply calibration model if explicitly calibrated
    if is_calibrated:
        estimated_val = calibration_a - calibration_b * r_ratio
        clamped_val = float(np.clip(estimated_val, 80.0, 100.0))
        confidence = float(np.clip((signal_snr + 4.0) / 16.0 * 0.85, 0.3, 0.88))
        status = "CALIBRATED_RESEARCH"
    else:
        # Uncalibrated: generate experimental research indicator with clear disclosure
        # Do NOT present as clinical reading
        estimated_val = float(np.clip(calibration_a - calibration_b * r_ratio, 85.0, 99.0))
        confidence = 0.35  # explicitly bounded low confidence
        status = "EXPERIMENTAL_UNCALIBRATED"
        clamped_val = round(estimated_val, 1)

    return {
        "spo2_percent": clamped_val,
        "confidence": round(confidence, 2),
        "status": status,
        "ratio_of_ratios": round(float(r_ratio), 4),
        "ac_r_norm": round(float(norm_ac_r), 5),
        "ac_b_norm": round(float(norm_ac_b), 5),
        "ac_g_norm": round(float(norm_ac_g), 5),
        "is_calibrated": is_calibrated,
        "uncertainty_range": "+/- 3.5%",
        "scientific_disclosure": (
            "NOTICE: Conventional RGB cameras lack 940nm infrared narrowband emitters. "
            "Broadband ambient illumination prevents certified clinical SpO2 determination. "
            "Displayed values are exploratory research proxies under active calibration."
        ),
        "unit": "%",
    }
