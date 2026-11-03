"""
GREEN Channel Remote Photoplethysmography Algorithm.

Based on:
Verkruysse, W., Svaasand, L. O., & Nelson, J. S. (2008).
"Remote plethysmographic imaging using ambient light".
Optics Express, 16(26), 21434-21445.
doi: 10.1364/OE.16.021434
"""

from typing import Dict, Any, Tuple
import numpy as np
from app.rppg.pos_algorithm import temporal_butterworth_bandpass


def compute_green_rppg(
    rgb_signals: np.ndarray,
    fps: float = 30.0,
    lowcut: float = 0.7,
    highcut: float = 3.5,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Extracts rPPG pulse signal using the single green channel method.

    Biomedical Rationale:
    Oxyhemoglobin (HbO2) exhibits strong absorption peaks in the green spectrum
    (~520-580 nm), which yields the highest pulsatile signal-to-noise ratio in
    standard camera sensors under diffuse white/ambient illumination.

    Mathematical steps:
    1. Extract green channel G(t).
    2. Temporal normalization: G_norm(t) = (G(t) - mean(G)) / std(G).
    3. Zero-phase Butterworth bandpass filter in cardiac range [0.7, 3.5] Hz.

    Args:
        rgb_signals: 2D numpy array of shape (N, 3), spatially averaged R, G, B.
        fps: Video frame rate in frames per second (Hz).
        lowcut: Bandpass filter lower bound (Hz, default 0.7 Hz ~ 42 BPM).
        highcut: Bandpass filter upper bound (Hz, default 3.5 Hz ~ 210 BPM).

    Returns:
        filtered_rppg: 1D numpy array of filtered green pulse waveform.
        raw_rppg: 1D numpy array of normalized green signal before bandpass.
        metadata: Dictionary containing processing statistics and parameters.
    """
    rgb = np.asarray(rgb_signals, dtype=np.float64)
    n_frames, n_channels = rgb.shape

    if n_channels != 3:
        raise ValueError(f"Expected rgb_signals shape (N, 3), got {rgb.shape}")
    if n_frames < 10:
        raise ValueError(f"Insufficient frames ({n_frames}) for rPPG analysis")

    g = rgb[:, 1]
    g_mean = np.mean(g)
    g_std = np.std(g)

    if g_std < 1e-9:
        g_norm = g - g_mean
    else:
        g_norm = (g - g_mean) / g_std

    # Invert signal so systolic peaks point upwards (blood absorption causes decrease in reflection)
    raw_rppg = -g_norm

    filtered_rppg = temporal_butterworth_bandpass(
        raw_rppg,
        lowcut=lowcut,
        highcut=highcut,
        fs=fps,
        order=3,
    )

    metadata = {
        "algorithm": "GREEN (Single-Channel Photoplethysmography)",
        "reference": "Verkruysse et al., Optics Express 2008",
        "fps": float(fps),
        "total_frames": int(n_frames),
        "duration_sec": float(n_frames / fps) if fps > 0 else 0.0,
        "bandpass_lowcut_hz": float(lowcut),
        "bandpass_highcut_hz": float(highcut),
    }

    return filtered_rppg, raw_rppg, metadata
