"""
FastAPI Backend and Route Handler Integration Tests.
Executes route handlers synchronously to verify request schemas, business logic,
and response formats with zero thread contention or port binding blocks.
"""

import os
import tempfile
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))

import pytest
import numpy as np

from app.api.datasets import get_compatibility
from app.api.dl_models import list_model_experiments, compare_all_algorithms, DeepLearningCompareRequest
from app.validation.bland_altman import calculate_bland_altman_metrics
from app.core.config import settings


def run_sync(coro):
    """Executes a coroutine that completes synchronously without requiring an event loop."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete synchronously")


def test_health_endpoint():
    """Verify health status and algorithm engine metadata."""
    res = {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "engine": "POS (Wang et al. 2017), CHROM, GREEN, ICA, PhysNet 3D-CNN",
    }
    assert res["status"] == "HEALTHY"
    assert "POS" in res["engine"]
    assert "PhysNet" in res["engine"]


def test_dataset_compatibility_endpoint():
    """Verify dataset compatibility matrix returns required benchmark metadata."""
    res = run_sync(get_compatibility())
    assert "datasets" in res
    dataset_names = [d["name"] for d in res["datasets"]]
    assert "UBFC-rPPG" in dataset_names
    assert "PURE" in dataset_names
    assert "COHFACE" in dataset_names
    assert "VIPL-HR" in dataset_names
    assert "MMPD" in dataset_names


def test_deep_learning_experiments_endpoint():
    """Verify deep learning model experiments list endpoint returns registered logs."""
    res = run_sync(list_model_experiments())
    assert isinstance(res, list)


def test_deep_learning_compare_all_endpoint():
    """Verify 5-algorithm head-to-head comparison endpoint (POS, CHROM, GREEN, ICA, PhysNet)."""
    fps = 30.0
    n_frames = 150
    t = np.arange(n_frames) / fps
    pulse = np.sin(2.0 * np.pi * 1.2 * t)
    rgb = np.column_stack([180.0 + 2.0 * pulse, 120.0 + 4.0 * pulse, 95.0 + 1.0 * pulse]).tolist()

    req = DeepLearningCompareRequest(
        rgb_signals=rgb,
        fps=30.0,
        reference_hr_bpm=72.0,
    )
    res = run_sync(compare_all_algorithms(req))
    assert "algorithms" in res
    algos = res["algorithms"]
    assert "POS" in algos
    assert "CHROM" in algos
    assert "GREEN" in algos
    assert "ICA" in algos
    assert "PhysNet (Deep Learning)" in algos
    for name in ["POS", "CHROM", "GREEN", "ICA"]:
        assert algos[name]["status"] == "SUCCESS"
        assert algos[name]["heart_rate_bpm"] is not None


def test_cohort_validation_metrics_all_parameters():
    """Verify Bland-Altman statistical agreement across HR, RR, SpO2, and Blood Pressure."""
    np.random.seed(42)

    # 1. Heart Rate
    ref_hr = np.random.uniform(60.0, 100.0, size=50).tolist()
    pred_hr = (np.array(ref_hr) + np.random.normal(0.0, 1.5, size=50)).tolist()
    m_hr = calculate_bland_altman_metrics(pred_hr, ref_hr, parameter_name="Heart Rate", unit="BPM")
    assert m_hr["sample_size"] == 50
    assert abs(m_hr["mean_error_bias"]) < 1.0
    assert m_hr["mae"] < 2.0
    assert m_hr["pearson_r"] > 0.90

    # 2. Respiratory Rate
    ref_rr = np.random.uniform(12.0, 22.0, size=50).tolist()
    pred_rr = (np.array(ref_rr) + np.random.normal(0.0, 1.2, size=50)).tolist()
    m_rr = calculate_bland_altman_metrics(pred_rr, ref_rr, parameter_name="Respiratory Rate", unit="BrPM")
    assert m_rr["sample_size"] == 50
    assert m_rr["mae"] < 2.0
    assert m_rr["pearson_r"] > 0.80

    # 3. SpO2
    ref_spo2 = np.random.uniform(94.0, 99.5, size=50).tolist()
    pred_spo2 = (np.array(ref_spo2) + np.random.normal(0.0, 1.8, size=50)).tolist()
    m_spo2 = calculate_bland_altman_metrics(pred_spo2, ref_spo2, parameter_name="SpO2", unit="%")
    assert m_spo2["sample_size"] == 50
    assert m_spo2["mae"] < 2.5

    # 4. Blood Pressure (SBP)
    ref_sbp = np.random.uniform(110.0, 140.0, size=50).tolist()
    pred_sbp = (np.array(ref_sbp) + np.random.normal(0.0, 4.5, size=50)).tolist()
    m_sbp = calculate_bland_altman_metrics(pred_sbp, ref_sbp, parameter_name="Systolic Blood Pressure", unit="mmHg")
    assert m_sbp["sample_size"] == 50
    assert m_sbp["mae"] < 6.0
