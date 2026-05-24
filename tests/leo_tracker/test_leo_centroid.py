"""Tests for CentroidExtractor — sub-pixel accuracy and SNR computation."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from leo_tracker.centroid import CentroidExtractor


def _gaussian_patch(
    cx: float, cy: float, sigma: float = 2.0, size: int = 64, intensity: float = 200.0
) -> npt.NDArray[np.float32]:
    """Create a frame with a single Gaussian blob at (cx, cy)."""
    x = np.arange(size)
    y = np.arange(size)
    xx, yy = np.meshgrid(x, y)
    blob = intensity * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma**2))
    return blob.astype(np.float32)


def test_centroid_accuracy_integer_position() -> None:
    """Centroid of a Gaussian at an integer position must be recovered to < 0.1 px."""
    cx, cy = 32.0, 32.0
    frame = _gaussian_patch(cx, cy)
    extractor = CentroidExtractor()
    result = extractor.extract(frame, (20, 20, 44, 44))
    assert result is not None
    assert abs(result.x_sub - cx) < 0.1
    assert abs(result.y_sub - cy) < 0.1


def test_centroid_accuracy_subpixel_position() -> None:
    """Centroid of a Gaussian at a non-integer position must be within 0.15 px."""
    cx, cy = 32.7, 31.4
    frame = _gaussian_patch(cx, cy)
    extractor = CentroidExtractor()
    result = extractor.extract(frame, (20, 18, 46, 46))
    assert result is not None
    assert abs(result.x_sub - cx) < 0.15
    assert abs(result.y_sub - cy) < 0.15


def test_snr_positive_for_bright_source() -> None:
    """SNR must be positive for a blob well above the background."""
    frame = _gaussian_patch(32.0, 32.0, intensity=300.0)
    extractor = CentroidExtractor()
    result = extractor.extract(frame, (20, 20, 44, 44))
    assert result is not None
    assert result.snr > 0.0


def test_uncertainty_decreases_with_snr() -> None:
    """Higher intensity blob must produce smaller uncertainty_px."""
    extractor = CentroidExtractor()
    r_bright = extractor.extract(
        _gaussian_patch(32.0, 32.0, intensity=500.0), (20, 20, 44, 44)
    )
    r_faint = extractor.extract(
        _gaussian_patch(32.0, 32.0, intensity=50.0), (20, 20, 44, 44)
    )
    assert r_bright is not None and r_faint is not None
    assert r_bright.uncertainty_px < r_faint.uncertainty_px


def test_area_matches_bbox() -> None:
    """area_px must equal bounding-box width × height."""
    frame = _gaussian_patch(32.0, 32.0)
    extractor = CentroidExtractor()
    result = extractor.extract(frame, (20, 20, 44, 44))
    assert result is not None
    assert result.area_px == 24 * 24


def test_returns_none_on_zero_weight_patch() -> None:
    """All-zero patch must return None (no signal to centroid)."""
    frame = np.zeros((64, 64), dtype=np.float32)
    extractor = CentroidExtractor()
    result = extractor.extract(frame, (10, 10, 20, 20))
    assert result is None
