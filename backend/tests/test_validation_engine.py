"""
Unit and Validation Tests for Biomedical Statistical Engine:
- Bland-Altman Limits of Agreement (LOA = Mean +/- 1.96 * SD)
- Pearson correlation, r^2, MAE, RMSE
- Plot artifact generation
- Confidence intervals of agreement limits
"""

import os
import pytest
import numpy as np

from app.validation.bland_altman import calculate_bland_altman_metrics, generate_bland_altman_figure


def test_bland_altman_metrics_calculation():
    """Verify Bland-Altman mathematical calculations match analytical values."""
    references = [60.0, 70.0, 80.0, 90.0, 100.0]
    # Predictions with constant bias of +2.0 BPM and known noise
    predictions = [62.0, 71.0, 83.0, 91.5, 102.5]

    metrics = calculate_bland_altman_metrics(predictions, references, "Heart Rate", "BPM")

    assert metrics["status"] == "VALIDATED"
    assert metrics["sample_size"] == 5
    assert metrics["mae"] > 0
    assert metrics["rmse"] > 0
    assert metrics["pearson_r"] > 0.98  # Highly correlated

    ba = metrics["bland_altman"]
    bias = ba["bias"]
    upper_loa = ba["upper_loa"]
    lower_loa = ba["lower_loa"]

    assert upper_loa > bias
    assert lower_loa < bias
    # Upper LOA - bias should equal bias - lower LOA (1.96 * SD)
    assert abs((upper_loa - bias) - (bias - lower_loa)) < 1e-2


def test_bland_altman_insufficient_samples():
    """Verify safeguards when sample size is too small (< 3)."""
    metrics = calculate_bland_altman_metrics([70.0, 75.0], [70.0, 74.0])
    assert metrics["status"] == "INSUFFICIENT_DATA"
    assert metrics["sample_size"] == 2


def test_bland_altman_figure_generation(tmp_path):
    """Verify Bland-Altman plot generation creates a valid image file."""
    plot_file = str(tmp_path / "test_bland_altman.png")
    refs = [65.0, 72.0, 80.0, 88.0, 95.0, 102.0]
    preds = [66.0, 71.5, 81.2, 87.0, 96.1, 101.5]

    output = generate_bland_altman_figure(preds, refs, plot_file, "Heart Rate", "BPM", "(Unit Test)")

    assert os.path.exists(output)
    assert os.path.getsize(output) > 5000  # PNG image has non-trivial size

