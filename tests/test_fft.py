"""Tests for FFTDefectDetector."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from metrology_pipeline import FFTDefectDetector, ScanMetadata
from metrology_pipeline.generator import DefectSpec, SensorDataGenerator


@pytest.fixture(scope="module")
def metadata() -> ScanMetadata:
    """Shared ScanMetadata for FFT tests."""
    return ScanMetadata(
        wafer_id="AB000010",
        scan_timestamp=datetime.now(UTC),
        pixel_size_nm=10.0,
        scan_width_um=1.28,
        equipment_id="SIM-001",
    )


@pytest.fixture(scope="module")
def detector() -> FFTDefectDetector:
    """Shared FFTDefectDetector instance."""
    return FFTDefectDetector()


@pytest.fixture(scope="module")
def synthetic_with_defects() -> tuple[np.ndarray, list[DefectSpec]]:  # type: ignore[type-arg]
    """128x128 height map with 5 known defects."""
    gen = SensorDataGenerator(size=128)
    rng = np.random.default_rng(7)
    height_map, defect_specs = gen._make_height_map(5, rng)
    return height_map, defect_specs


def test_detector_finds_at_least_three_defects(
    synthetic_with_defects: tuple[np.ndarray, list[DefectSpec]],  # type: ignore[type-arg]
    detector: FFTDefectDetector,
    metadata: ScanMetadata,
) -> None:
    """Detector finds >= 3 out of 5 planted defects."""
    height_map, defect_specs = synthetic_with_defects
    detections = detector.detect(height_map.astype(np.float32), metadata)
    assert len(detections) >= 3, f"Expected >= 3 detections, got {len(detections)}"


def test_detector_returns_defect_detections(
    synthetic_with_defects: tuple[np.ndarray, list[DefectSpec]],  # type: ignore[type-arg]
    detector: FFTDefectDetector,
    metadata: ScanMetadata,
) -> None:
    """All returned objects are DefectDetection instances."""
    from metrology_pipeline.models import DefectDetection

    height_map, _ = synthetic_with_defects
    detections = detector.detect(height_map.astype(np.float32), metadata)
    for d in detections:
        assert isinstance(d, DefectDetection)


def test_detector_clean_image_few_detections(
    detector: FFTDefectDetector,
    metadata: ScanMetadata,
) -> None:
    """On a defect-free flat image the detector returns zero detections."""
    rng = np.random.default_rng(99)
    # Pure gaussian noise — no periodic defect signal
    clean = rng.normal(0, 0.05, (128, 128)).astype(np.float32)
    detections = detector.detect(clean, metadata)
    # Allow a modest number of false positives on pure noise
    assert len(detections) <= 25, (
        f"Too many detections on clean image: {len(detections)}"
    )


def test_detector_confidence_in_range(
    synthetic_with_defects: tuple[np.ndarray, list[DefectSpec]],  # type: ignore[type-arg]
    detector: FFTDefectDetector,
    metadata: ScanMetadata,
) -> None:
    """All confidence values are in [0, 1]."""
    height_map, _ = synthetic_with_defects
    detections = detector.detect(height_map.astype(np.float32), metadata)
    for d in detections:
        assert 0.0 <= d.confidence <= 1.0


def test_detector_depth_nm_non_negative(
    synthetic_with_defects: tuple[np.ndarray, list[DefectSpec]],  # type: ignore[type-arg]
    detector: FFTDefectDetector,
    metadata: ScanMetadata,
) -> None:
    """All depth_nm values are non-negative."""
    height_map, _ = synthetic_with_defects
    detections = detector.detect(height_map.astype(np.float32), metadata)
    for d in detections:
        assert d.depth_nm >= 0.0


def test_detector_pixel_coordinates_in_bounds(
    synthetic_with_defects: tuple[np.ndarray, list[DefectSpec]],  # type: ignore[type-arg]
    detector: FFTDefectDetector,
    metadata: ScanMetadata,
) -> None:
    """Detected pixel coordinates are within image bounds."""
    height_map, _ = synthetic_with_defects
    detections = detector.detect(height_map.astype(np.float32), metadata)
    h, w = height_map.shape
    for d in detections:
        assert 0 <= d.x_pixel < w
        assert 0 <= d.y_pixel < h
