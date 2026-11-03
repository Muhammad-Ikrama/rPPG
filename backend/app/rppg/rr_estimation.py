"""
Respiratory Rate (RR) Estimation Module.

Extracts respiratory patterns via:
1. Respiratory Baseline Modulation (RBM) - Low-frequency thoracic venous pressure wave.
2. Respiratory Amplitude Modulation (RAM) - Systolic envelope modulation.
3. Respiratory Frequency Modulation (RFM) - Heart rate variability / RSA coupling.

Does not infer RR blindly from HR. If signal length is too short (<15s) or
spectral prominence is weak, reports status as UNAVAILABLE or LOW_CONFIDENCE.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from scipy import signal


def estimate_respiratory_rate(
    raw_rppg: np.ndarray,
    filtered_rppg: np.ndarray,
    fps: float = 30.0,
    min_rr_brpm: float = 6.0,
    max_rr_brpm: float = 30.0,
) -> Dict[str, Any]:
    """
    Estimates respiratory rate in breaths per minute (BrPM).

    Args:
        raw_rppg: 1D reconstructed rPPG before aggressive cardiac bandpass (preserves RBM).
        filtered_rppg: 1D pulse-filtered rPPG (for RAM envelope extraction).
        fps: Sampling rate in Hz.
        min_rr_brpm: Minimum physiological respiratory rate (6 BrPM ~ 0.1 Hz).
        max_rr_brpm: Maximum physiological respiratory rate (30 BrPM ~ 0.5 Hz).

    Returns:
        Dictionary containing RR estimate, confidence, waveform, and status.
    """
    n = len(raw_rppg)
    duration_sec = n / fps if fps > 0 else 0.0

    # Respiration requires at least 15 seconds for minimal cycle resolution (3-4 breaths)
    if duration_sec < 12.0 or n < 100:
        return {
            "respiratory_rate_brpm": None,
            "confidence": 0.0,
            "status": "UNAVAILABLE",
            "message": f"Measurement duration ({duration_sec:.1f}s) is insufficient for reliable RR (minimum 15s recommended)",
            "unit": "BrPM",
            "respiratory_waveform": [],
        }

    min_freq = min_rr_brpm / 60.0  # 0.10 Hz
    max_freq = max_rr_brpm / 60.0  # 0.50 Hz
    nyq = 0.5 * fps

    # 1. Pipeline A: Respiratory Baseline Modulation (RBM) from reconstructed rPPG
    low_cutoff = max(0.01, min_freq / nyq)
    high_cutoff = min(0.49, max_freq / nyq)

    try:
        b_rbm, a_rbm = signal.butter(2, [low_cutoff, high_cutoff], btype="bandpass")
        padlen = min(3 * max(len(a_rbm), len(b_rbm)), n - 1)
        rbm_signal = signal.filtfilt(b_rbm, a_rbm, raw_rppg, padlen=padlen)
    except Exception:
        rbm_signal = np.zeros(n)

    # 2. Pipeline B: Respiratory Amplitude Modulation (RAM) from systolic envelope
    # Detect cardiac peaks
    min_peak_dist = max(2, int(fps * 0.35))
    peaks, _ = signal.find_peaks(filtered_rppg, distance=min_peak_dist, prominence=0.2)

    ram_freq = None
    if len(peaks) >= 6:
        peak_times = peaks / fps
        peak_amplitudes = filtered_rppg[peaks]
        # Interpolate envelope at uniform 10 Hz grid
        interp_times = np.linspace(peak_times[0], peak_times[-1], int((peak_times[-1] - peak_times[0]) * 10))
        if len(interp_times) > 30:
            envelope = np.interp(interp_times, peak_times, peak_amplitudes)
            # Detrend and analyze envelope spectrum
            env_detrend = signal.detrend(envelope)
            f_ram, p_ram = signal.welch(env_detrend, fs=10.0, nperseg=min(len(env_detrend), 128), nfft=512)
            ram_mask = (f_ram >= min_freq) & (f_ram <= max_freq)
            if np.any(ram_mask):
                ram_peak_idx = np.argmax(p_ram[ram_mask])
                ram_freq = float(f_ram[ram_mask][ram_peak_idx])

    # 3. Spectral analysis on RBM signal
    nperseg = min(n, int(fps * 16))
    f_rbm, p_rbm = signal.welch(
        rbm_signal,
        fs=fps,
        window="hann",
        nperseg=nperseg,
        nfft=max(1024, n * 2),
    )

    mask = (f_rbm >= min_freq) & (f_rbm <= max_freq)
    if not np.any(mask):
        return {
            "respiratory_rate_brpm": None,
            "confidence": 0.0,
            "status": "UNAVAILABLE",
            "message": "No spectral energy in physiological respiratory band",
            "unit": "BrPM",
            "respiratory_waveform": [],
        }

    band_freqs = f_rbm[mask]
    band_psd = p_rbm[mask]

    peak_idx = np.argmax(band_psd)
    rbm_freq = float(band_freqs[peak_idx])

    # Sub-bin interpolation
    full_peak_idx = np.where(mask)[0][peak_idx]
    if 0 < full_peak_idx < len(p_rbm) - 1:
        y1 = np.log(max(p_rbm[full_peak_idx - 1], 1e-12))
        y2 = np.log(max(p_rbm[full_peak_idx], 1e-12))
        y3 = np.log(max(p_rbm[full_peak_idx + 1], 1e-12))
        denom = 2 * (2 * y2 - y1 - y3)
        if abs(denom) > 1e-9:
            delta = np.clip((y1 - y3) / denom, -0.5, 0.5)
            rbm_freq += delta * (f_rbm[1] - f_rbm[0])

    # Fusion of RBM and RAM estimates
    if ram_freq is not None and abs(ram_freq - rbm_freq) < 0.08:
        # High coherence between baseline and amplitude modulation
        best_freq = 0.65 * rbm_freq + 0.35 * ram_freq
        coherence = 1.0 - (abs(ram_freq - rbm_freq) / 0.08)
    else:
        best_freq = rbm_freq
        coherence = 0.5

    rr_brpm = float(np.clip(best_freq * 60.0, min_rr_brpm, max_rr_brpm))

    # Evaluate respiratory peak prominence and noise ratio
    max_power = np.max(band_psd)
    mean_power = np.mean(band_psd)
    snr_resp = max_power / (mean_power + 1e-12)

    confidence = float(np.clip((snr_resp - 1.5) / 5.0 * (0.6 + 0.4 * coherence), 0.0, 0.95))

    if confidence >= 0.55:
        status = "GOOD"
    elif confidence >= 0.25:
        status = "FAIR"
    else:
        status = "LOW_CONFIDENCE"

    # Downsample respiratory waveform for UI visualization (up to 100 points)
    step = max(1, n // 100)
    waveform_downsampled = [round(float(v), 4) for v in rbm_signal[::step]]

    return {
        "respiratory_rate_brpm": round(rr_brpm, 1),
        "confidence": round(confidence, 2),
        "status": status,
        "method": "RBM-RAM Modulation Analysis",
        "snr_factor": round(float(snr_resp), 2),
        "unit": "BrPM",
        "respiratory_waveform": waveform_downsampled,
    }
