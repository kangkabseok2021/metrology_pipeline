"""Sub-pixel centroid extractor using O(N) marginal-sum weighted centre-of-mass.

Formula: Cx = Σ x·I(x,y) / Σ I(x,y) via 1-D marginal sums.
Uncertainty (Cramer-Rao lower bound): σ_c = σ_PSF / SNR.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from .models import CentroidResult


class CentroidExtractor:
    """Extracts a sub-pixel centroid from a residual intensity patch."""

    MIN_WEIGHT_SUM: float = 1e-6

    def extract(
        self,
        residual: npt.NDArray[np.float32],
        bbox: tuple[int, int, int, int],
        psf_sigma: float = 1.5,
    ) -> CentroidResult | None:
        """Compute the weighted centre-of-mass centroid for a bounding box.

        Uses 1-D marginal sums for O(N) efficiency rather than the O(N²)
        direct 2-D weighted average.

        Args:
            residual: Full residual frame in ADU.
            bbox: (x0, y0, x1, y1) bounding box (pixel coordinates).
            psf_sigma: PSF sigma in pixels — used for uncertainty estimate.

        Returns:
            :class:`~leo_tracker.models.CentroidResult` or None if the blob
            has insufficient signal.
        """
        x0, y0, x1, y1 = bbox
        x0, y0 = max(0, x0), max(0, y0)
        x1 = min(residual.shape[1], x1)
        y1 = min(residual.shape[0], y1)
        if x1 <= x0 or y1 <= y0:
            return None

        patch = residual[y0:y1, x0:x1].astype(np.float64)
        # threshold at 0 to use only positive intensities
        patch_pos = np.where(patch > 0, patch, 0.0)

        weights_x = patch_pos.sum(axis=0)   # shape (width,)
        weights_y = patch_pos.sum(axis=1)   # shape (height,)
        total_weight = float(weights_x.sum())
        if total_weight < self.MIN_WEIGHT_SUM:
            return None

        cx = float(np.average(np.arange(x0, x1), weights=weights_x))
        cy = float(np.average(np.arange(y0, y1), weights=weights_y))

        area = int((x1 - x0) * (y1 - y0))
        noise = float(np.std(residual))
        peak = float(patch_pos.max())
        snr = (peak / noise) if noise > 0 else 0.0
        uncertainty = (psf_sigma / snr) if snr > 0 else psf_sigma

        return CentroidResult(
            x_px=int(round(cx)),
            y_px=int(round(cy)),
            x_sub=cx,
            y_sub=cy,
            snr=snr,
            area_px=max(1, area),
            uncertainty_px=uncertainty,
        )
