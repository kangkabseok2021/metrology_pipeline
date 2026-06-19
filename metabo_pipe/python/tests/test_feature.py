"""Tests for CWT peak detection, LOESS RT alignment, and feature matrix builder."""
from __future__ import annotations

import numpy as np
import pytest

from metabopipe.feature import (
    ChromatographicPeak,
    FeatureDetector,
    FeatureMatrixBuilder,
    RTAligner,
)
from metabopipe.reader import ExtractedIonChromatogram


def _gaussian_eic(n: int = 50, apex: int = 25, sigma: float = 3.0, height: float = 1e4) -> ExtractedIonChromatogram:
    rts = np.arange(n, dtype=float)
    ints = height * np.exp(-0.5 * ((rts - apex) / sigma) ** 2)
    return ExtractedIonChromatogram(mz_target=180.063, rt_array=rts, intensity_array=ints)


def test_detector_finds_single_gaussian() -> None:
    eic = _gaussian_eic(apex=25)
    peaks = FeatureDetector().find_peaks(eic)
    assert len(peaks) == 1
    assert peaks[0].rt_apex == pytest.approx(25.0, abs=2.0)


def test_detector_finds_two_separated_peaks() -> None:
    rts = np.arange(60, dtype=float)
    ints = 1e4 * np.exp(-0.5 * ((rts - 15) / 3.0) ** 2) + 1e4 * np.exp(-0.5 * ((rts - 45) / 3.0) ** 2)
    eic = ExtractedIonChromatogram(mz_target=200.0, rt_array=rts, intensity_array=ints)
    peaks = FeatureDetector().find_peaks(eic)
    assert len(peaks) == 2
    apices = sorted(p.rt_apex for p in peaks)
    assert apices[0] == pytest.approx(15.0, abs=2.0)
    assert apices[1] == pytest.approx(45.0, abs=2.0)


def test_detector_returns_empty_for_flat_signal() -> None:
    rts = np.arange(30, dtype=float)
    eic = ExtractedIonChromatogram(mz_target=100.0, rt_array=rts, intensity_array=np.zeros(30))
    assert FeatureDetector().find_peaks(eic) == []


def test_detector_peak_area_positive() -> None:
    eic = _gaussian_eic(height=5e3)
    peaks = FeatureDetector().find_peaks(eic)
    assert peaks and peaks[0].area > 0.0


def test_rt_aligner_reduces_drift() -> None:
    """After alignment, corrected RTs should be closer to the reference."""
    rts = [10, 20, 30, 40, 50]
    ref_peaks = [ChromatographicPeak(rt_apex=float(rt), mz=100.0, area=1.0, apex_intensity=1e4) for rt in rts]
    drifted = [ChromatographicPeak(rt_apex=float(rt + 2), mz=100.0, area=1.0, apex_intensity=1e4) for rt in rts]

    aligned = RTAligner().align({"ref": ref_peaks, "s1": drifted}, "ref")
    corrected_rts = [p.rt_apex for p in aligned["s1"]]
    original_errors = [abs((rt + 2) - rt) for rt in [10, 20, 30, 40, 50]]
    corrected_errors = [abs(c - r) for c, r in zip(corrected_rts, [10, 20, 30, 40, 50])]
    assert sum(corrected_errors) <= sum(original_errors)


def test_feature_matrix_shape_correct() -> None:
    peaks_s1 = [ChromatographicPeak(rt_apex=10.0, mz=180.063, area=1.0, apex_intensity=1e4)]
    peaks_s2 = [ChromatographicPeak(rt_apex=10.2, mz=180.063, area=1.0, apex_intensity=8e3)]
    sample_peaks = {"s1": peaks_s1, "s2": peaks_s2}

    samples, features, matrix = FeatureMatrixBuilder(mz_tol_ppm=10.0, rt_tol_sec=5.0).build(sample_peaks)
    assert matrix.shape == (2, 1)
    assert "s1" in samples and "s2" in samples


def test_feature_matrix_fill_value_for_missing() -> None:
    """A feature absent from one sample should get fill_value=0."""
    peaks_s1 = [ChromatographicPeak(rt_apex=10.0, mz=180.063, area=1.0, apex_intensity=5e3)]
    peaks_s2 = [ChromatographicPeak(rt_apex=50.0, mz=250.000, area=1.0, apex_intensity=3e3)]

    _, _, matrix = FeatureMatrixBuilder(mz_tol_ppm=5.0, rt_tol_sec=5.0).build(
        {"s1": peaks_s1, "s2": peaks_s2}, fill_value=0.0
    )
    assert matrix.shape == (2, 2)
    assert 0.0 in matrix.flatten()
