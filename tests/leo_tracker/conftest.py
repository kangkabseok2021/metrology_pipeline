"""Shared fixtures for leo_tracker tests."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest

from leo_tracker.models import GeneratorConfig


@pytest.fixture()
def default_config() -> GeneratorConfig:
    """Return a small, fast GeneratorConfig for unit tests."""
    return GeneratorConfig(size=128, n_stars=5, seed=0)


@pytest.fixture()
def small_frame(default_config: GeneratorConfig) -> npt.NDArray[np.float32]:
    """Return a 128×128 synthetic frame."""
    from leo_tracker.generator import SyntheticImageGenerator

    gen = SyntheticImageGenerator()
    frame, _ = gen.generate(default_config)
    return frame


@pytest.fixture()
def gaussian_blob() -> npt.NDArray[np.float32]:
    """Return a 64×64 frame with a single Gaussian blob at (32, 32)."""
    s = 64
    cx, cy = 32.0, 32.0
    x = np.arange(s)
    y = np.arange(s)
    xx, yy = np.meshgrid(x, y)
    blob = 200.0 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 2.0**2))
    noise = np.random.default_rng(7).normal(0, 2.0, (s, s))
    return (blob + noise + 50.0).astype(np.float32)
