"""Orchestrate the full metrology pipeline."""

from __future__ import annotations

import time
from typing import Literal

import h5py
import numpy as np

from .backend import JAX_AVAILABLE
from .deconvolution import WienerDeconvolution
from .detector import FFTDefectDetector
from .models import PipelineResult, SensorReading


class PipelineRunner:
    """Run generate → detect → result."""

    def __init__(self) -> None:
        """Initialize detector and deconvolver."""
        self._detector = FFTDefectDetector()
        self._deconvolver = WienerDeconvolution()

    def run(self, reading: SensorReading, use_wiener: bool = False) -> PipelineResult:
        """Execute the pipeline on a validated SensorReading."""
        with h5py.File(reading.hdf5_path, "r") as f:
            height_map = f["scan/height_map"][()].astype(np.float32)
        t0 = time.perf_counter()
        algorithm: Literal["fft_bandpass", "wiener_deconvolution"]
        if use_wiener:
            height_map = self._deconvolver.deconvolve(height_map)
            algorithm = "wiener_deconvolution"
        else:
            algorithm = "fft_bandpass"
        defects = self._detector.detect(height_map, reading.metadata)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return PipelineResult(
            scan=reading,
            defects=defects,
            processing_time_ms=round(elapsed_ms, 2),
            algorithm=algorithm,
            gpu_accelerated=JAX_AVAILABLE,
        )
