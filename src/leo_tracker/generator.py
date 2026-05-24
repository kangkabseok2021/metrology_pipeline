"""Synthetic LEO sensor-frame generator.

Produces 2-D float32 frames containing:
- Poisson-distributed background sky noise
- Fixed stars with 2-D Gaussian PSF
- A single moving satellite streak with Gaussian cross-section

Ground-truth sub-pixel centroid of the streak mid-point is returned
alongside the frame for validation.
"""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

from .models import GeneratorConfig


class SyntheticImageGenerator:
    """Generates synthetic satellite sensor frames for pipeline validation."""

    PSF_SIGMA: float = 1.5  # diffraction-limited PSF at 500 nm
    STAR_INTENSITY: float = 150.0  # ADU per star peak

    def generate(
        self, config: GeneratorConfig
    ) -> tuple[npt.NDArray[np.float32], tuple[float, float]]:
        """Generate a synthetic frame and return it with the ground-truth centroid.

        Args:
            config: Frozen generator configuration.

        Returns:
            Tuple of (frame, (gt_cx, gt_cy)) where gt_cx/gt_cy are the
            sub-pixel streak centroid coordinates.
        """
        rng = np.random.default_rng(config.seed)
        s = config.size
        frame = rng.poisson(config.sky_background, (s, s)).astype(np.float32)
        self._add_stars(frame, config, rng)
        gt_cx, gt_cy = self._add_streak(frame, config, rng)
        return frame, (gt_cx, gt_cy)

    def _add_stars(
        self,
        frame: npt.NDArray[np.float32],
        config: GeneratorConfig,
        rng: np.random.Generator,
    ) -> None:
        """Place Gaussian PSF stars at random positions."""
        s = config.size
        margin = 10
        xs = rng.integers(margin, s - margin, config.n_stars)
        ys = rng.integers(margin, s - margin, config.n_stars)
        r = int(math.ceil(4 * self.PSF_SIGMA))
        xi = np.arange(s)
        yi = np.arange(s)
        xx, yy = np.meshgrid(xi, yi)
        for cx, cy in zip(xs, ys):
            x0, x1 = max(0, cx - r), min(s, cx + r + 1)
            y0, y1 = max(0, cy - r), min(s, cy + r + 1)
            patch_xx = xx[y0:y1, x0:x1]
            patch_yy = yy[y0:y1, x0:x1]
            blob = self.STAR_INTENSITY * np.exp(
                -((patch_xx - cx) ** 2 + (patch_yy - cy) ** 2)
                / (2 * self.PSF_SIGMA**2)
            )
            frame[y0:y1, x0:x1] += blob.astype(np.float32)

    def _add_streak(
        self,
        frame: npt.NDArray[np.float32],
        config: GeneratorConfig,
        rng: np.random.Generator,
    ) -> tuple[float, float]:
        """Add a satellite streak and return its sub-pixel centroid."""
        s = config.size
        length = int(rng.integers(config.streak_length_min, config.streak_length_max + 1))
        angle = float(rng.uniform(0.0, 2 * math.pi))
        cx = float(rng.uniform(s * 0.25, s * 0.75))
        cy = float(rng.uniform(s * 0.25, s * 0.75))
        dx = math.cos(angle)
        dy = math.sin(angle)
        half = length / 2.0
        r = int(math.ceil(4 * config.streak_sigma))
        xi = np.arange(s)
        yi = np.arange(s)
        xx, yy = np.meshgrid(xi, yi)
        n_samples = max(length * 2, 50)
        for t in np.linspace(-half, half, n_samples):
            sx = cx + t * dx
            sy = cy + t * dy
            ix, iy = int(round(sx)), int(round(sy))
            x0, x1 = max(0, ix - r), min(s, ix + r + 1)
            y0, y1 = max(0, iy - r), min(s, iy + r + 1)
            if x0 >= x1 or y0 >= y1:
                continue
            patch_xx = xx[y0:y1, x0:x1]
            patch_yy = yy[y0:y1, x0:x1]
            contrib = config.streak_intensity / n_samples * np.exp(
                -((patch_xx - sx) ** 2 + (patch_yy - sy) ** 2)
                / (2 * config.streak_sigma**2)
            )
            frame[y0:y1, x0:x1] += contrib.astype(np.float32)
        return cx, cy
