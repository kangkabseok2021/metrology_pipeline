"""Parallel frame processor using ProcessPoolExecutor for GIL bypass.

The top-level function :func:`process_single_frame` must remain at module level
so that it is picklable across process boundaries.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ProcessPoolExecutor, TimeoutError, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from .errors import DetectionError, InvalidFrameError
from .models import TrackingResult
from .processing import MorphologicalDetector

_FRAME_TIMEOUT_S: float = 30.0


def process_single_frame(
    frame_path: Path,
    frame_id: int,
    psf_sigma: float = 1.5,
) -> TrackingResult:
    """Process a single frame file and return a TrackingResult.

    Module-level function (not a method) so it is picklable for
    :class:`concurrent.futures.ProcessPoolExecutor`.

    Args:
        frame_path: Path to a .npy float32 sensor frame.
        frame_id: Identifier for this frame in the batch.
        psf_sigma: PSF sigma passed to the centroid extractor.

    Returns:
        :class:`~leo_tracker.models.TrackingResult`.

    Raises:
        InvalidFrameError: For malformed frames.
        DetectionError: For unexpected backend errors.
    """
    t0 = time.perf_counter()
    frame = np.load(frame_path).astype(np.float32)
    detector = MorphologicalDetector()
    detector._cx.MIN_WEIGHT_SUM = 1e-6
    detections = detector.detect(frame)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return TrackingResult(
        frame_id=frame_id,
        timestamp_utc=datetime.now(UTC),
        detections=detections,
        processing_time_ms=elapsed_ms,
        background_level_adu=float(np.median(frame)),
    )


@dataclass
class BatchResult:
    """Summary result for a batch of frames."""

    results: list[TrackingResult]
    success_count: int
    failure_count: int
    failed_frames: list[str]


class BatchProcessor:
    """Distributes frame processing across CPU cores via ProcessPoolExecutor."""

    def run(
        self,
        frames: list[Path],
        max_workers: int | None = None,
    ) -> BatchResult:
        """Process a list of frame files in parallel.

        Args:
            frames: Paths to .npy sensor frames.
            max_workers: Number of worker processes. Defaults to :func:`os.cpu_count`.

        Returns:
            :class:`BatchResult` with results and failure statistics.
        """
        n_workers = max_workers or os.cpu_count() or 1
        results: list[TrackingResult] = []
        failed: list[str] = []

        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            future_to_path = {
                executor.submit(process_single_frame, path, idx): path
                for idx, path in enumerate(frames)
            }
            for future in as_completed(future_to_path, timeout=None):
                path = future_to_path[future]
                try:
                    result = future.result(timeout=_FRAME_TIMEOUT_S)
                    results.append(result)
                except TimeoutError:
                    failed.append(str(path))
                except (InvalidFrameError, DetectionError, Exception):
                    failed.append(str(path))

        return BatchResult(
            results=results,
            success_count=len(results),
            failure_count=len(failed),
            failed_frames=failed,
        )
