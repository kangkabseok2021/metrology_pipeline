"""FFT-based defect detector."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from .backend import jit, jnp
from .models import DefectDetection, ScanMetadata


def _fft_detect(height_map: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
    """Apply bandpass FFT filter and return magnitude image."""
    spectrum = jnp.fft.fft2(height_map)
    rows, cols = height_map.shape
    u = jnp.fft.fftfreq(rows)
    v = jnp.fft.fftfreq(cols)
    uu, vv = jnp.meshgrid(u, v, indexing="ij")
    freq = jnp.sqrt(uu**2 + vv**2)
    mask = (freq >= 0.01) & (freq <= 0.1)
    filtered = spectrum * mask
    return jnp.abs(jnp.fft.ifft2(filtered)).real  # type: ignore[return-value]


_fft_detect_jit = jit(_fft_detect)


class FFTDefectDetector:
    """Detect defects via 2-D FFT bandpass filtering."""

    def detect(
        self, height_map: npt.NDArray[np.float32], metadata: ScanMetadata
    ) -> list[DefectDetection]:
        """Detect defects and return validated DefectDetection list."""
        filtered = np.array(_fft_detect_jit(height_map), dtype=np.float32)
        mu = float(filtered.mean())
        sigma = float(filtered.std())
        threshold = mu + 3.0 * sigma
        ys, xs = np.where(filtered > threshold)
        # cluster nearby pixels — keep local maxima only
        detections: list[DefectDetection] = []
        visited = np.zeros_like(filtered, dtype=bool)
        for y, x in sorted(
            zip(ys.tolist(), xs.tolist()), key=lambda p: -filtered[p[0], p[1]]
        ):
            if visited[y, x]:
                continue
            val = float(filtered[y, x])
            confidence = min(1.0, (val - threshold) / (sigma + 1e-9))
            depth_nm = max(0.0, (val - mu) * metadata.pixel_size_nm)
            detections.append(
                DefectDetection(
                    defect_id=len(detections),
                    x_pixel=int(x),
                    y_pixel=int(y),
                    x_nm=float(x) * metadata.pixel_size_nm,
                    y_nm=float(y) * metadata.pixel_size_nm,
                    confidence=round(float(np.clip(confidence, 0, 1)), 4),
                    depth_nm=round(depth_nm, 2),
                )
            )
            # mark 5-pixel neighbourhood as visited
            y0, y1 = max(0, y - 5), min(filtered.shape[0], y + 6)
            x0, x1 = max(0, x - 5), min(filtered.shape[1], x + 6)
            visited[y0:y1, x0:x1] = True
            if len(detections) >= 200:
                break
        return detections
