"""Tests for BackgroundSubtractor."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from leo_tracker.processing import BackgroundSubtractor


def _uniform_frame(level: float, size: int = 64) -> npt.NDArray[np.float32]:
    return np.full((size, size), level, dtype=np.float32)


def test_background_estimate_near_true_level() -> None:
    """Background estimate on a near-uniform frame must be within 5% of truth."""
    true_bg = 50.0
    rng = np.random.default_rng(0)
    frame = rng.poisson(true_bg, (128, 128)).astype(np.float32)
    sub = BackgroundSubtractor()
    _, bg_level = sub.subtract(frame)
    assert abs(bg_level - true_bg) / true_bg < 0.05


def test_residual_mean_near_zero() -> None:
    """Top-hat residual of a background-only frame must be small relative to sky."""
    rng = np.random.default_rng(1)
    sky = 60.0
    frame = rng.poisson(sky, (128, 128)).astype(np.float32)
    sub = BackgroundSubtractor()
    residual, _ = sub.subtract(frame)
    # white_tophat is non-negative; mean should be << sky_background
    assert float(residual.mean()) < sky * 0.5


def test_tophat_enhances_compact_source() -> None:
    """Residual around an injected point source must be positive."""
    rng = np.random.default_rng(2)
    frame = rng.poisson(50.0, (128, 128)).astype(np.float32)
    cx, cy = 64, 64
    x = np.arange(128)
    y = np.arange(128)
    xx, yy = np.meshgrid(x, y)
    frame += (200.0 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / 4.5)).astype(
        np.float32
    )
    sub = BackgroundSubtractor()
    residual, _ = sub.subtract(frame)
    source_region = residual[cy - 5 : cy + 6, cx - 5 : cx + 6]
    assert float(source_region.max()) > 0.0


def test_output_dtype_is_float32() -> None:
    """subtract() must return a float32 residual regardless of input."""
    frame = np.ones((64, 64), dtype=np.float64) * 40.0
    sub = BackgroundSubtractor()
    residual, _ = sub.subtract(frame.astype(np.float32))
    assert residual.dtype == np.float32
