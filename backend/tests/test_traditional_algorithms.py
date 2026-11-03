"""
Unit and Validation Tests for Traditional rPPG Algorithms:
- POS (Wang et al. 2017)
- CHROM (de Haan & Jeanne 2013)
- GREEN (Verkruysse et al. 2008)
- ICA (Poh et al. 2010)
- Multi-Algorithm Comparative Runner
"""

import pytest
import numpy as np

from app.rppg.chrom_algorithm import compute_chrom_rppg
from app.rppg.green_algorithm import compute_green_rppg
from app.rppg.ica_algorithm import compute_ica_rppg
from app.rppg.multi_algorithm_runner import run_traditional_comparison
from app.rppg.hr_estimation import estimate_heart_rate


def generate_synthetic_pulsatile_rgb(
    duration_sec: float = 15.0,
    fps: float = 30.0,
    target_hr_bpm: float = 72.0,
    snr_db: float = 12.0,
) -> np.ndarray:
    """Generates synthetic physiological RGB traces with realistic optical pulse modulation."""
    n_frames = int(round(duration_sec * fps))
    t = np.linspace(0, duration_sec, n_frames, endpoint=False)
    target_freq = target_hr_bpm / 60.0

    # Cardiac pulsatile harmonics
    pulse_wave = (
        np.sin(2.0 * np.pi * target_freq * t)
        + 0.35 * np.sin(4.0 * np.pi * target_freq * t)
        + 0.15 * np.sin(6.0 * np.pi * target_freq * t)
    )

    # Base skin reflection: High in Red, moderate in Green, lower in Blue
    base_r = 175.0
    base_g = 120.0
    base_b = 95.0

    # Differential modulation amplitude (Green has highest optical absorption for HbO2)
    mod_r = 0.008
    mod_g = 0.025
    mod_b = 0.006

    noise_amp = 0.025 / (10.0 ** (snr_db / 20.0))
    rng = np.random.RandomState(42)

    r_sig = base_r * (1.0 + mod_r * pulse_wave + rng.normal(0, noise_amp, n_frames))
    g_sig = base_g * (1.0 + mod_g * pulse_wave + rng.normal(0, noise_amp, n_frames))
    b_sig = base_b * (1.0 + mod_b * pulse_wave + rng.normal(0, noise_amp, n_frames))

    return np.column_stack([r_sig, g_sig, b_sig])


def test_chrom_algorithm_accuracy():
    """Verify CHROM algorithm extracts correct heart rate within 2.0 BPM."""
    fps = 30.0
    target_hr = 75.0
    rgb = generate_synthetic_pulsatile_rgb(duration_sec=15.0, fps=fps, target_hr_bpm=target_hr, snr_db=15.0)

    filtered, raw, meta = compute_chrom_rppg(rgb, fps=fps)
    assert len(filtered) == len(rgb)
    assert meta["algorithm"] == "CHROM (Chrominance-based)"

    hr_res = estimate_heart_rate(filtered, fps=fps)
    assert hr_res["heart_rate_bpm"] is not None
    assert abs(hr_res["heart_rate_bpm"] - target_hr) <= 2.0
    assert hr_res["confidence"] > 0.65


def test_green_algorithm_accuracy():
    """Verify single green channel method extracts correct heart rate within 2.0 BPM."""
    fps = 30.0
    target_hr = 80.0
    rgb = generate_synthetic_pulsatile_rgb(duration_sec=15.0, fps=fps, target_hr_bpm=target_hr, snr_db=15.0)

    filtered, raw, meta = compute_green_rppg(rgb, fps=fps)
    assert len(filtered) == len(rgb)
    assert meta["algorithm"].startswith("GREEN")

    hr_res = estimate_heart_rate(filtered, fps=fps)
    assert hr_res["heart_rate_bpm"] is not None
    assert abs(hr_res["heart_rate_bpm"] - target_hr) <= 2.0


def test_ica_algorithm_accuracy():
    """Verify FastICA decomposes RGB mixtures and isolates arterial pulse component."""
    fps = 30.0
    target_hr = 68.0
    rgb = generate_synthetic_pulsatile_rgb(duration_sec=15.0, fps=fps, target_hr_bpm=target_hr, snr_db=15.0)

    filtered, raw, meta = compute_ica_rppg(rgb, fps=fps)
    assert len(filtered) == len(rgb)
    assert meta["algorithm"].startswith("ICA")
    assert 0 <= meta["selected_component_index"] <= 2

    hr_res = estimate_heart_rate(filtered, fps=fps)
    assert hr_res["heart_rate_bpm"] is not None
    assert abs(hr_res["heart_rate_bpm"] - target_hr) <= 2.5


def test_multi_algorithm_comparison():
    """Verify unified comparative runner executes all 4 methods and computes inter-algorithm statistics."""
    fps = 30.0
    target_hr = 70.0
    rgb = generate_synthetic_pulsatile_rgb(duration_sec=15.0, fps=fps, target_hr_bpm=target_hr, snr_db=15.0)

    comparison = run_traditional_comparison(rgb, fps=fps, reference_hr_bpm=target_hr)

    assert "algorithms" in comparison
    algos = comparison["algorithms"]
    assert "POS" in algos
    assert "CHROM" in algos
    assert "GREEN" in algos
    assert "ICA" in algos

    for name in ["POS", "CHROM", "GREEN", "ICA"]:
        assert algos[name]["status"] == "SUCCESS"
        assert algos[name]["heart_rate_bpm"] is not None
        assert algos[name]["error_against_reference_bpm"] is not None
        assert algos[name]["error_against_reference_bpm"] < 3.0

    # Cross-algorithm agreement standard deviation should be tight (< 2.0 BPM)
    assert comparison["inter_algorithm_agreement_std_bpm"] < 2.0
    assert abs(comparison["ensemble_median_hr_bpm"] - target_hr) < 2.0

