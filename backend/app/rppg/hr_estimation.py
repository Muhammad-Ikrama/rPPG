"""
Heart Rate (HR) Estimation from rPPG Signal.

Performs:
1. Welch Power Spectral Density (PSD) and Fast Fourier Transform (FFT).
2. Sub-bin quadratic peak interpolation.
3. Signal-to-Noise Ratio (SNR) and spectral confidence calculation.
4. Time-domain systolic peak detection and Inter-Beat Interval (IBI) analysis.
5. Heart Rate Variability (HRV - RMSSD) and signal quality scoring.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from scipy import signal


def estimate_heart_rate(
    rppg_signal: np.ndarray,
    fps: float = 30.0,
    min_hr_bpm: float = 42.0,
    max_hr_bpm: float = 210.0,
) -> Dict[str, Any]:
    """
    Estimates heart rate in BPM from bandpass-filtered rPPG pulse signal.

    Args:
        rppg_signal: 1D numpy array of filtered rPPG signal.
        fps: Sampling rate in Hz.
        min_hr_bpm: Minimum physiological HR in BPM (0.7 Hz = 42 BPM).
        max_hr_bpm: Maximum physiological HR in BPM (3.5 Hz = 210 BPM).

    Returns:
        Dictionary with HR estimate, confidence, SNR, peaks, IBI, and quality metrics.
    """
    sig = np.asarray(rppg_signal, dtype=np.float64)
    n = len(sig)

    if n < 15 or fps <= 0:
        return {
            "heart_rate_bpm": None,
            "confidence": 0.0,
            "snr_db": -99.0,
            "status": "UNRELIABLE",
            "message": "Insufficient signal samples for spectral HR analysis",
            "time_domain_bpm": None,
            "rmssd_ms": None,
            "ibi_ms": [],
            "frequencies_hz": [],
            "psd": [],
        }

    # Normalize signal for uniform numerical behavior
    sig_std = np.std(sig)
    if sig_std > 1e-9:
        sig_norm = (sig - np.mean(sig)) / sig_std
    else:
        sig_norm = sig - np.mean(sig)

    min_freq = min_hr_bpm / 60.0
    max_freq = max_hr_bpm / 60.0

    # 1. Frequency Domain Analysis: Welch PSD
    # Window length: ~4-8 seconds or whole signal if shorter
    nperseg = min(n, max(64, int(fps * 6)))
    nfft = max(1024, 2 ** int(np.ceil(np.log2(n * 4))))  # zero-pad for smooth interpolation

    freqs, psd = signal.welch(
        sig_norm,
        fs=fps,
        window="hann",
        nperseg=nperseg,
        noverlap=nperseg // 2 if nperseg > 1 else None,
        nfft=nfft,
        scaling="density",
    )

    # Restrict to physiological heart rate band [min_freq, max_freq]
    band_mask = (freqs >= min_freq) & (freqs <= max_freq)
    if not np.any(band_mask):
        return {
            "heart_rate_bpm": None,
            "confidence": 0.0,
            "snr_db": -99.0,
            "status": "UNRELIABLE",
            "message": "No spectral frequencies in physiological band",
        }

    band_freqs = freqs[band_mask]
    band_psd = psd[band_mask]

    peak_idx_local = np.argmax(band_psd)
    raw_peak_freq = band_freqs[peak_idx_local]

    # Sub-bin interpolation via quadratic fit on the 3 points around the peak
    global_peak_idx = np.where(band_mask)[0][peak_idx_local]
    if 0 < global_peak_idx < len(psd) - 1:
        y1 = np.log(max(psd[global_peak_idx - 1], 1e-12))
        y2 = np.log(max(psd[global_peak_idx], 1e-12))
        y3 = np.log(max(psd[global_peak_idx + 1], 1e-12))
        denom = 2 * (2 * y2 - y1 - y3)
        if abs(denom) > 1e-9:
            delta = (y1 - y3) / denom
            delta = np.clip(delta, -0.5, 0.5)
            df = freqs[1] - freqs[0]
            refined_freq = freqs[global_peak_idx] + delta * df
        else:
            refined_freq = raw_peak_freq
    else:
        refined_freq = raw_peak_freq

    spectral_hr_bpm = float(np.clip(refined_freq * 60.0, min_hr_bpm, max_hr_bpm))

    # 2. Signal-to-Noise Ratio (SNR) in dB (de Haan & Jeanne, 2013)
    # Fundamental pulse window +/- 0.15 Hz, Harmonic window at 2*f +/- 0.15 Hz
    delta_f = 0.15
    f_fund = refined_freq
    f_harm = 2.0 * refined_freq

    fund_mask = (freqs >= f_fund - delta_f) & (freqs <= f_fund + delta_f)
    harm_mask = (freqs >= f_harm - delta_f) & (freqs <= f_harm + delta_f)
    signal_mask = fund_mask | harm_mask

    total_band_mask = (freqs >= min_freq) & (freqs <= min(max_freq * 1.5, fps * 0.5))
    noise_mask = total_band_mask & (~signal_mask)

    signal_power = np.sum(psd[signal_mask])
    noise_power = np.sum(psd[noise_mask])

    if noise_power > 1e-12 and signal_power > 0:
        snr_linear = signal_power / noise_power
        snr_db = float(10.0 * np.log10(snr_linear))
    else:
        snr_db = -10.0

    # 3. Time-Domain Peak Detection & IBI
    # Expected peak distance: at least 0.28 sec (corresponding to ~210 bpm max)
    min_distance = max(2, int(fps * 0.28))
    peaks, props = signal.find_peaks(
        sig_norm,
        distance=min_distance,
        prominence=0.3,
    )

    time_domain_bpm = None
    rmssd_ms = None
    ibi_ms: List[float] = []

    if len(peaks) >= 2:
        ibi_samples = np.diff(peaks)
        ibi_seconds = ibi_samples / fps
        ibi_ms = [float(val * 1000.0) for val in ibi_seconds]
        mean_ibi_s = float(np.median(ibi_seconds))
        if mean_ibi_s > 0:
            time_domain_bpm = float(np.clip(60.0 / mean_ibi_s, min_hr_bpm, max_hr_bpm))

        if len(ibi_ms) >= 2:
            successive_diffs = np.diff(ibi_ms)
            rmssd_ms = float(np.sqrt(np.mean(successive_diffs ** 2)))

    # 4. Confidence and Quality Assessment
    # Map SNR (-6 dB to +12 dB) to [0, 1]
    snr_factor = np.clip((snr_db + 6.0) / 18.0, 0.0, 1.0)

    # Agreement factor between spectral HR and time-domain HR
    agreement_factor = 1.0
    if time_domain_bpm is not None:
        discrepancy = abs(spectral_hr_bpm - time_domain_bpm)
        agreement_factor = np.clip(1.0 - (discrepancy / 20.0), 0.2, 1.0)

    # Peak prominence factor
    max_band_p = np.max(band_psd)
    median_band_p = np.median(band_psd)
    peakiness = max_band_p / (median_band_p + 1e-12)
    peakiness_factor = np.clip((peakiness - 2.0) / 10.0, 0.1, 1.0)

    overall_confidence = float(
        np.clip(
            0.50 * snr_factor + 0.30 * agreement_factor + 0.20 * peakiness_factor,
            0.0,
            0.99,
        )
    )

    # Final HR output is spectral HR with high precision, backed by time-domain consistency
    if overall_confidence >= 0.75 and snr_db >= 2.0:
        quality_status = "EXCELLENT"
    elif overall_confidence >= 0.50 and snr_db >= -2.0:
        quality_status = "GOOD"
    elif overall_confidence >= 0.30:
        quality_status = "FAIR"
    else:
        quality_status = "UNRELIABLE"

    # Select representative PSD points for lightweight frontend charts (up to 120 bins in physiological range)
    plot_mask = (freqs >= 0.5) & (freqs <= 4.0)
    sampled_freqs = [round(float(f), 3) for f in freqs[plot_mask][:: max(1, len(freqs[plot_mask]) // 100)]]
    sampled_psd = [round(float(p), 4) for p in psd[plot_mask][:: max(1, len(freqs[plot_mask]) // 100)]]

    return {
        "heart_rate_bpm": round(spectral_hr_bpm, 1),
        "confidence": round(overall_confidence, 2),
        "snr_db": round(snr_db, 1),
        "status": quality_status,
        "time_domain_bpm": round(time_domain_bpm, 1) if time_domain_bpm else None,
        "rmssd_ms": round(rmssd_ms, 1) if rmssd_ms else None,
        "ibi_ms": ibi_ms,
        "peak_indices": [int(p) for p in peaks],
        "frequencies_hz": sampled_freqs,
        "psd": sampled_psd,
        "unit": "BPM",
    }
