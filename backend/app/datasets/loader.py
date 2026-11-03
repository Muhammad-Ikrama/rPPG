"""
Dataset Loaders and Biomedical Benchmark Generators.

Provides:
1. UBFC-rPPG and PURE ground-truth file parsers.
2. Physiologically rigorous synthetic facial video and RGB stream generator.
   Accurately models photoplethysmographic absorption:
   - Green channel dominant pulsatile amplitude (520-560 nm peak hemoglobin absorption).
   - Red and Blue secondary optical absorption.
   - Respiratory baseline wander (RBM) and amplitude modulation (RAM).
   - Realistic illumination drift and additive sensor noise.
"""

from typing import Dict, Any, List, Tuple, Optional
import os
import numpy as np


def load_ubfc_ground_truth(filepath: str) -> Dict[str, np.ndarray]:
    """
    Loads ground-truth text file from the UBFC-rPPG dataset.
    Format is typically 3 lines:
    Line 0: BVP trace (photoplethysmograph waveform)
    Line 1: HR values (ground truth BPM per second or sample)
    Line 2: Timestamps (in seconds)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"UBFC ground truth file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if len(lines) >= 3:
        bvp = np.array([float(x) for x in lines[0].split() if x])
        hr = np.array([float(x) for x in lines[1].split() if x])
        time_s = np.array([float(x) for x in lines[2].split() if x])
    elif len(lines) == 1:
        # Single column format
        data = np.loadtxt(filepath)
        time_s = np.arange(len(data)) / 30.0
        bvp = data
        hr = np.zeros_like(data)
    else:
        data = np.loadtxt(filepath)
        time_s = data[:, 0]
        bvp = data[:, 1]
        hr = data[:, 2] if data.shape[1] > 2 else np.zeros_like(time_s)

    return {
        "time_s": time_s,
        "bvp": bvp,
        "hr_bpm": hr,
        "mean_hr_bpm": float(np.mean(hr[hr > 30])) if np.any(hr > 30) else float(np.mean(hr)),
    }


def generate_synthetic_rppg_stream(
    duration_sec: float = 20.0,
    fps: float = 30.0,
    target_hr_bpm: float = 75.0,
    target_rr_brpm: float = 15.0,
    snr_db: float = 6.0,
    skin_tone_rgb: Tuple[float, float, float] = (185.0, 135.0, 115.0),
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Synthesizes a realistic, physiologically grounded RGB optical time-series.

    Models:
    - Cardiac pulse fundamental frequency f_c = HR / 60 Hz + 2nd harmonic.
    - Respiratory modulation f_r = RR / 60 Hz (Baseline wander & amplitude shift).
    - Chromatic absorption coefficients across RGB Bayer bands (Green > Red, Blue).
    - Additive Gaussian sensor noise calibrated to target SNR.

    Args:
        duration_sec: Recording duration in seconds.
        fps: Sampling rate (Hz).
        target_hr_bpm: Ground-truth Heart Rate in BPM.
        target_rr_brpm: Ground-truth Respiratory Rate in Breaths/min.
        snr_db: Target cardiac signal-to-noise ratio in dB.
        skin_tone_rgb: Baseline DC skin reflection [R, G, B].

    Returns:
        rgb_signals: 2D array of shape (N, 3).
        ground_truth_bvp: 1D ground-truth cardiac blood volume pulse waveform.
        ground_truth_meta: Dictionary of ground-truth parameters.
    """
    n_frames = int(round(duration_sec * fps))
    t = np.arange(n_frames) / fps

    f_hr = target_hr_bpm / 60.0
    f_rr = target_rr_brpm / 60.0

    # Cardiac pulse wave: fundamental + asymmetric 2nd harmonic (dicrotic notch)
    cardiac_wave = (
        np.sin(2 * np.pi * f_hr * t)
        + 0.35 * np.sin(4 * np.pi * f_hr * t + 0.7)
        + 0.15 * np.sin(6 * np.pi * f_hr * t + 1.2)
    )

    # Respiratory Baseline Modulation (RBM) and Amplitude Modulation (RAM)
    resp_baseline = 0.25 * np.sin(2 * np.pi * f_rr * t)
    resp_amplitude = 1.0 + 0.15 * np.sin(2 * np.pi * f_rr * t + 0.5)

    modulated_pulse = (cardiac_wave * resp_amplitude) + resp_baseline

    # Hemoglobin absorption in optical bands:
    # Green (520-560nm) has strongest blood absorption fluctuation: -0.015
    # Red (600-650nm): -0.006
    # Blue (450-480nm): -0.004
    dc_r, dc_g, dc_b = skin_tone_rgb

    # Inverted because increased blood volume lowers reflected light
    ac_r = -0.007 * dc_r * modulated_pulse
    ac_g = -0.018 * dc_g * modulated_pulse
    ac_b = -0.005 * dc_b * modulated_pulse

    # Calculate additive noise from requested SNR
    signal_power = np.var(ac_g)
    snr_linear = 10.0 ** (snr_db / 10.0)
    noise_power = signal_power / (snr_linear + 1e-9)
    noise_std = np.sqrt(noise_power)

    noise_r = np.random.normal(0, noise_std * 0.8, n_frames)
    noise_g = np.random.normal(0, noise_std * 1.0, n_frames)
    noise_b = np.random.normal(0, noise_std * 1.2, n_frames)

    # Ambient slow illumination drift (< 0.05 Hz)
    ambient_drift = 2.0 * np.sin(2 * np.pi * 0.03 * t)

    r_stream = dc_r + ac_r + noise_r + ambient_drift
    g_stream = dc_g + ac_g + noise_g + ambient_drift
    b_stream = dc_b + ac_b + noise_b + ambient_drift

    rgb_signals = np.column_stack([r_stream, g_stream, b_stream])

    ground_truth_meta = {
        "target_hr_bpm": target_hr_bpm,
        "target_rr_brpm": target_rr_brpm,
        "duration_sec": duration_sec,
        "fps": fps,
        "snr_db": snr_db,
    }

    return rgb_signals, cardiac_wave, ground_truth_meta
