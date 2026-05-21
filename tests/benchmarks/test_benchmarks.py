"""Benchmark tests for FFTDefectDetector."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from metrology_pipeline import FFTDefectDetector, ScanMetadata


@pytest.fixture  # type: ignore[misc]
def metadata() -> ScanMetadata:
    """ScanMetadata for benchmark tests."""
    return ScanMetadata(
        wafer_id="AB000099",
        scan_timestamp=datetime.now(UTC),
        pixel_size_nm=10.0,
        scan_width_um=5.12,
        equipment_id="SIM-001",
    )


@pytest.fixture  # type: ignore[misc]
def map_512() -> np.ndarray:  # type: ignore[type-arg]
    """512x512 random float32 height map."""
    rng = np.random.default_rng(0)
    return rng.normal(0, 1, (512, 512)).astype(np.float32)


@pytest.mark.benchmark  # type: ignore[misc]
def test_fft_512(
    benchmark: pytest.fixture,  # type: ignore[type-arg]
    map_512: np.ndarray,  # type: ignore[type-arg]
    metadata: ScanMetadata,
) -> None:
    """Benchmark FFTDefectDetector.detect on a 512x512 image."""
    det = FFTDefectDetector()
    benchmark(det.detect, map_512, metadata)
