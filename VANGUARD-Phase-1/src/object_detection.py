"""Accessibility object detection for transit images."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.image_processor import PreparedImage
from src.models import ImageAuditSummary, ImageDetection

try:
    from ultralytics import YOLO  # type: ignore

    HAS_ULTRALYTICS = True
except Exception:  # pragma: no cover - optional dependency
    YOLO = None
    HAS_ULTRALYTICS = False


ACCESSIBILITY_LABELS = {
    "positive": {"ramp", "handrail", "tactile_paving", "curb_cut", "low_floor_bus", "priority_seating"},
    "negative": {"obstruction", "blocked_entrance", "poor_lighting", "broken_path", "crowding"},
}


class ImageDetectionResult(BaseModel):
    """Structured output for a single image prediction."""

    image_id: str = Field(...)
    image_name: str = Field(...)
    source_path: str = Field(...)
    stop_id: Optional[str] = Field(default=None)
    detector: str = Field(default="demo_fallback")
    detections: List[ImageDetection] = Field(default_factory=list)
    inferred_features: Dict[str, bool] = Field(default_factory=dict)
    overall_signal: str = Field(default="unknown")
    overall_confidence: float = Field(default=0.0)
    image_width: Optional[int] = Field(default=None)
    image_height: Optional[int] = Field(default=None)

    def to_summary(self, source_path: str) -> ImageAuditSummary:
        return ImageAuditSummary(
            image_id=self.image_id,
            image_name=self.image_name,
            source_path=source_path,
            stop_id=self.stop_id,
            detector=self.detector,
            image_width=self.image_width,
            image_height=self.image_height,
            detections=self.detections,
            inferred_features=self.inferred_features,
            overall_signal=self.overall_signal,
            overall_confidence=self.overall_confidence,
        )


class AccessibilityObjectDetector:
    """Detect accessibility-related objects in bus and stop photos."""

    def __init__(self, model_path: Optional[str] = None, detector_mode: str = "auto"):
        self.model_path = model_path
        self.mode = detector_mode
        self.model = None

        if detector_mode == "demo":
            self.mode = "demo"
            return

        if not HAS_ULTRALYTICS:
            self.mode = "demo"
            return

        candidate_model = model_path or "yolov8n.pt"
        try:
            self.model = YOLO(candidate_model)
            self.mode = "real"
        except Exception:
            self.model = None
            self.mode = "demo"

    @staticmethod
    def _demo_labels(image_path: str) -> List[ImageDetection]:
        name = Path(image_path).stem.lower()
        labels: List[ImageDetection] = []

        keyword_map = {
            "ramp": "ramp",
            "handrail": "handrail",
            "tactile": "tactile_paving",
            "curb": "curb_cut",
            "seat": "priority_seating",
            "light": "poor_lighting",
            "dark": "poor_lighting",
            "block": "blocked_entrance",
            "obstruct": "obstruction",
            "crowd": "crowding",
            "door": "bus_door",
            "bus": "low_floor_bus",
        }

        for keyword, label in keyword_map.items():
            if keyword in name:
                labels.append(ImageDetection(label=label, confidence=0.85, source="demo_fallback"))

        if not labels:
            labels.append(ImageDetection(label="unknown", confidence=0.25, source="demo_fallback"))

        return labels

    def predict(self, prepared_image: PreparedImage) -> ImageDetectionResult:
        if self.model is None:
            # Use original name so keyword-based demo fallback remains deterministic in tests.
            detections = self._demo_labels(prepared_image.original_name)
            labels = [d.label for d in detections]
            inferred = {label: label in ACCESSIBILITY_LABELS["positive"] for label in labels if label != "unknown"}
            signal = "positive" if any(inferred.values()) else ("negative" if any(label in ACCESSIBILITY_LABELS["negative"] for label in labels) else "unknown")
            confidence = max((d.confidence for d in detections), default=0.0)
            return ImageDetectionResult(
                image_id=prepared_image.image_id,
                image_name=prepared_image.original_name,
                source_path=prepared_image.stored_path,
                stop_id=prepared_image.stop_id,
                detector="demo_fallback",
                detections=detections,
                inferred_features=inferred,
                overall_signal=signal,
                overall_confidence=confidence,
                image_width=prepared_image.width,
                image_height=prepared_image.height,
            )

        results = self.model.predict(prepared_image.stored_path, verbose=False)
        detections: List[ImageDetection] = []
        inferred: Dict[str, bool] = {}

        for result in results:
            names = result.names
            boxes = getattr(result, "boxes", [])
            for box in boxes:
                label = names[int(box.cls[0])]
                confidence = float(box.conf[0])
                bbox = [float(v) for v in box.xyxy[0].tolist()]
                detections.append(ImageDetection(label=label, confidence=confidence, bbox=bbox, source="ultralytics"))
                inferred[label] = confidence >= 0.5

        if not detections:
            detections.append(ImageDetection(label="unknown", confidence=0.0, source="ultralytics"))

        detected_labels = {d.label for d in detections}
        positive = bool(detected_labels & ACCESSIBILITY_LABELS["positive"])
        negative = bool(detected_labels & ACCESSIBILITY_LABELS["negative"])
        signal = "positive" if positive and not negative else "negative" if negative else "unknown"
        confidence = max((d.confidence for d in detections), default=0.0)

        return ImageDetectionResult(
            image_id=prepared_image.image_id,
            image_name=prepared_image.original_name,
            source_path=prepared_image.stored_path,
            stop_id=prepared_image.stop_id,
            detector=self.mode,
            detections=detections,
            inferred_features=inferred,
            overall_signal=signal,
            overall_confidence=confidence,
            image_width=prepared_image.width,
            image_height=prepared_image.height,
        )


def summarize_detections(results: List[ImageDetectionResult]) -> Dict[str, int]:
    """Count detected labels across many images."""
    counter: Counter[str] = Counter()
    for result in results:
        counter.update(d.label for d in result.detections)
    return dict(counter)
