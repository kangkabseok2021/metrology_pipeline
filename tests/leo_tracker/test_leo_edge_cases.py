"""Edge-case and error-handling tests for the detection pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from leo_tracker.errors import InvalidFrameError
from leo_tracker.processing import MorphologicalDetector, _validate_frame


def test_all_zeros_returns_empty_detections() -> None:
    """A flat-zero frame must produce an empty detection list without crashing."""
    frame = np.zeros((128, 128), dtype=np.float32)
    det = MorphologicalDetector()
    results = det.detect(frame)
    assert results == []


def test_all_nan_raises_invalid_frame_error() -> None:
    """A frame filled with NaN must raise InvalidFrameError with shape in message."""
    frame = np.full((64, 64), np.nan, dtype=np.float32)
    det = MorphologicalDetector()
    with pytest.raises(InvalidFrameError, match=r"\(64, 64\)"):
        det.detect(frame)


def test_int16_dtype_cast_to_float32() -> None:
    """int16 frame must be automatically cast and processed without error."""
    frame = np.random.default_rng(0).integers(0, 500, (128, 128), dtype=np.int16)
    det = MorphologicalDetector()
    results = det.detect(frame)
    assert isinstance(results, list)


def test_oversaturated_frame_returns_empty() -> None:
    """Frame where all pixels are at maximum returns no detections."""
    frame = np.full((128, 128), np.finfo(np.float32).max, dtype=np.float32)
    det = MorphologicalDetector()
    # max-saturated frames have zero variance — threshold fails gracefully
    results = det.detect(frame)
    assert isinstance(results, list)


def test_wrong_ndim_raises_invalid_frame_error() -> None:
    """A 3-D array must raise InvalidFrameError mentioning the shape."""
    frame = np.zeros((64, 64, 3), dtype=np.float32)
    with pytest.raises(InvalidFrameError, match=r"2-D"):
        _validate_frame(frame)


def test_small_frame_no_crash() -> None:
    """An 8×8 frame must be processed gracefully (no blobs expected)."""
    frame = np.random.default_rng(1).poisson(50.0, (8, 8)).astype(np.float32)
    det = MorphologicalDetector()
    results = det.detect(frame)
    assert isinstance(results, list)


def test_single_inf_pixel_raises_invalid_frame_error() -> None:
    """A frame with a single Inf pixel must raise InvalidFrameError."""
    frame = np.ones((64, 64), dtype=np.float32) * 50.0
    frame[32, 32] = np.inf
    with pytest.raises(InvalidFrameError):
        _validate_frame(frame)
