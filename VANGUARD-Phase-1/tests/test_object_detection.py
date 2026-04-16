"""Tests for image preprocessing and accessibility object detection."""

import tempfile
from pathlib import Path

from PIL import Image

from src.image_processor import ImageProcessor
from src.object_detection import AccessibilityObjectDetector


def _create_test_image(path: Path, color=(180, 180, 180)):
    image = Image.new("RGB", (640, 480), color=color)
    image.save(path)


def test_image_processor_prepares_image_bytes():
    temp_dir = Path(tempfile.mkdtemp())
    image_path = temp_dir / "STOP_001_ramp.jpg"
    _create_test_image(image_path)

    processor = ImageProcessor()
    prepared = processor.prepare_bytes(
        file_name=image_path.name,
        content=image_path.read_bytes(),
        destination_dir=temp_dir / "prepared",
        stop_id="STOP_001",
    )

    assert prepared.stop_id == "STOP_001"
    assert prepared.width <= 1280
    assert prepared.height <= 1280
    assert Path(prepared.stored_path).exists()


def test_detector_uses_demo_fallback_for_keywords():
    temp_dir = Path(tempfile.mkdtemp())
    image_path = temp_dir / "STOP_002_ramp_and_light.jpg"
    _create_test_image(image_path)

    processor = ImageProcessor()
    prepared = processor.prepare_bytes(
        file_name=image_path.name,
        content=image_path.read_bytes(),
        destination_dir=temp_dir / "prepared",
        stop_id="STOP_002",
    )

    detector = AccessibilityObjectDetector(model_path=None, detector_mode="demo")
    result = detector.predict(prepared)

    labels = [d.label for d in result.detections]
    assert result.detector == "demo_fallback"
    assert "ramp" in labels or "low_floor_bus" in labels
    assert result.stop_id == "STOP_002"
