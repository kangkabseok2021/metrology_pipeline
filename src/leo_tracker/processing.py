"""Background subtraction and OpenCV morphological detection chain.

All OpenCV calls are encapsulated in :class:`ImageProcessor` — this is the
single import boundary for cv2, making the backend swappable.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import numpy.typing as npt
import scipy.ndimage

from .centroid import CentroidExtractor
from .errors import InvalidFrameError
from .interfaces import AbstractDetector
from .models import CentroidResult


def _validate_frame(frame: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
    """Validate and normalise a sensor frame to float32.

    Args:
        frame: Input array of any numeric dtype.

    Returns:
        float32 copy of *frame*.

    Raises:
        InvalidFrameError: If frame has wrong ndim, contains non-finite values,
            or cannot be cast to float32.
    """
    if frame.ndim != 2:
        raise InvalidFrameError(f"Expected 2-D frame, got shape {frame.shape}")
    try:
        out = frame.astype(np.float32)
    except (TypeError, ValueError) as exc:
        raise InvalidFrameError(
            f"Cannot cast frame dtype {frame.dtype} to float32"
        ) from exc
    if not np.isfinite(out).all():
        raise InvalidFrameError(
            f"Frame contains non-finite values (NaN/Inf) — shape {frame.shape}"
        )
    return out


class BackgroundSubtractor:
    """Estimates and subtracts sigma-clipped median background."""

    FILTER_SIZE: int = 31
    SIGMA_CLIP: float = 3.0
    TOPHAT_SIZE: int = 7

    def subtract(
        self, frame: npt.NDArray[np.float32]
    ) -> tuple[npt.NDArray[np.float32], float]:
        """Apply sigma-clipped median background subtraction.

        Args:
            frame: Validated float32 sensor frame in ADU.

        Returns:
            Tuple of (residual_frame, background_level_adu) where
            residual = frame - background after top-hat enhancement.
        """
        background = scipy.ndimage.median_filter(frame, size=self.FILTER_SIZE).astype(
            np.float32
        )
        residual = frame - background
        bg_level = float(np.median(background))
        # morphological top-hat removes extended gradients, enhances compact sources
        tophat = scipy.ndimage.white_tophat(residual, size=self.TOPHAT_SIZE).astype(
            np.float32
        )
        return tophat, bg_level


class ImageProcessor:
    """Wraps all OpenCV calls — the single cv2 import boundary.

    Replacing this class with a different backend (e.g. scikit-image)
    requires no changes outside this module.
    """

    def blur(
        self, frame: npt.NDArray[np.float32], sigma: float = 0.8
    ) -> npt.NDArray[np.float32]:
        """Apply Gaussian blur for hot-pixel / cosmic-ray rejection.

        Args:
            frame: Input float32 frame.
            sigma: Gaussian blur sigma in pixels.

        Returns:
            Blurred float32 frame.
        """
        import cv2  # noqa: PLC0415

        return cv2.GaussianBlur(frame, (0, 0), sigma).astype(np.float32)

    def threshold_and_label(
        self, residual: npt.NDArray[np.float32]
    ) -> tuple[npt.NDArray[np.int32], int, npt.NDArray[np.int32]]:
        """Threshold residual and label connected components.

        Args:
            residual: Top-hat enhanced residual frame.

        Returns:
            Tuple of (labels, n_labels, stats) compatible with
            cv2.connectedComponentsWithStats output.
            stats shape: (n_labels, 5) — [x, y, w, h, area].
        """
        import cv2  # noqa: PLC0415

        median = float(np.median(residual))
        mad = float(np.median(np.abs(residual - median)))
        thresh_val = median + 5.0 * mad
        _, binary = cv2.threshold(residual, thresh_val, 255.0, cv2.THRESH_BINARY)
        binary_u8 = binary.astype(np.uint8)
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        opened = cv2.morphologyEx(binary_u8, cv2.MORPH_OPEN, kernel)
        n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(opened)
        return (
            cast(npt.NDArray[np.int32], np.asarray(labels, dtype=np.int32)),
            int(n_labels),
            cast(npt.NDArray[np.int32], np.asarray(stats, dtype=np.int32)),
        )

    def fit_ellipse_angle(
        self,
        frame: npt.NDArray[np.float32],
        label_map: npt.NDArray[np.int32],
        label_idx: int,
    ) -> float | None:
        """Fit an ellipse to a blob and return its major-axis angle in degrees.

        Args:
            frame: Original frame (unused but kept for API consistency).
            label_map: Connected-component label map.
            label_idx: Label index of the blob to fit.

        Returns:
            Major-axis angle in degrees, or None if fitting fails.
        """
        import cv2  # noqa: PLC0415

        mask = (label_map == label_idx).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours or len(contours[0]) < 5:
            return None
        _, _, angle = cv2.fitEllipse(contours[0])
        return float(angle)


class MorphologicalDetector(AbstractDetector):
    """Concrete detector: Gaussian blur → top-hat BG sub → threshold → centroid.

    This is the default production detector. Swappable via
    :class:`~leo_tracker.interfaces.AbstractDetector`.
    """

    MIN_AREA_PX: int = 3
    MAX_AREA_PX: int = 500
    PSF_SIGMA: float = 1.5

    def __init__(self) -> None:
        """Initialise with default background subtractor and image processor."""
        self._bg = BackgroundSubtractor()
        self._img = ImageProcessor()
        self._cx = CentroidExtractor()

    def detect(self, frame: npt.NDArray[np.float32]) -> list[CentroidResult]:
        """Detect objects via morphological pipeline.

        Args:
            frame: Validated float32 sensor frame.

        Returns:
            List of :class:`~leo_tracker.models.CentroidResult` objects.

        Raises:
            InvalidFrameError: Propagated from frame validation.
            DetectionError: Wraps any unexpected backend exception.
        """
        from .errors import DetectionError  # noqa: PLC0415

        try:
            f = _validate_frame(frame)
            blurred = self._img.blur(f)
            residual, _ = self._bg.subtract(blurred)
            labels, n_labels, stats = self._img.threshold_and_label(residual)
            results: list[CentroidResult] = []
            for i in range(1, n_labels):  # 0 is background
                area = int(stats[i, 4])
                if area < self.MIN_AREA_PX or area > self.MAX_AREA_PX:
                    continue
                x0 = int(stats[i, 0])
                y0 = int(stats[i, 1])
                w = int(stats[i, 2])
                h = int(stats[i, 3])
                x1, y1 = x0 + w, y0 + h
                result = self._cx.extract(residual, (x0, y0, x1, y1), self.PSF_SIGMA)
                if result is not None:
                    results.append(result)
        except InvalidFrameError:
            raise
        except Exception as exc:
            raise DetectionError(f"Detection backend failure: {exc}") from exc
        return results


class FFTDetector(AbstractDetector):
    """Alternate detector: FFT bandpass filter for periodic background patterns."""

    def __init__(self, low_cutoff: float = 0.05, high_cutoff: float = 0.4) -> None:
        """Initialise FFT detector with bandpass parameters.

        Args:
            low_cutoff: Normalised low spatial-frequency cutoff [0, 0.5].
            high_cutoff: Normalised high spatial-frequency cutoff [0, 0.5].
        """
        self._low = low_cutoff
        self._high = high_cutoff
        self._cx = CentroidExtractor()

    def detect(self, frame: npt.NDArray[np.float32]) -> list[CentroidResult]:
        """Detect objects via FFT bandpass filter.

        Args:
            frame: Validated float32 sensor frame.

        Returns:
            List of :class:`~leo_tracker.models.CentroidResult` objects.
        """
        f = _validate_frame(frame)
        spectrum = np.fft.fft2(f)
        shifted = np.fft.fftshift(spectrum)
        rows, cols = f.shape
        cr, cc = rows // 2, cols // 2
        y_idx = np.arange(rows)
        x_idx = np.arange(cols)
        xx, yy = np.meshgrid(x_idx, y_idx)
        dist = np.sqrt(((xx - cc) / cols) ** 2 + ((yy - cr) / rows) ** 2)
        mask = (dist >= self._low) & (dist <= self._high)
        shifted *= mask
        filtered = np.abs(np.fft.ifft2(np.fft.ifftshift(shifted))).astype(np.float32)
        median = float(np.median(filtered))
        mad = float(np.median(np.abs(filtered - median)))
        thresh = median + 5.0 * mad
        binary = (filtered > thresh).astype(np.uint8)
        labeled, n = scipy.ndimage.label(binary)
        results: list[CentroidResult] = []
        for i in range(1, n + 1):
            coords = np.argwhere(labeled == i)
            if len(coords) < 3 or len(coords) > 500:
                continue
            y0, x0 = coords.min(axis=0)
            y1, x1 = coords.max(axis=0) + 1
            result = self._cx.extract(
                filtered, (int(x0), int(y0), int(x1), int(y1)), 1.5
            )
            if result is not None:
                results.append(result)
        return results
