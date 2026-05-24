"""End-to-end tests for PipelineOrchestrator."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from leo_tracker.generator import SyntheticImageGenerator
from leo_tracker.models import GeneratorConfig, TrackingResult
from leo_tracker.pipeline import JsonFrameWriter, NpyFrameLoader, PipelineOrchestrator
from leo_tracker.processing import FFTDetector, MorphologicalDetector


def _save_frames(n: int, tmpdir: Path, size: int = 128) -> list[Path]:
    """Generate and save *n* synthetic frames, return paths."""
    gen = SyntheticImageGenerator()
    paths = []
    for i in range(n):
        cfg = GeneratorConfig(size=size, seed=i + 10)
        frame, _ = gen.generate(cfg)
        p = tmpdir / f"frame_{i:04d}.npy"
        np.save(p, frame)
        paths.append(p)
    return paths


def test_single_frame_returns_tracking_result() -> None:
    """process_frame must return a valid TrackingResult."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = _save_frames(1, Path(tmp))
        orch = PipelineOrchestrator()
        result = orch.process_frame(paths[0], frame_id=0)
        assert isinstance(result, TrackingResult)
        assert result.frame_id == 0
        assert result.processing_time_ms > 0.0


def test_batch_of_five_frames_all_processed() -> None:
    """process_batch on 5 frames must return 5 results."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = _save_frames(5, Path(tmp))
        orch = PipelineOrchestrator()
        results = orch.process_batch(paths)
        assert len(results) == 5
        for r in results:
            assert r.processing_time_ms > 0.0


def test_detector_is_swappable() -> None:
    """PipelineOrchestrator must accept any AbstractDetector subclass."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = _save_frames(1, Path(tmp))
        orch_morph = PipelineOrchestrator(detector=MorphologicalDetector())
        orch_fft = PipelineOrchestrator(detector=FFTDetector())
        r_morph = orch_morph.process_frame(paths[0])
        r_fft = orch_fft.process_frame(paths[0])
        assert isinstance(r_morph, TrackingResult)
        assert isinstance(r_fft, TrackingResult)


def test_json_writer_produces_valid_json() -> None:
    """process_batch with JsonFrameWriter must write parseable JSON."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        paths = _save_frames(3, tmp_path)
        output = tmp_path / "results.json"
        orch = PipelineOrchestrator()
        writer = JsonFrameWriter()
        orch.process_batch(paths, writer=writer, output_path=output)
        assert output.exists()
        data = json.loads(output.read_text())
        assert isinstance(data, list)
        assert len(data) == 3


def test_batch_skips_bad_frame_gracefully() -> None:
    """process_batch must skip a malformed frame and continue."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good_paths = _save_frames(2, tmp_path)
        # inject a 3-D frame that will raise InvalidFrameError
        bad = tmp_path / "bad.npy"
        np.save(bad, np.zeros((4, 4, 3), dtype=np.float32))
        all_paths = good_paths + [bad]
        orch = PipelineOrchestrator()
        results = orch.process_batch(all_paths)
        # only 2 good frames succeed
        assert len(results) == 2
