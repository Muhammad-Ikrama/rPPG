"""
Biomedical Signal Quality Assessment (SQI) and Motion Metric Module.

Evaluates:
1. Cardiac spectral Signal-to-Noise Ratio (SNR in dB).
2. Waveform skewness and kurtosis.
3. Illumination stability across frames.
4. Rigid/non-rigid facial motion artifacts.
5. Overall Signal Quality Index (SQI: 0.0 - 1.0).
"""

from typing import Dict, Any, List
import numpy as np
from scipy import stats


def evaluate_signal_quality(
    rppg_signal: np.ndarray,
    rgb_signals: np.ndarray,
    snr_db: float,
    fps: float = 30.0,
) -> Dict[str, Any]:
    """
    Computes comprehensive quality metrics for an rPPG recording.

    Args:
        rppg_signal: 1D pulse-filtered rPPG waveform.
        rgb_signals: 2D array (N, 3) of spatial mean RGB values across frames.
        snr_db: Spectral SNR of the cardiac fundamental peak.
        fps: Video frame rate.

    Returns:
        Dictionary with overall SQI, sub-scores, status, and actionable user guidance.
    """
    n = len(rppg_signal)
    if n < 15:
        return {
            "sqi_score": 0.0,
            "status": "POOR",
            "snr_db": snr_db,
            "illumination_stability": 0.0,
            "motion_stability": 0.0,
            "guidance": "Recording duration too short.",
        }

    # 1. Illumination Stability: standard deviation of total luminance normalized by mean
    luminance = 0.299 * rgb_signals[:, 0] + 0.587 * rgb_signals[:, 1] + 0.114 * rgb_signals[:, 2]
    mean_lum = float(np.mean(luminance))
    std_lum = float(np.std(luminance))
    lum_cov = (std_lum / mean_lum) if mean_lum > 0 else 1.0
    # Ideal: lum_cov < 0.03. Score drops if lum_cov > 0.10
    illumination_score = float(np.clip(1.0 - (lum_cov / 0.10), 0.0, 1.0))

    # 2. Motion Stability: frame-to-frame derivative of luminance
    frame_diffs = np.abs(np.diff(luminance))
    mean_diff = float(np.mean(frame_diffs))
    # Normalized motion score: lower jitter -> higher score
    motion_score = float(np.clip(1.0 - (mean_diff / (mean_lum * 0.03 + 1e-6)), 0.0, 1.0))

    # 3. Waveform Morphology Quality: Skewness and Kurtosis
    # Physiological rPPG exhibits mild positive skewness and kurtosis around 2.5 - 4.5
    skew = float(stats.skew(rppg_signal))
    kurt = float(stats.kurtosis(rppg_signal))  # Fisher kurtosis (normal == 0)

    # 4. SNR Contribution (scaled from [-6 dB, +12 dB] to [0, 1])
    snr_score = float(np.clip((snr_db + 6.0) / 18.0, 0.0, 1.0))

    # 5. Composite SQI
    sqi = float(
        np.clip(
            0.45 * snr_score + 0.25 * motion_score + 0.20 * illumination_score + 0.10 * (1.0 if abs(kurt) < 3.0 else 0.5),
            0.0,
            1.0,
        )
    )

    if sqi >= 0.75:
        status = "EXCELLENT"
        guidance = "Optimal signal quality. Measurement is highly reliable."
    elif sqi >= 0.55:
        status = "GOOD"
        guidance = "Good signal quality. Minor ambient variation detected."
    elif sqi >= 0.35:
        status = "FAIR"
        guidance = "Fair quality. Try to remain still and ensure consistent frontal lighting."
    else:
        status = "POOR"
        guidance = "Poor signal quality. Please avoid facial movements and face a steady light source."

    return {
        "sqi_score": round(sqi, 2),
        "status": status,
        "snr_db": round(float(snr_db), 1),
        "illumination_stability": round(illumination_score, 2),
        "motion_stability": round(motion_score, 2),
        "skewness": round(skew, 2),
        "kurtosis": round(kurt, 2),
        "guidance": guidance,
    }
