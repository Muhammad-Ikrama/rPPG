"""
rPPG Dataset Benchmarking and Statistical Validation Module.

Computes:
1. Mean Absolute Error (MAE): (1/N) * sum(|HR_pred - HR_gt|)
2. Root Mean Square Error (RMSE): sqrt((1/N) * sum((HR_pred - HR_gt)^2))
3. Pearson Correlation Coefficient (r)
4. Bland-Altman statistics (mean bias, 95% limits of agreement: bias +/- 1.96 * SD)
"""

from typing import Dict, Any, List, Tuple
import numpy as np
from scipy import stats


def compute_benchmark_metrics(
    predictions: List[float],
    ground_truths: List[float],
) -> Dict[str, Any]:
    """
    Evaluates algorithmic estimates against reference ground truths.

    Args:
        predictions: List of algorithm estimates (e.g. HR in BPM).
        ground_truths: List of paired reference values.

    Returns:
        Dictionary of statistical validation metrics.
    """
    preds = np.asarray(predictions, dtype=np.float64)
    gts = np.asarray(ground_truths, dtype=np.float64)

    # Filter out any NaN or None pairs
    valid_mask = (~np.isnan(preds)) & (~np.isnan(gts))
    preds = preds[valid_mask]
    gts = gts[valid_mask]

    n = len(preds)
    if n < 2:
        return {
            "samples_count": n,
            "mae": None,
            "rmse": None,
            "pearson_r": None,
            "mean_bias": None,
            "std_error": None,
            "loa_upper": None,
            "loa_lower": None,
            "message": "Insufficient paired samples for benchmark evaluation",
        }

    errors = preds - gts
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # Pearson correlation
    if np.std(preds) > 1e-6 and np.std(gts) > 1e-6:
        r_val, p_val = stats.pearsonr(preds, gts)
        r_val = float(r_val)
        p_val = float(p_val)
    else:
        r_val, p_val = 0.0, 1.0

    # Bland-Altman statistics
    mean_bias = float(np.mean(errors))
    std_diff = float(np.std(errors, ddof=1))
    loa_upper = float(mean_bias + 1.96 * std_diff)
    loa_lower = float(mean_bias - 1.96 * std_diff)

    return {
        "samples_count": n,
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "pearson_r": round(r_val, 3),
        "p_value": round(p_val, 5),
        "mean_bias": round(mean_bias, 2),
        "std_error": round(std_diff, 2),
        "loa_upper": round(loa_upper, 2),
        "loa_lower": round(loa_lower, 2),
        "unit": "BPM",
    }
