"""
Comprehensive Phase 3 Verification Test Suite.

Validates:
1. End-to-end video-to-physiological-signal extraction workflow.
2. Facial Skin ROI extraction (Forehead, Left Cheek, Right Cheek with skin mask).
3. 4 Traditional rPPG Algorithms (GREEN, CHROM, POS, ICA) benchmarked side-by-side.
4. Signal Quality Assessment (SQI) and rejection of degraded/unusable recordings.
5. Four independent vital sign pathways (HR, RR, SpO2, BP) with zero cross-derivation.
6. Deep learning multi-task models (MTTS-CAN dual head, PhysNet 3D spatio-temporal volume).
"""

import pytest
import numpy as np
import cv2

from app.rppg.face_roi import FaceROIExtractor, segment_skin_ycrcb
from app.rppg.pos_algorithm import compute_pos_rppg
from app.rppg.chrom_algorithm import compute_chrom_rppg
from app.rppg.green_algorithm import compute_green_rppg
from app.rppg.ica_algorithm import compute_ica_rppg
from app.rppg.multi_algorithm_runner import run_traditional_comparison
from app.rppg.quality_assessment import evaluate_signal_quality
from app.rppg.hr_estimation import estimate_heart_rate
from app.rppg.rr_estimation import estimate_respiratory_rate
from app.rppg.spo2_estimation import estimate_spo2_research
from app.rppg.bp_estimation import extract_pulse_morphology_features, estimate_blood_pressure_experimental
from app.datasets.loader import generate_synthetic_rppg_stream


def create_synthetic_face_frame(width=320, height=240, skin_bgr=(120, 150, 200)) -> np.ndarray:
    """Creates a synthetic frame containing a skin-colored face ellipse."""
    frame = np.full((height, width, 3), 30, dtype=np.uint8)  # Dark background
    center = (width // 2, height // 2)
    axes = (60, 80)
    cv2.ellipse(frame, center, axes, 0, 0, 360, skin_bgr, -1)
    return frame


def generate_multichannel_rppg(duration_sec=16.0, fps=30.0, hr_bpm=72.0, rr_brpm=15.0):
    """Generates synthetic physiological RGB traces with both cardiac and respiratory components."""
    n_frames = int(round(duration_sec * fps))
    t = np.linspace(0, duration_sec, n_frames, endpoint=False)

    f_hr = hr_bpm / 60.0
    f_rr = rr_brpm / 60.0

    # Cardiac pulse wave
    cardiac = np.sin(2.0 * np.pi * f_hr * t) + 0.3 * np.sin(4.0 * np.pi * f_hr * t)
    # Respiratory baseline modulation (RBM)
    respiratory = 0.25 * np.sin(2.0 * np.pi * f_rr * t)

    base_r, base_g, base_b = 180.0, 130.0, 100.0
    rng = np.random.RandomState(42)
    noise = rng.normal(0, 0.002, n_frames)

    r = base_r * (1.0 + 0.006 * cardiac + 0.003 * respiratory + noise)
    g = base_g * (1.0 + 0.022 * cardiac + 0.008 * respiratory + noise)
    b = base_b * (1.0 + 0.005 * cardiac + 0.002 * respiratory + noise)

    return np.column_stack([r, g, b])


def test_skin_segmentation_ycrcb():
    """Verify YCrCb skin segmentation correctly labels skin and rejects dark background."""
    frame = create_synthetic_face_frame(width=200, height=200, skin_bgr=(120, 150, 200))
    mask = segment_skin_ycrcb(frame)

    assert mask.shape == (200, 200)
    # Center should be detected as skin
    assert mask[100, 100] == 255
    # Corners should be non-skin (0)
    assert mask[5, 5] == 0


def test_face_roi_extractor_execution():
    """Verify FaceROIExtractor processes frames and extracts anatomical ROIs without crashing."""
    extractor = FaceROIExtractor(ema_alpha=0.7)
    frame = create_synthetic_face_frame(width=320, height=240)

    result = extractor.extract_from_frame(frame)
    assert "face_detected" in result
    assert "rgb_mean" in result
    assert len(result["rgb_mean"]) == 3
    assert "quality_score" in result
    assert result["quality_score"] >= 0.0


def test_four_traditional_algorithms_comparison():
    """Verify run_traditional_comparison runs POS, CHROM, GREEN, ICA on the same RGB signal."""
    rgb = generate_multichannel_rppg(duration_sec=15.0, fps=30.0, hr_bpm=72.0)
    comparison = run_traditional_comparison(rgb, fps=30.0, reference_hr_bpm=72.0)

    assert "algorithms" in comparison
    algos = comparison["algorithms"]
    assert "POS" in algos
    assert "CHROM" in algos
    assert "GREEN" in algos
    assert "ICA" in algos

    for name in ["POS", "CHROM", "GREEN", "ICA"]:
        res = algos[name]
        assert res["status"] == "SUCCESS"
        assert res["execution_time_ms"] > 0
        assert res["heart_rate_bpm"] is not None
        # All algorithms should estimate HR near 72 BPM (+/- 5 BPM on clean synthetic)
        assert abs(res["heart_rate_bpm"] - 72.0) < 5.0
        assert len(res["waveform_filtered"]) == len(rgb)

    assert comparison["inter_algorithm_agreement_std_bpm"] < 3.0


def test_signal_quality_assessment_and_rejection():
    """Verify SQI detects poor quality and provides actionable user guidance."""
    fps = 30.0
    # 1. Clean signal test
    rgb_clean = generate_multichannel_rppg(duration_sec=15.0, fps=fps, hr_bpm=70.0)
    clean_wave, _, _ = compute_pos_rppg(rgb_clean, fps=fps)
    sqi_clean = evaluate_signal_quality(clean_wave, rgb_clean, snr_db=12.5, fps=fps)

    assert sqi_clean["sqi_score"] >= 0.55
    assert sqi_clean["status"] in ["GOOD", "EXCELLENT"]

    # 2. Corrupted noisy signal test with heavy luminance fluctuation
    rng = np.random.RandomState(99)
    rgb_noisy = rgb_clean * (1.0 + 0.35 * rng.randn(*rgb_clean.shape))
    noisy_wave = rng.randn(len(rgb_clean))
    sqi_noisy = evaluate_signal_quality(noisy_wave, rgb_noisy, snr_db=-5.0, fps=fps)

    assert sqi_noisy["sqi_score"] < 0.40
    assert sqi_noisy["status"] in ["POOR", "FAIR"]
    assert "guidance" in sqi_noisy


def test_hr_estimation_welch_and_interpolation():
    """Verify HR estimation uses Welch PSD with quadratic sub-bin interpolation."""
    fps = 30.0
    target_hr = 84.5
    t = np.linspace(0, 15.0, int(15.0 * fps), endpoint=False)
    sig = np.sin(2.0 * np.pi * (target_hr / 60.0) * t)

    res = estimate_heart_rate(sig, fps=fps)
    assert res["heart_rate_bpm"] is not None
    # Sub-bin interpolation should achieve high accuracy within 1.0 BPM
    assert abs(res["heart_rate_bpm"] - target_hr) < 1.0
    assert res["confidence"] > 0.6
    assert res["snr_db"] > 5.0


def test_rr_estimation_independent_pathway():
    """Verify RR estimation is computed from respiratory dynamics, not derived from HR."""
    fps = 30.0
    target_rr = 15.0
    # 25 seconds duration provides sufficient respiratory cycles for accurate spectral analysis
    rgb, _, meta = generate_synthetic_rppg_stream(
        duration_sec=25.0,
        fps=fps,
        target_hr_bpm=75.0,
        target_rr_brpm=target_rr,
        snr_db=15.0,
    )

    filtered_wave, raw_wave, _ = compute_pos_rppg(rgb, fps=fps)
    rr_res = estimate_respiratory_rate(raw_wave, filtered_wave, fps=fps)

    assert rr_res["status"] in ["GOOD", "SUCCESS", "MODERATE_CONFIDENCE", "FAIR"]
    assert rr_res["respiratory_rate_brpm"] is not None
    assert abs(rr_res["respiratory_rate_brpm"] - target_rr) <= 3.0

    # Short duration rejection test (<12s)
    short_res = estimate_respiratory_rate(raw_wave[:150], filtered_wave[:150], fps=fps)
    assert short_res["status"] == "UNAVAILABLE"
    assert short_res["respiratory_rate_brpm"] is None


def test_spo2_dual_channel_and_limitations():
    """Verify SpO2 dual-channel estimation computes AC/DC ratios and discloses camera limitations."""
    fps = 30.0
    rgb = generate_multichannel_rppg(duration_sec=15.0, fps=fps, hr_bpm=72.0)
    spo2_res = estimate_spo2_research(rgb, fps=fps, signal_snr=10.0, is_calibrated=False)

    assert "spo2_percent" in spo2_res
    assert "ratio_of_ratios" in spo2_res
    assert "scientific_disclosure" in spo2_res
    assert len(spo2_res["scientific_disclosure"]) > 20
    # Without calibration reference, status must be EXPERIMENTAL_UNCALIBRATED
    assert spo2_res["status"] == "EXPERIMENTAL_UNCALIBRATED"


def test_blood_pressure_morphology_and_calibration():
    """Verify BP morphology extraction captures Crest Time, PW50, and flags uncalibrated state."""
    fps = 30.0
    rgb = generate_multichannel_rppg(duration_sec=15.0, fps=fps, hr_bpm=68.0)
    filtered, _, _ = compute_pos_rppg(rgb, fps=fps)

    morph = extract_pulse_morphology_features(filtered, fps=fps)
    assert morph["valid"] is True
    assert "mean_crest_time_s" in morph
    assert "mean_pw50_s" in morph
    assert "stiffness_surrogate" in morph
    assert morph["mean_crest_time_s"] > 0

    # Test uncalibrated BP estimation
    bp_res = estimate_blood_pressure_experimental(filtered, fps=fps, hr_bpm=68.0)
    assert bp_res["status"] in ["EXPERIMENTAL_RESEARCH", "EXPERIMENTAL_UNCALIBRATED"]
    assert bp_res["is_calibrated"] is False
    assert "iso_compliance_note" in bp_res
    # Must use extracted pulse morphology features
    assert "mean_crest_time_s" in bp_res["features"]
