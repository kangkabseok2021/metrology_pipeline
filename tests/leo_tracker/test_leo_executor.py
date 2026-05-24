"""Tests for BatchProcessor (ProcessPoolExecutor parallel frame processing)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from leo_tracker.executor import BatchProcessor
from leo_tracker.generator import SyntheticImageGenerator
from leo_tracker.models import GeneratorConfig


def _save_frames(n: int, tmpdir: Path, size: int = 64) -> list[Path]:
    """Generate and save *n* synthetic frames, return paths."""
    gen = SyntheticImageGenerator()
    paths = []
    for i in range(n):
        cfg = GeneratorConfig(size=size, seed=i + 20)
        frame, _ = gen.generate(cfg)
        p = tmpdir / f"frame_{i:04d}.npy"
        np.save(p, frame)
        paths.append(p)
    return paths


def test_batch_four_frames_max_workers_two() -> None:
    """4 frames processed with max_workers=2 must return exactly 4 results."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = _save_frames(4, Path(tmp))
        proc = BatchProcessor()
        result = proc.run(paths, max_workers=2)
        assert result.success_count == 4
        assert result.failure_count == 0
        assert len(result.results) == 4


def test_failed_frame_counted_in_failure_count() -> None:
    """A non-existent path must be counted in failure_count, not crash."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = _save_frames(2, Path(tmp))
        paths.append(Path(tmp) / "nonexistent.npy")
        proc = BatchProcessor()
        result = proc.run(paths, max_workers=1)
        assert result.success_count == 2
        assert result.failure_count == 1
        assert len(result.failed_frames) == 1


def test_results_contain_tracking_results() -> None:
    """Each result in BatchResult.results must be a valid TrackingResult."""
    from leo_tracker.models import TrackingResult

    with tempfile.TemporaryDirectory() as tmp:
        paths = _save_frames(3, Path(tmp))
        proc = BatchProcessor()
        result = proc.run(paths, max_workers=1)
        for r in result.results:
            assert isinstance(r, TrackingResult)
            assert r.processing_time_ms > 0.0


def test_empty_frame_list_returns_empty_result() -> None:
    """Empty input must return a BatchResult with zero successes."""
    proc = BatchProcessor()
    result = proc.run([], max_workers=1)
    assert result.success_count == 0
    assert result.failure_count == 0
    assert result.results == []
