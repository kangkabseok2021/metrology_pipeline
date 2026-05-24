"""Domain exceptions for the LEO tracker pipeline."""


class InvalidFrameError(ValueError):
    """Raised when a frame has non-finite values, wrong shape, or unsupported dtype."""


class DetectionError(RuntimeError):
    """Wraps unexpected errors from the detection backend (OpenCV / SciPy)."""
