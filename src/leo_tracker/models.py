"""Pydantic v2 domain models and frozen dataclasses for the LEO tracker."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class GeneratorConfig:
    """Configuration for the synthetic image generator."""

    size: int = 512
    sky_background: float = 50.0
    n_stars: int = 15
    psf_sigma: float = 1.5
    streak_intensity: float = 300.0
    streak_sigma: float = 1.2
    streak_length_min: int = 40
    streak_length_max: int = 80
    seed: int = 42


class CentroidResult(BaseModel):
    """Sub-pixel centroid of a single detected object."""

    model_config = ConfigDict(frozen=True)

    x_px: int = Field(..., description="Integer pixel column of bounding-box centre")
    y_px: int = Field(..., description="Integer pixel row of bounding-box centre")
    x_sub: float = Field(..., ge=0.0, description="Sub-pixel x centroid (weighted CoM)")
    y_sub: float = Field(..., ge=0.0, description="Sub-pixel y centroid (weighted CoM)")
    snr: float = Field(..., ge=0.0, description="Signal-to-noise ratio of the detection")
    area_px: int = Field(..., ge=1, description="Blob area in pixels")
    uncertainty_px: float = Field(
        ..., ge=0.0, description="Cramer-Rao centroid uncertainty = psf_sigma / snr"
    )


class TrackingResult(BaseModel):
    """Output of processing a single sensor frame."""

    model_config = ConfigDict(frozen=True)

    frame_id: int
    timestamp_utc: datetime
    detections: list[CentroidResult]
    processing_time_ms: float = Field(..., ge=0.0)
    background_level_adu: float
