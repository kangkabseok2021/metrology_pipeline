"""MetaboPipe end-to-end pipeline orchestrator."""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from .annotation import FormulaPredictor, SpectralMatcher, assign_schymanski_level
from .feature import FeatureDetector, FeatureMatrixBuilder, RTAligner
from .reader import ExtractedIonChromatogram, MzmlReader


class MetaboPipeline:
    def __init__(
        self,
        mzml_files: list[Path],
        target_mzs: list[float] | None = None,
        ppm_tol: float = 10.0,
        msp_library: Path | None = None,
        output_dir: Path = Path("results"),
        r_script: Path | None = None,
        metadata_csv: Path | None = None,
    ) -> None:
        self._mzml_files = mzml_files
        self._target_mzs = target_mzs
        self._ppm_tol = ppm_tol
        self._msp_library = msp_library
        self._output_dir = output_dir
        self._r_script = r_script
        self._metadata_csv = metadata_csv

    def run(self) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Phase 1 — feature extraction
        detector = FeatureDetector()
        sample_peaks: dict[str, list] = {}

        for mzml_path in self._mzml_files:
            reader = MzmlReader(mzml_path)
            spectra = reader.read_spectra()
            peaks = []
            if self._target_mzs:
                for mz in self._target_mzs:
                    eic = ExtractedIonChromatogram.build(spectra, mz, self._ppm_tol)
                    peaks.extend(detector.find_peaks(eic))
            sample_peaks[mzml_path.stem] = peaks

        if len(sample_peaks) > 1:
            ref = next(iter(sample_peaks))
            sample_peaks = RTAligner().align(sample_peaks, ref)

        builder = FeatureMatrixBuilder(mz_tol_ppm=self._ppm_tol, rt_tol_sec=10.0)
        samples, feature_labels, matrix = builder.build(sample_peaks)

        fm_path = self._output_dir / "feature_matrix.csv"
        pd.DataFrame(matrix, index=samples, columns=feature_labels).to_csv(fm_path)

        # Phase 2 — annotation
        predictor = FormulaPredictor(ppm_tolerance=5.0)
        matcher = SpectralMatcher()
        if self._msp_library and self._msp_library.exists():
            matcher.load_msp(self._msp_library)

        annotations = []
        for label in feature_labels:
            mz = float(label.split("_")[0][2:])
            candidates = predictor.predict(mz)
            spectral_matches = matcher.match([])
            annotations.append(
                {
                    "feature": label,
                    "top_formula": candidates[0].formula if candidates else "",
                    "ppm_error": candidates[0].ppm_error if candidates else float("nan"),
                    "schymanski_level": assign_schymanski_level(candidates, spectral_matches),
                    "top_match": spectral_matches[0].compound_name if spectral_matches else "",
                }
            )

        ann_path = self._output_dir / "annotations.csv"
        pd.DataFrame(annotations).to_csv(ann_path, index=False)

        # Phase 3 — R statistics (optional, skipped if no Rscript available)
        if self._r_script and self._r_script.exists() and self._metadata_csv:
            subprocess.run(
                ["Rscript", str(self._r_script), str(fm_path), str(self._metadata_csv)],
                check=True,
                capture_output=True,
            )

        return fm_path
