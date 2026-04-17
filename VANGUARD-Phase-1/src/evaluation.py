"""Evaluation utilities for gap detection quality against ground truth."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set

import pandas as pd

from src.models import AccessibilityScore
from src.utils import get_logger

logger = get_logger(__name__)

FEATURE_COLUMNS = [
    "has_ramp",
    "has_audio_signals",
    "has_tactile_pavement",
    "has_seating",
    "has_lighting",
    "has_staff_assistance",
    "has_restroom",
    "has_information_board",
    "accessible_entrance",
    "level_platform",
]


def _normalize_feature_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _extract_ground_truth_missing(row: pd.Series) -> Set[str]:
    if "missing_features" in row and pd.notna(row["missing_features"]):
        raw = str(row["missing_features"])
        return {_normalize_feature_name(item) for item in raw.replace("|", ",").split(",") if item.strip()}

    missing: Set[str] = set()
    for feature in FEATURE_COLUMNS:
        if feature in row:
            value = row.get(feature)
            if pd.isna(value):
                continue
            is_present = str(value).strip().lower() in {"true", "1", "yes", "y"}
            if not is_present:
                missing.add(feature.replace("has_", ""))
    return missing


def evaluate_gap_detection_precision(
    scores: List[AccessibilityScore],
    ground_truth_csv_path: str,
) -> Dict[str, float]:
    """Compute precision/recall/F1 for predicted missing features."""
    if not ground_truth_csv_path or not Path(ground_truth_csv_path).exists():
        return {}

    if not scores:
        return {}

    score_by_stop = {s.stop_id: s for s in scores}

    df = pd.read_csv(ground_truth_csv_path)
    if "stop_id" not in df.columns:
        logger.warning("Ground truth CSV missing required stop_id column")
        return {}

    tp = 0
    fp = 0
    fn = 0
    evaluated_stops = 0

    for _, row in df.iterrows():
        stop_id = str(row.get("stop_id", "")).strip()
        if not stop_id or stop_id not in score_by_stop:
            continue

        predicted = {_normalize_feature_name(f) for f in score_by_stop[stop_id].missing_features}
        truth = {_normalize_feature_name(f) for f in _extract_ground_truth_missing(row)}

        tp += len(predicted & truth)
        fp += len(predicted - truth)
        fn += len(truth - predicted)
        evaluated_stops += 1

    if evaluated_stops == 0:
        return {}

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    return {
        "evaluated_stops": float(evaluated_stops),
        "true_positives": float(tp),
        "false_positives": float(fp),
        "false_negatives": float(fn),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
    }
