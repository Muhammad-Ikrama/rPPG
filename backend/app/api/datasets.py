"""
Dataset Compatibility and Benchmarking Evaluation API Routes.
"""

from typing import Dict, Any, List
from fastapi import APIRouter
from pydantic import BaseModel
from app.datasets.compatibility import get_compatibility_summary, DATASET_COMPATIBILITY_MATRIX
from app.datasets.benchmark import compute_benchmark_metrics
from app.datasets.loader import generate_synthetic_rppg_stream
from app.rppg.pos_algorithm import compute_pos_rppg
from app.rppg.hr_estimation import estimate_heart_rate

router = APIRouter(prefix="/datasets", tags=["Dataset Management & Benchmarking"])


class BenchmarkRequest(BaseModel):
    test_bpm_values: List[float] = [55.0, 68.0, 75.0, 88.0, 102.0, 120.0]
    snr_db: float = 10.0
    duration_sec: float = 15.0


@router.get("/compatibility")
async def get_compatibility():
    """
    Returns public dataset compatibility matrix for UBFC-rPPG, PURE, COHFACE, VIPL-HR, and MMPD.
    Documents available ground-truth physiological parameters (HR, RR, SpO2, BP).
    """
    return {
        "datasets": get_compatibility_summary(),
        "detailed_matrix": DATASET_COMPATIBILITY_MATRIX,
        "scientific_note": (
            "Most facial video datasets (UBFC, PURE, VIPL) record pulse oximeter references "
            "providing accurate HR and normoxic baseline SpO2. None provide arterial or cuff blood pressure "
            "labels, which necessitates dedicated paired protocol calibration."
        ),
    }


@router.post("/benchmark-run")
async def run_benchmark(payload: BenchmarkRequest) -> Dict[str, Any]:
    """
    Runs automated validation of the POS algorithm across multiple physiological heart rates.
    Computes MAE, RMSE, Pearson r, and Bland-Altman limits of agreement.
    """
    predictions = []
    ground_truths = []
    sample_records = []

    fps = 30.0

    for target_hr in payload.test_bpm_values:
        rgb_stream, _, meta = generate_synthetic_rppg_stream(
            duration_sec=payload.duration_sec,
            fps=fps,
            target_hr_bpm=target_hr,
            snr_db=payload.snr_db,
        )

        filtered_rppg, _, _ = compute_pos_rppg(rgb_stream, fps=fps)
        hr_res = estimate_heart_rate(filtered_rppg, fps=fps)

        est_hr = hr_res.get("heart_rate_bpm")
        if est_hr is not None:
            predictions.append(est_hr)
            ground_truths.append(target_hr)
            sample_records.append({
                "target_hr": target_hr,
                "estimated_hr": est_hr,
                "error": round(abs(est_hr - target_hr), 2),
                "confidence": hr_res.get("confidence"),
                "snr_db": hr_res.get("snr_db"),
                "status": hr_res.get("status"),
            })

    metrics = compute_benchmark_metrics(predictions, ground_truths)

    return {
        "status": "COMPLETED",
        "algorithm": "POS (Wang et al. 2017)",
        "metrics": metrics,
        "sample_records": sample_records,
    }
