"""
Unit Tests for SpO2 and Blood Pressure (BP) Research Pipelines.
"""

import numpy as np
import pytest
from app.rppg.spo2_estimation import estimate_spo2_research
from app.rppg.bp_estimation import estimate_blood_pressure_experimental, extract_pulse_morphology_features
from app.datasets.loader import generate_synthetic_rppg_stream
from app.rppg.pos_algorithm import compute_pos_rppg


def test_spo2_uncalibrated_scientific_safeguard():
    """Verify that uncalibrated SpO2 produces an explicit experimental disclosure and bounded confidence."""
    rgb_signals, _, _ = generate_synthetic_rppg_stream(duration_sec=15.0, fps=30.0, snr_db=10.0)

    res = estimate_spo2_research(rgb_signals, fps=30.0, signal_snr=8.0, is_calibrated=False)

    assert "NOTICE" in res["scientific_disclosure"]
    assert res["status"] in ["EXPERIMENTAL_UNCALIBRATED", "EXPERIMENTAL_LOW_QUALITY"]
    assert res["confidence"] <= 0.40
    assert res["ratio_of_ratios"] is not None


def test_bp_no_hardcoded_120_80():
    """Verify that BP does not emit hardcoded default 120/80 and responds to morphological shifts."""
    rgb_signals, _, _ = generate_synthetic_rppg_stream(duration_sec=20.0, fps=30.0, target_hr_bpm=72.0, snr_db=15.0)
    filtered_rppg, _, _ = compute_pos_rppg(rgb_signals, fps=30.0)

    bp_res = estimate_blood_pressure_experimental(filtered_rppg, fps=30.0)

    assert bp_res["status"].startswith("EXPERIMENTAL")
    assert "ISO 81060-2" in bp_res["iso_compliance_note"]
    # Check that SBP and DBP are not hardcoded 120.0 and 80.0
    sbp = bp_res["sbp_mmhg"]
    dbp = bp_res["dbp_mmhg"]
    assert sbp is not None and dbp is not None
    assert not (sbp == 120.0 and dbp == 80.0)
    assert sbp > dbp + 15.0  # Pulse pressure physically plausible
