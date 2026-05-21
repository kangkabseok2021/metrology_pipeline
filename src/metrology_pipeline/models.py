"""Pydantic v2 domain models for metrology pipeline."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)


class ScanMetadata(BaseModel):
    """Immutable metadata for a wafer scan."""

    model_config = ConfigDict(frozen=True)

    wafer_id: str
    scan_timestamp: datetime
    pixel_size_nm: float = Field(..., gt=0, lt=100)
    scan_width_um: float = Field(..., gt=0)
    equipment_id: str

    @field_validator("wafer_id")
    @classmethod
    def validate_wafer_id(cls, v: str) -> str:
        r"""Validate wafer_id matches pattern [A-Z]{2}\d{6}."""
        if not re.fullmatch(r"[A-Z]{2}\d{6}", v):
            raise ValueError(f"wafer_id must match [A-Z]{{2}}\\d{{6}}, got {v!r}")
        return v


class SensorReading(BaseModel):
    """A validated reference to an HDF5 wafer scan file."""

    model_config = ConfigDict(frozen=True)

    metadata: ScanMetadata
    shape: tuple[int, int]
    dtype: Literal["float32", "float64"]
    hdf5_path: Path
    checksum_sha256: str

    @model_validator(mode="after")
    def validate_file_and_checksum(self) -> SensorReading:
        """Verify the HDF5 file exists and its checksum matches."""
        if not self.hdf5_path.exists():
            raise ValueError(f"HDF5 file not found: {self.hdf5_path}")
        digest = hashlib.sha256(self.hdf5_path.read_bytes()).hexdigest()
        if digest != self.checksum_sha256:
            raise ValueError("SHA-256 checksum mismatch — file may be corrupted")
        return self


class DefectDetection(BaseModel):
    """A single detected defect on a wafer."""

    model_config = ConfigDict(frozen=True)

    defect_id: int
    x_pixel: int
    y_pixel: int
    x_nm: float
    y_nm: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    depth_nm: float = Field(..., ge=0.0)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def severity(self) -> Literal["minor", "major", "critical"]:
        """Classify defect severity by depth."""
        if self.depth_nm < 5.0:
            return "minor"
        elif self.depth_nm < 20.0:
            return "major"
        return "critical"


class PipelineResult(BaseModel):
    """Output of a complete pipeline run."""

    model_config = ConfigDict(frozen=True)

    scan: SensorReading
    defects: list[DefectDetection]
    processing_time_ms: float = Field(..., ge=0)
    algorithm: Literal["fft_bandpass", "wiener_deconvolution"]
    gpu_accelerated: bool
    false_positive_rate: float | None = None
