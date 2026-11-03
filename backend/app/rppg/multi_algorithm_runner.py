"""
Multi-Algorithm Traditional rPPG Comparative Runner.

Executes and compares:
1. POS (Wang et al. 2017)
2. CHROM (de Haan & Jeanne 2013)
3. GREEN (Verkruysse et al. 2008)
4. ICA (Poh et al. 2010)

Provides side-by-side waveform extraction, HR estimates, SNR, and execution latency.
"""

from typing import Dict, Any, List, Optional
import time
import numpy as np

from app.rppg.pos_algorithm import compute_pos_rppg
from app.rppg.chrom_algorithm import compute_chrom_rppg
from app.rppg.green_algorithm import compute_green_rppg
from app.rppg.ica_algorithm import compute_ica_rppg
from app.rppg.hr_estimation import estimate_heart_rate


def run_traditional_comparison(
    rgb_signals: np.ndarray,
    fps: float = 30.0,
    reference_hr_bpm: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Executes all 4 traditional rPPG algorithms on the same input RGB temporal trace
    and returns a comparative performance breakdown.

    Args:
        rgb_signals: 2D numpy array of shape (N, 3), spatially averaged R, G, B channels.
        fps: Video frame rate in frames per second (Hz).
        reference_hr_bpm: Optional synchronized ground truth HR from reference instrument (e.g. ECG).

    Returns:
        Dictionary containing comparative metrics, per-algorithm waveforms, and summary ranks.
    """
    rgb = np.asarray(rgb_signals, dtype=np.float64)
    n_frames = len(rgb)

    algorithms = {
        "POS": lambda x, f: compute_pos_rppg(x, fps=f),
        "CHROM": lambda x, f: compute_chrom_rppg(x, fps=f),
        "GREEN": lambda x, f: compute_green_rppg(x, fps=f),
        "ICA": lambda x, f: compute_ica_rppg(x, fps=f),
    }

    results: Dict[str, Any] = {}

    for name, algo_fn in algorithms.items():
        t0 = time.perf_counter()
        try:
            filtered_rppg, raw_rppg, meta = algo_fn(rgb, fps)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            # Estimate Heart Rate
            hr_result = estimate_heart_rate(filtered_rppg, fps=fps)

            hr_bpm = hr_result.get("heart_rate_bpm")
            error_bpm = None
            if reference_hr_bpm is not None and hr_bpm is not None:
                error_bpm = abs(hr_bpm - reference_hr_bpm)

            results[name] = {
                "algorithm": name,
                "status": "SUCCESS",
                "execution_time_ms": round(elapsed_ms, 2),
                "heart_rate_bpm": hr_bpm,
                "confidence": hr_result.get("confidence", 0.0),
                "snr_db": hr_result.get("snr_db", -99.0),
                "error_against_reference_bpm": round(error_bpm, 2) if error_bpm is not None else None,
                "waveform_filtered": [round(float(v), 4) for v in filtered_rppg.tolist()],
                "metadata": meta,
            }
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            results[name] = {
                "algorithm": name,
                "status": "FAILED",
                "error": str(e),
                "execution_time_ms": round(elapsed_ms, 2),
                "heart_rate_bpm": None,
                "confidence": 0.0,
                "snr_db": -99.0,
                "error_against_reference_bpm": None,
                "waveform_filtered": [],
            }

    # Cross-algorithm agreement (standard deviation of predicted HRs)
    valid_hrs = [
        res["heart_rate_bpm"]
        for res in results.values()
        if res.get("heart_rate_bpm") is not None
    ]
    inter_algorithm_std = float(np.std(valid_hrs)) if len(valid_hrs) > 1 else 0.0
    ensemble_median_hr = float(np.median(valid_hrs)) if valid_hrs else None

    return {
        "total_frames": int(n_frames),
        "fps": float(fps),
        "reference_hr_bpm": reference_hr_bpm,
        "ensemble_median_hr_bpm": round(ensemble_median_hr, 1) if ensemble_median_hr is not None else None,
        "inter_algorithm_agreement_std_bpm": round(inter_algorithm_std, 2),
        "algorithms": results,
    }

