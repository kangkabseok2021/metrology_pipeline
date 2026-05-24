"""Abstract base classes and protocols defining the leo_tracker SOLID contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt

from .models import CentroidResult, TrackingResult


class AbstractDetector(ABC):
    """Open/Closed base for all detection backends.

    Concrete subclasses implement :meth:`detect` and can be swapped at
    construction time without changing :class:`~leo_tracker.pipeline.PipelineOrchestrator`.
    """

    @abstractmethod
    def detect(self, frame: npt.NDArray[np.float32]) -> list[CentroidResult]:
        """Detect objects in a normalised float32 sensor frame.

        Args:
            frame: 2-D float32 array, values in ADU.

        Returns:
            List of sub-pixel centroid results (may be empty).
        """


@runtime_checkable
class IFrameLoader(Protocol):
    """Protocol for frame loaders — loads a raw sensor frame from disk."""

    def load(self, path: Path) -> npt.NDArray[np.float32]:
        """Load a sensor frame from *path* and return a float32 array.

        Args:
            path: Path to the frame file (.npy or similar).

        Returns:
            2-D float32 NumPy array in ADU.
        """
        ...


@runtime_checkable
class IFrameWriter(Protocol):
    """Protocol for result writers — serialises TrackingResult objects."""

    def write(self, results: list[TrackingResult], path: Path) -> None:
        """Write tracking results to *path*.

        Args:
            results: List of :class:`~leo_tracker.models.TrackingResult`.
            path: Destination file path (JSON or CSV).
        """
        ...
