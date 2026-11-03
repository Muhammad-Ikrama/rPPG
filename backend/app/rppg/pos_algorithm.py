"""
Plane-Orthogonal-to-Skin (POS) Remote Photoplethysmography Algorithm.

Based on:
Wang, W., den Brinker, A. C., Stuijk, S., & de Haan, G. (2017).
"Algorithmic Principles of Remote PPG".
IEEE Transactions on Biomedical Engineering, 64(7), 1479-1491.
doi: 10.1109/TBME.2016.2609282
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np
from scipy import signal


def temporal_butterworth_bandpass(
    data: np.ndarray,
    lowcut: float = 0.7,
    highcut: float = 3.5,
    fs: float = 30.0,
    order: int = 3,
) -> np.ndarray:
    """
    Applies a zero-phase Butterworth bandpass filter to 1D rPPG temporal signal.

    Args:
        data: 1D numpy array of temporal rPPG signal.
        lowcut: Lower cutoff frequency in Hz (0.7 Hz ~ 42 BPM).
        highcut: Upper cutoff frequency in Hz (3.5 Hz ~ 210 BPM).
        fs: Sampling rate / frame rate in Hz.
        order: Filter order (default 3, giving 6th-order after forward-backward).

    Returns:
        Filtered 1D numpy array.
    """
    if len(data) < 15:
        return data - np.mean(data)

    nyq = 0.5 * fs
    # Ensure cutoffs are valid relative to Nyquist frequency
    low = max(0.01, min(lowcut / nyq, 0.95))
    high = min(0.99, max(low + 0.05, highcut / nyq))

    # Design filter
    b, a = signal.butter(order, [low, high], btype="bandpass")

    # If data length is too short for default padlen, adjust padlen
    padlen = min(3 * max(len(a), len(b)), len(data) - 1)
    if padlen <= 0:
        return data - np.mean(data)

    try:
        filtered = signal.filtfilt(b, a, data, padlen=padlen)
        return filtered
    except Exception:
        # Fallback to mean-centering if filtfilt encounters boundary condition
        return data - np.mean(data)


def compute_pos_rppg(
    rgb_signals: np.ndarray,
    fps: float = 30.0,
    window_sec: float = 1.6,
    stride: int = 1,
    lowcut: float = 0.7,
    highcut: float = 3.5,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Extracts rPPG pulse signal using the Plane-Orthogonal-to-Skin (POS) algorithm.

    Mathematical steps:
    1. Spatial averaging over facial ROI yields temporal channels C(t) = [R(t), G(t), B(t)].
    2. In a sliding temporal window of length L:
       Cn(t) = C(t) / mean(C(t))  [Temporal normalization]
    3. Project onto POS plane:
       S1(t) = G_n(t) - B_n(t)
       S2(t) = G_n(t) + B_n(t) - 2 * R_n(t)
    4. Adaptive alpha tuning:
       alpha = std(S1) / std(S2)
       h(t) = S1(t) + alpha * S2(t)
    5. Overlap-add (OLA) window reconstruction.
    6. Bandpass filtering within physiological heart rate range [0.7, 3.5] Hz.

    Args:
        rgb_signals: 2D numpy array of shape (N, 3), spatially averaged R, G, B.
        fps: Video frame rate in frames per second (Hz).
        window_sec: Window length in seconds (standard: 1.6s).
        stride: Temporal window stride in frames (default: 1 frame).
        lowcut: Bandpass filter lower bound (Hz).
        highcut: Bandpass filter upper bound (Hz).

    Returns:
        filtered_rppg: 1D numpy array of filtered pulse waveform.
        raw_rppg: 1D numpy array of reconstructed POS signal before bandpass.
        metadata: Dictionary containing processing statistics and parameters.
    """
    rgb = np.asarray(rgb_signals, dtype=np.float64)
    n_frames, n_channels = rgb.shape

    if n_channels != 3:
        raise ValueError(f"Expected rgb_signals shape (N, 3), got {rgb.shape}")
    if n_frames < 10:
        raise ValueError(f"Insufficient frames ({n_frames}) for rPPG analysis")

    # Handle window size
    window_length = int(round(fps * window_sec))
    # Window length must be between 10 frames and total frame count
    window_length = max(10, min(window_length, n_frames))

    # Buffers for overlap-add reconstruction
    reconstructed_h = np.zeros(n_frames, dtype=np.float64)
    overlap_count = np.zeros(n_frames, dtype=np.float64)

    # If the video is shorter than window_length, evaluate as a single window
    if n_frames <= window_length:
        window_indices = [(0, n_frames)]
    else:
        window_indices = [
            (i, i + window_length)
            for i in range(0, n_frames - window_length + 1, stride)
        ]
        # Ensure the trailing frames are covered if step missed the end
        if window_indices[-1][1] < n_frames:
            window_indices.append((n_frames - window_length, n_frames))

    # Process sliding windows
    for start_idx, end_idx in window_indices:
        window_rgb = rgb[start_idx:end_idx, :]  # shape: (L, 3)

        # 1. Temporal normalization: divide each channel by its mean over window
        channel_means = np.mean(window_rgb, axis=0)
        # Avoid division by zero
        channel_means = np.where(channel_means == 0, 1e-6, channel_means)
        c_norm = window_rgb / channel_means

        r_norm = c_norm[:, 0]
        g_norm = c_norm[:, 1]
        b_norm = c_norm[:, 2]

        # 2. Orthogonal skin plane projection
        s1 = g_norm - b_norm
        s2 = g_norm + b_norm - 2.0 * r_norm

        # 3. Dynamic alpha ratio
        std_s1 = np.std(s1)
        std_s2 = np.std(s2)

        if std_s2 < 1e-9:
            alpha = 0.0
        else:
            alpha = std_s1 / std_s2

        # 4. Construct window rPPG signal and zero-mean
        h_win = s1 + alpha * s2
        h_win = h_win - np.mean(h_win)

        # 5. Overlap-add
        reconstructed_h[start_idx:end_idx] += h_win
        overlap_count[start_idx:end_idx] += 1.0

    # Normalize by overlap counts
    nonzero_mask = overlap_count > 0
    reconstructed_h[nonzero_mask] /= overlap_count[nonzero_mask]

    # Fill any untouched edges if any
    if not np.all(nonzero_mask):
        reconstructed_h[~nonzero_mask] = 0.0

    raw_rppg = reconstructed_h.copy()

    # 6. Zero-phase bandpass filtering in physiological range
    filtered_rppg = temporal_butterworth_bandpass(
        raw_rppg,
        lowcut=lowcut,
        highcut=highcut,
        fs=fps,
        order=3,
    )

    metadata = {
        "algorithm": "POS (Plane-Orthogonal-to-Skin)",
        "reference": "Wang et al., IEEE TBME 2017",
        "fps": float(fps),
        "total_frames": int(n_frames),
        "duration_sec": float(n_frames / fps) if fps > 0 else 0.0,
        "window_length_frames": int(window_length),
        "stride": int(stride),
        "bandpass_lowcut_hz": float(lowcut),
        "bandpass_highcut_hz": float(highcut),
    }

    return filtered_rppg, raw_rppg, metadata
