"""
Unit Tests for the Plane-Orthogonal-to-Skin (POS) Algorithm.
"""

import numpy as np
import pytest
from app.rppg.pos_algorithm import compute_pos_rppg, temporal_butterworth_bandpass
from app.datasets.loader import generate_synthetic_rppg_stream


def test_pos_synthetic_stream():
    """Verify that POS recovers the cardiac pulsation from synthetic RGB data."""
    target_hr = 72.0
    fps = 30.0
    duration = 15.0

    rgb_signals, gt_pulse, meta = generate_synthetic_rppg_stream(
        duration_sec=duration,
        fps=fps,
        target_hr_bpm=target_hr,
        target_rr_brpm=15.0,
        snr_db=10.0,
    )

    filtered_rppg, raw_rppg, metadata = compute_pos_rppg(
        rgb_signals,
        fps=fps,
        window_sec=1.6,
        stride=1,
    )

    assert len(filtered_rppg) == len(rgb_signals)
    assert len(raw_rppg) == len(rgb_signals)
    assert metadata["algorithm"].startswith("POS")
    assert metadata["fps"] == fps

    # Check that correlation with ground-truth cardiac wave is positive and strong
    corr = np.corrcoef(filtered_rppg[30:-30], gt_pulse[30:-30])[0, 1]
    # Because blood volume changes inversely with reflected light, correlation is either high positive or high negative (phase inverted)
    assert abs(corr) > 0.40, f"Correlation with ground-truth pulse {corr} should be substantial"


def test_temporal_butterworth_bandpass():
    """Verify that bandpass filter passes 1.2 Hz (72 BPM) and attenuates high/low noise."""
    fs = 30.0
    t = np.arange(300) / fs
    sig_1hz = np.sin(2 * np.pi * 1.2 * t)  # 72 BPM -> within [0.7, 3.5] Hz
    noise_low = 5.0 * np.sin(2 * np.pi * 0.1 * t)  # 6 BPM -> below passband
    noise_high = 2.0 * np.sin(2 * np.pi * 8.0 * t)  # 480 BPM -> above passband

    composite = sig_1hz + noise_low + noise_high
    filtered = temporal_butterworth_bandpass(composite, lowcut=0.7, highcut=3.5, fs=fs)

    # 1.2 Hz component should dominate the filtered output
    assert np.std(filtered) > 0.3
    # Low frequency drift should be suppressed
    assert abs(np.mean(filtered)) < 0.1
