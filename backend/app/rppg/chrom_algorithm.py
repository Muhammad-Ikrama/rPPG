"""
Chrominance-Based (CHROM) Remote Photoplethysmography Algorithm.

Based on:
de Haan, G., & Jeanne, V. (2013).
"Robust pulse rate from chrominance-based rPPG".
IEEE Transactions on Biomedical Engineering, 60(10), 2878-2886.
doi: 10.1109/TBME.2013.2266196
"""

from typing import Dict, Any, Tuple
import numpy as np
from app.rppg.pos_algorithm import temporal_butterworth_bandpass


def compute_chrom_rppg(
    rgb_signals: np.ndarray,
    fps: float = 30.0,
    window_sec: float = 1.6,
    stride: int = 1,
    lowcut: float = 0.7,
    highcut: float = 3.5,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    Extracts rPPG pulse signal using the Chrominance-based (CHROM) algorithm.

    Mathematical steps:
    1. Spatial averaging over facial skin ROI yields temporal channels C(t) = [R(t), G(t), B(t)].
    2. In a sliding temporal window of length L:
       Cn(t) = C(t) / mean(C(t))  [Temporal normalization]
    3. Chrominance signals:
       Xs = 3 * Rn - 2 * Gn
       Ys = 1.5 * Rn + Gn - 1.5 * Bn
    4. Bandpass filter Xs and Ys within physiological band [lowcut, highcut] Hz.
    5. Adaptive alpha tuning:
       alpha = std(X_filtered) / std(Y_filtered)
    6. Pulse signal:
       S = X_filtered - alpha * Y_filtered
    7. Overlap-add (OLA) window reconstruction across the full video duration.

    Args:
        rgb_signals: 2D numpy array of shape (N, 3), spatially averaged R, G, B.
        fps: Video frame rate in frames per second (Hz).
        window_sec: Window length in seconds (standard: 1.6s).
        stride: Temporal window stride in frames (default: 1 frame).
        lowcut: Bandpass filter lower bound (Hz).
        highcut: Bandpass filter upper bound (Hz).

    Returns:
        filtered_rppg: 1D numpy array of filtered pulse waveform.
        raw_rppg: 1D numpy array of reconstructed CHROM signal before final bandpass.
        metadata: Dictionary containing processing statistics and parameters.
    """
    rgb = np.asarray(rgb_signals, dtype=np.float64)
    n_frames, n_channels = rgb.shape

    if n_channels != 3:
        raise ValueError(f"Expected rgb_signals shape (N, 3), got {rgb.shape}")
    if n_frames < 10:
        raise ValueError(f"Insufficient frames ({n_frames}) for rPPG analysis")

    window_length = int(round(fps * window_sec))
    window_length = max(10, min(window_length, n_frames))

    reconstructed_s = np.zeros(n_frames, dtype=np.float64)
    overlap_count = np.zeros(n_frames, dtype=np.float64)

    if n_frames <= window_length:
        window_indices = [(0, n_frames)]
    else:
        window_indices = [
            (i, i + window_length)
            for i in range(0, n_frames - window_length + 1, stride)
        ]
        if window_indices[-1][1] < n_frames:
            window_indices.append((n_frames - window_length, n_frames))

    for start_idx, end_idx in window_indices:
        window_rgb = rgb[start_idx:end_idx, :]

        # Temporal normalization
        channel_means = np.mean(window_rgb, axis=0)
        channel_means = np.where(channel_means == 0, 1e-6, channel_means)
        c_norm = window_rgb / channel_means

        r_norm = c_norm[:, 0]
        g_norm = c_norm[:, 1]
        b_norm = c_norm[:, 2]

        # 3. Chrominance differences (de Haan & Jeanne 2013)
        xs = 3.0 * r_norm - 2.0 * g_norm
        ys = 1.5 * r_norm + g_norm - 1.5 * b_norm

        # 4. Zero-phase bandpass filter on components
        xs_f = temporal_butterworth_bandpass(xs, lowcut=lowcut, highcut=highcut, fs=fps, order=2)
        ys_f = temporal_butterworth_bandpass(ys, lowcut=lowcut, highcut=highcut, fs=fps, order=2)

        # 5. Adaptive ratio of standard deviations
        std_y = np.std(ys_f)
        if std_y < 1e-9:
            alpha = 0.0
        else:
            alpha = np.std(xs_f) / std_y

        # 6. Pulse signal
        s_win = xs_f - alpha * ys_f
        s_win = s_win - np.mean(s_win)

        # 7. Overlap-add
        reconstructed_s[start_idx:end_idx] += s_win
        overlap_count[start_idx:end_idx] += 1.0

    nonzero_mask = overlap_count > 0
    reconstructed_s[nonzero_mask] /= overlap_count[nonzero_mask]
    if not np.all(nonzero_mask):
        reconstructed_s[~nonzero_mask] = 0.0

    raw_rppg = reconstructed_s.copy()

    # Final zero-phase pass
    filtered_rppg = temporal_butterworth_bandpass(
        raw_rppg,
        lowcut=lowcut,
        highcut=highcut,
        fs=fps,
        order=3,
    )

    metadata = {
        "algorithm": "CHROM (Chrominance-based)",
        "reference": "de Haan & Jeanne, IEEE TBME 2013",
        "fps": float(fps),
        "total_frames": int(n_frames),
        "duration_sec": float(n_frames / fps) if fps > 0 else 0.0,
        "window_length_frames": int(window_length),
        "stride": int(stride),
        "bandpass_lowcut_hz": float(lowcut),
        "bandpass_highcut_hz": float(highcut),
    }

    return filtered_rppg, raw_rppg, metadata
