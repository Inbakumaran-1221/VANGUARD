"""Tests for gap detection evaluation metrics."""

import tempfile
from pathlib import Path

import pandas as pd

from src.evaluation import evaluate_gap_detection_precision
from src.models import AccessibilityScore, PriorityLevel


def test_evaluate_gap_detection_precision_returns_metrics():
    score = AccessibilityScore(
        stop_id="STOP_001",
        stop_name="Main",
        latitude=0.0,
        longitude=0.0,
        gap_score=70.0,
        priority_level=PriorityLevel.HIGH,
        missing_features=["ramp", "lighting"],
        critical_gaps=[],
        grievance_count=0,
        top_themes=[],
        recommendations=[],
    )

    temp_dir = Path(tempfile.mkdtemp())
    csv_path = temp_dir / "ground_truth.csv"

    pd.DataFrame([
        {"stop_id": "STOP_001", "missing_features": "ramp,tactile_pavement"},
    ]).to_csv(csv_path, index=False)

    metrics = evaluate_gap_detection_precision([score], str(csv_path))

    assert metrics
    assert metrics["evaluated_stops"] == 1.0
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1_score"] == 0.5
