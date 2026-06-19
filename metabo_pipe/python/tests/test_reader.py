"""Tests for mzML reader and EIC builder."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from metabopipe.reader import ExtractedIonChromatogram, MzmlReader, Spectrum


def _make_spectra(n: int = 5, target_mz: float = 100.0) -> list[Spectrum]:
    return [
        Spectrum(
            rt=float(i),
            mz_array=np.array([target_mz, target_mz + 50.0]),
            intensity_array=np.array([float(i * 10), 1.0]),
        )
        for i in range(n)
    ]


def test_eic_rt_array_length(synthetic_spectra: list[Spectrum]) -> None:
    eic = ExtractedIonChromatogram.build(synthetic_spectra, 180.063, ppm_tolerance=10.0)
    assert len(eic.rt_array) == len(synthetic_spectra)


def test_eic_target_within_window() -> None:
    """Signal at exactly the target m/z should be captured."""
    spectra = _make_spectra(5, target_mz=200.0)
    eic = ExtractedIonChromatogram.build(spectra, 200.0, ppm_tolerance=10.0)
    assert np.all(eic.intensity_array[:] >= 0.0)
    assert eic.intensity_array[4] > 0.0  # scan 4 has intensity 40


def test_eic_zero_outside_ppm_window() -> None:
    """A mass 50 Da away should produce zero EIC intensities."""
    spectra = _make_spectra(5, target_mz=200.0)
    eic = ExtractedIonChromatogram.build(spectra, 201.0, ppm_tolerance=5.0)
    # 201 vs 200 = 4975 ppm — well outside 5 ppm window
    assert np.all(eic.intensity_array == 0.0)


def test_eic_mz_attribute() -> None:
    eic = ExtractedIonChromatogram.build(_make_spectra(3, 100.0), 100.0)
    assert eic.mz_target == pytest.approx(100.0)


def test_mzml_reader_returns_ms1(mzml_file: Path) -> None:
    spectra = MzmlReader(mzml_file).read_spectra()
    assert len(spectra) == 20


def test_mzml_reader_rt_monotonic(mzml_file: Path) -> None:
    spectra = MzmlReader(mzml_file).read_spectra()
    rts = [s.rt for s in spectra]
    assert all(b > a for a, b in zip(rts, rts[1:]))


def test_mzml_reader_eic_has_peak(mzml_file: Path) -> None:
    spectra = MzmlReader(mzml_file).read_spectra()
    eic = ExtractedIonChromatogram.build(spectra, 180.063, ppm_tolerance=10.0)
    # Peak should be near scan 10 (index 10) — highest intensity
    assert eic.intensity_array.argmax() == pytest.approx(10, abs=2)
