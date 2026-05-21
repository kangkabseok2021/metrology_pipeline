"""Tests for WienerDeconvolution: PSNR improvement after deconvolution."""

from __future__ import annotations

import numpy as np
import pytest

from metrology_pipeline.deconvolution import WienerDeconvolution


def _psnr(reference: np.ndarray, test: np.ndarray) -> float:  # type: ignore[type-arg]
    """Compute Peak Signal-to-Noise Ratio in dB."""
    mse = float(np.mean((reference.astype(np.float64) - test.astype(np.float64)) ** 2))
    if mse == 0.0:
        return float("inf")
    data_range = float(reference.max() - reference.min())
    if data_range == 0.0:
        return 0.0
    return 20.0 * np.log10(data_range / np.sqrt(mse))


@pytest.fixture(scope="module")
def sharp_image() -> np.ndarray:  # type: ignore[type-arg]
    """Synthetic sharp 128x128 test image."""
    x = np.linspace(0, 4 * np.pi, 128, dtype=np.float32)
    xx, yy = np.meshgrid(x, x)
    img = (np.sin(xx) * np.cos(yy)).astype(np.float32)
    # Add a few bright spots
    for cx, cy in [(32, 32), (64, 96), (100, 50)]:
        xi = np.arange(128)
        xxg, yyg = np.meshgrid(xi, xi)
        img += (2.0 * np.exp(-((xxg - cx) ** 2 + (yyg - cy) ** 2) / 18.0)).astype(
            np.float32
        )
    return img


def _blur_with_same_psf(
    img: np.ndarray,  # type: ignore[type-arg]
    psf_fwhm_px: float,
) -> np.ndarray:  # type: ignore[type-arg]
    """Blur *img* using the same PSF that WienerDeconvolution._make_psf() produces."""
    deconv = WienerDeconvolution(psf_fwhm_px=psf_fwhm_px)
    psf = deconv._make_psf(img.shape)
    h_freq = np.fft.fft2(psf)
    g_freq = np.fft.fft2(img)
    return np.real(np.fft.ifft2(h_freq * g_freq)).astype(np.float32)


def test_deconvolution_improves_psnr(
    sharp_image: np.ndarray,  # type: ignore[type-arg]
) -> None:
    """PSNR of deconvolved image exceeds PSNR of blurred input.

    We blur using the exact PSF model the WienerDeconvolution knows about,
    so the filter has maximum information to invert the blur.
    """
    psf_fwhm = 3.0
    blurred = _blur_with_same_psf(sharp_image, psf_fwhm)

    deconv = WienerDeconvolution(psf_fwhm_px=psf_fwhm)
    restored = deconv.deconvolve(blurred, noise_var=1e-6)

    psnr_blurred = _psnr(sharp_image, blurred)
    psnr_restored = _psnr(sharp_image, restored)

    assert psnr_restored > psnr_blurred, (
        f"Expected PSNR improvement: blurred={psnr_blurred:.2f} dB, "
        f"restored={psnr_restored:.2f} dB"
    )


def test_deconvolution_output_shape(sharp_image: np.ndarray) -> None:  # type: ignore[type-arg]
    """Deconvolution output has same shape as input."""
    blurred = _blur_with_same_psf(sharp_image, psf_fwhm_px=3.0)
    deconv = WienerDeconvolution(psf_fwhm_px=3.0)
    result = deconv.deconvolve(blurred)
    assert result.shape == blurred.shape


def test_deconvolution_output_dtype(sharp_image: np.ndarray) -> None:  # type: ignore[type-arg]
    """Deconvolution output is float32."""
    blurred = _blur_with_same_psf(sharp_image, psf_fwhm_px=3.0)
    deconv = WienerDeconvolution(psf_fwhm_px=3.0)
    result = deconv.deconvolve(blurred)
    assert result.dtype == np.float32


def test_deconvolution_finite_output(sharp_image: np.ndarray) -> None:  # type: ignore[type-arg]
    """Deconvolution output contains no NaN or Inf."""
    blurred = _blur_with_same_psf(sharp_image, psf_fwhm_px=3.0)
    deconv = WienerDeconvolution(psf_fwhm_px=3.0)
    result = deconv.deconvolve(blurred)
    assert np.all(np.isfinite(result))
