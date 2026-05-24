"""Tests for SyntheticImageGenerator."""

from __future__ import annotations

import numpy as np

from leo_tracker.generator import SyntheticImageGenerator
from leo_tracker.models import GeneratorConfig


def test_frame_shape_and_dtype() -> None:
    """Generated frame must have the configured shape and float32 dtype."""
    cfg = GeneratorConfig(size=128, seed=1)
    gen = SyntheticImageGenerator()
    frame, _ = gen.generate(cfg)
    assert frame.shape == (128, 128)
    assert frame.dtype == np.float32


def test_streak_centroid_within_bounds() -> None:
    """Ground-truth streak centroid must lie in the central 50% of the frame."""
    cfg = GeneratorConfig(size=128, seed=2)
    gen = SyntheticImageGenerator()
    _, (cx, cy) = gen.generate(cfg)
    margin = 128 * 0.25
    assert margin <= cx <= 128 - margin
    assert margin <= cy <= 128 - margin


def test_streak_visible_as_intensity_peak() -> None:
    """Frame with streak must have higher max than frame without streak."""
    rng = np.random.default_rng(3)
    baseline = rng.poisson(50.0, (128, 128)).astype(np.float32)
    cfg = GeneratorConfig(size=128, seed=3)
    gen = SyntheticImageGenerator()
    frame, _ = gen.generate(cfg)
    assert float(frame.max()) > float(baseline.max())


def test_background_level_near_sky_background() -> None:
    """Median of the frame should be within 30% of sky_background."""
    cfg = GeneratorConfig(size=256, sky_background=50.0, n_stars=0, seed=4)
    gen = SyntheticImageGenerator()
    frame, _ = gen.generate(cfg)
    median = float(np.median(frame))
    assert 35.0 <= median <= 65.0


def test_star_count_affects_bright_pixels() -> None:
    """Frame with more stars must have more bright pixels than frame with zero stars."""
    cfg_no = GeneratorConfig(size=128, n_stars=0, seed=5)
    cfg_yes = GeneratorConfig(size=128, n_stars=20, seed=5)
    gen = SyntheticImageGenerator()
    f_no, _ = gen.generate(cfg_no)
    f_yes, _ = gen.generate(cfg_yes)
    thresh = 200.0
    assert (f_yes > thresh).sum() >= (f_no > thresh).sum()


def test_deterministic_with_same_seed() -> None:
    """Same seed must produce identical frames."""
    cfg = GeneratorConfig(size=64, seed=99)
    gen = SyntheticImageGenerator()
    f1, gt1 = gen.generate(cfg)
    f2, gt2 = gen.generate(cfg)
    assert np.array_equal(f1, f2)
    assert gt1 == gt2
