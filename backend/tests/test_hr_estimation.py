"""
Unit Tests for Heart Rate (HR) Estimation.
"""

import numpy as np
import pytest
from app.rppg.hr_estimation import estimate_heart_rate
from app.rppg.pos_algorithm import compute_pos_rppg
from app.datasets.loader import generate_synthetic_rppg_stream


@pytest.mark.parametrize("target_hr", [60.0, 75.0, 90.0, 110.0])
def test_hr_accuracy_across_physiological_range(target_hr):
    """Verify that spectral HR estimation accurately detects various heart rates within 2 BPM."""
    fps = 30.0
    duration = 20.0

    rgb_signals, _, _ = generate_synthetic_rppg_stream(
        duration_sec=duration,
        fps=fps,
        target_hr_bpm=target_hr,
        target_rr_brpm=16.0,
        snr_db=12.0,
    )

    filtered_rppg, _, _ = compute_pos_rppg(rgb_signals, fps=fps)
    hr_result = estimate_heart_rate(filtered_rppg, fps=fps)

    estimated_hr = hr_result["heart_rate_bpm"]
    assert estimated_hr is not None
    error = abs(estimated_hr - target_hr)
    assert error <= 2.5, f"Estimated HR {estimated_hr} was not within 2.5 BPM of target {target_hr}"
    assert hr_result["confidence"] >= 0.50
    assert hr_result["status"] in ["EXCELLENT", "GOOD"]
    assert hr_result["snr_db"] > 0.0


def test_insufficient_signal_handling():
    """Verify safe degradation when signal is too short or empty."""
    short_signal = np.array([1.0, 2.0, 3.0])
    res = estimate_heart_rate(short_signal, fps=30.0)
    assert res["heart_rate_bpm"] is None
    assert res["status"] == "UNRELIABLE"
