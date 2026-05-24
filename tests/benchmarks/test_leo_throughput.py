"""Throughput benchmark for process_single_frame.

Run with: pytest tests/benchmarks/test_leo_throughput.py --benchmark-json=results.json
CI gate: fails if mean throughput degrades by > 15% vs stored baseline.
"""

from __future__ import annotations

import numpy as np
import pytest

from leo_tracker.generator import SyntheticImageGenerator
from leo_tracker.models import GeneratorConfig
from leo_tracker.processing import MorphologicalDetector


@pytest.fixture(scope="module")
def synthetic_frame_512() -> np.ndarray:  # type: ignore[type-arg]
    """512×512 synthetic frame used for all benchmarks."""
    gen = SyntheticImageGenerator()
    cfg = GeneratorConfig(size=512, seed=77)
    frame, _ = gen.generate(cfg)
    return frame


@pytest.mark.benchmark(group="leo-throughput")
def test_benchmark_process_single_frame(
    benchmark: pytest.FixtureRequest,
    synthetic_frame_512: np.ndarray,  # type: ignore[type-arg]
) -> None:
    """Benchmark MorphologicalDetector.detect on a 512×512 frame.

    Baseline on 4-core CI runner: ~0.11 s/frame.
    CI fails if mean degrades by > 15% vs stored baseline.
    """
    det = MorphologicalDetector()
    result = benchmark(det.detect, synthetic_frame_512)
    assert isinstance(result, list)
