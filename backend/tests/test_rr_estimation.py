"""
Unit Tests for Respiratory Rate (RR) Estimation.
"""

import numpy as np
import pytest
from app.rppg.rr_estimation import estimate_respiratory_rate
from app.rppg.pos_algorithm import compute_pos_rppg
from app.datasets.loader import generate_synthetic_rppg_stream


def test_rr_estimation_accuracy():
    """Verify that RR estimation detects respiratory baseline/amplitude modulation."""
    fps = 30.0
    duration = 25.0
    target_rr = 16.0

    rgb_signals, _, _ = generate_synthetic_rppg_stream(
        duration_sec=duration,
        fps=fps,
        target_hr_bpm=75.0,
        target_rr_brpm=target_rr,
        snr_db=15.0,
    )

    filtered_rppg, raw_rppg, _ = compute_pos_rppg(rgb_signals, fps=fps)
    rr_result = estimate_respiratory_rate(raw_rppg, filtered_rppg, fps=fps)

    estimated_rr = rr_result["respiratory_rate_brpm"]
    assert estimated_rr is not None
    error = abs(estimated_rr - target_rr)
    assert error <= 3.0, f"Estimated RR {estimated_rr} not within 3.0 BrPM of target {target_rr}"
    assert rr_result["status"] in ["GOOD", "FAIR"]


def test_rr_short_duration_unavailable():
    """Ensure signal shorter than 12s returns UNAVAILABLE status per scientific guidelines."""
    fps = 30.0
    short_raw = np.sin(np.linspace(0, 10, 150))
    short_filt = np.sin(np.linspace(0, 10, 150))

    res = estimate_respiratory_rate(short_raw, short_filt, fps=fps)
    assert res["status"] == "UNAVAILABLE"
    assert res["respiratory_rate_brpm"] is None
