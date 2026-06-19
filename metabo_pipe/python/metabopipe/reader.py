"""LC-MS mzML parser and extracted-ion chromatogram builder."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pyteomics import mzml


@dataclass
class Spectrum:
    rt: float  # seconds
    mz_array: np.ndarray
    intensity_array: np.ndarray


@dataclass
class ExtractedIonChromatogram:
    mz_target: float
    rt_array: np.ndarray
    intensity_array: np.ndarray

    @classmethod
    def build(
        cls,
        spectra: list[Spectrum],
        mz: float,
        ppm_tolerance: float = 10.0,
    ) -> ExtractedIonChromatogram:
        rts: list[float] = []
        intensities: list[float] = []
        for s in spectra:
            ppm_delta = np.abs(s.mz_array - mz) / mz * 1e6
            mask = ppm_delta <= ppm_tolerance
            intensities.append(float(s.intensity_array[mask].sum()) if mask.any() else 0.0)
            rts.append(s.rt)
        return cls(mz, np.array(rts, dtype=float), np.array(intensities, dtype=float))


class MzmlReader:
    """Stream MS1 spectra from an mzML file without loading everything into memory."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def read_spectra(self) -> list[Spectrum]:
        spectra: list[Spectrum] = []
        with mzml.MzML(str(self._path)) as reader:
            for spec in reader:
                if spec.get("ms level") != 1:
                    continue
                scan = spec["scanList"]["scan"][0]
                rt_raw = scan.get("scan start time", 0.0)
                # pyteomics may return a unitfloat; convert explicitly
                rt_min = float(rt_raw)
                rt_sec = rt_min * 60.0
                spectra.append(
                    Spectrum(
                        rt=rt_sec,
                        mz_array=np.asarray(spec["m/z array"], dtype=float),
                        intensity_array=np.asarray(spec["intensity array"], dtype=float),
                    )
                )
        return spectra
