"""PipelineOrchestrator — composes detector and loader with zero business logic in routes.

Depends only on :class:`~leo_tracker.interfaces.AbstractDetector` and
:class:`~leo_tracker.interfaces.IFrameLoader`, never on concrete classes (DIP).
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import numpy.typing as npt

from .errors import DetectionError, InvalidFrameError
from .interfaces import AbstractDetector, IFrameLoader, IFrameWriter
from .models import CentroidResult, TrackingResult
from .processing import MorphologicalDetector


class NpyFrameLoader:
    """Default IFrameLoader — loads float32 NumPy arrays from .npy files."""

    def load(self, path: Path) -> npt.NDArray[np.float32]:
        """Load a .npy file as a float32 array.

        Args:
            path: Path to a .npy sensor frame.

        Returns:
            float32 2-D NumPy array.
        """
        return np.load(path).astype(np.float32)


class JsonFrameWriter:
    """Default IFrameWriter — serialises TrackingResult list to a JSON file."""

    def write(self, results: list[TrackingResult], path: Path) -> None:
        """Write results to a JSON file.

        Args:
            results: List of :class:`~leo_tracker.models.TrackingResult`.
            path: Destination .json file path.
        """
        data = [json.loads(r.model_dump_json()) for r in results]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class PipelineOrchestrator:
    """Coordinates frame loading, detection, and result assembly.

    Depends on :class:`~leo_tracker.interfaces.AbstractDetector` and
    :class:`~leo_tracker.interfaces.IFrameLoader` — concrete classes are
    injected at construction time for testability and extensibility.
    """

    def __init__(
        self,
        detector: AbstractDetector | None = None,
        loader: IFrameLoader | None = None,
    ) -> None:
        """Initialise orchestrator with optional injected collaborators.

        Args:
            detector: Detection backend. Defaults to :class:`~leo_tracker.processing.MorphologicalDetector`.
            loader: Frame loader. Defaults to :class:`NpyFrameLoader`.
        """
        self._detector: AbstractDetector = detector or MorphologicalDetector()
        self._loader: IFrameLoader = loader or NpyFrameLoader()

    def process_frame(self, frame_path: Path, frame_id: int = 0) -> TrackingResult:
        """Load and process a single frame.

        Args:
            frame_path: Path to the sensor frame file.
            frame_id: Numeric identifier for this frame.

        Returns:
            :class:`~leo_tracker.models.TrackingResult`.

        Raises:
            InvalidFrameError: For malformed input.
            DetectionError: For unexpected backend errors.
        """
        t0 = time.perf_counter()
        frame = self._loader.load(frame_path)
        detections = self._detector.detect(frame)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        bg = float(np.median(frame))
        return TrackingResult(
            frame_id=frame_id,
            timestamp_utc=datetime.now(UTC),
            detections=detections,
            processing_time_ms=elapsed_ms,
            background_level_adu=bg,
        )

    def process_batch(
        self,
        frame_paths: list[Path],
        writer: IFrameWriter | None = None,
        output_path: Path | None = None,
    ) -> list[TrackingResult]:
        """Process a list of frames sequentially.

        Args:
            frame_paths: Ordered list of sensor frame paths.
            writer: Optional result writer.
            output_path: Destination path for writer (required if *writer* is set).

        Returns:
            List of :class:`~leo_tracker.models.TrackingResult` in input order.
        """
        results: list[TrackingResult] = []
        for idx, path in enumerate(frame_paths):
            try:
                result = self.process_frame(path, frame_id=idx)
            except (InvalidFrameError, DetectionError):
                continue
            results.append(result)
        if writer and output_path:
            writer.write(results, output_path)
        return results
