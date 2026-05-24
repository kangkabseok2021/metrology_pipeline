"""LEO Object Detection & Tracking Pipeline.

Processes synthetic satellite sensor frames to detect sub-pixel centroids
of objects against a noisy starfield using OpenCV + SciPy morphological chain.
"""

from .pipeline import PipelineOrchestrator

__all__ = ["PipelineOrchestrator"]
