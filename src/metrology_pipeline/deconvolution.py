"""Wiener deconvolution."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


class WienerDeconvolution:
    """Remove optical PSF blur using Wiener filter."""

    def __init__(self, psf_fwhm_px: float = 3.0) -> None:
        """Initialize with PSF full-width at half-maximum in pixels."""
        self._fwhm = psf_fwhm_px

    def _make_psf(self, shape: tuple[int, int]) -> npt.NDArray[np.float32]:
        """Generate a Gaussian PSF padded to the given shape."""
        sigma = self._fwhm / (2 * np.sqrt(2 * np.log(2)))
        s = min(shape[0], shape[1], 64)
        x = np.arange(s) - s // 2
        xx, yy = np.meshgrid(x, x)
        psf = np.exp(-(xx**2 + yy**2) / (2 * sigma**2)).astype(np.float32)
        psf /= psf.sum()
        full = np.zeros(shape, dtype=np.float32)
        full[: psf.shape[0], : psf.shape[1]] = psf
        return full

    def deconvolve(
        self,
        blurred: npt.NDArray[np.float32],
        noise_var: float = 0.01,
    ) -> npt.NDArray[np.float32]:
        """Apply Wiener deconvolution to blurred height map."""
        psf = self._make_psf(blurred.shape)
        h_freq = np.fft.fft2(psf)  # noqa: N806 — conventional DSP uppercase
        g_freq = np.fft.fft2(blurred)
        signal_var = float(np.var(blurred))
        k_ratio = noise_var / (signal_var + 1e-12)
        h_conj = np.conj(h_freq)
        wiener = h_conj / (np.abs(h_freq) ** 2 + k_ratio)
        result = np.real(np.fft.ifft2(g_freq * wiener)).astype(np.float32)
        return result
