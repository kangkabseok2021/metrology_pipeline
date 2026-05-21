"""Tests for Pydantic models: validation, checksum, severity."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from metrology_pipeline.models import DefectDetection, ScanMetadata, SensorReading

# ---------------------------------------------------------------------------
# ScanMetadata
# ---------------------------------------------------------------------------


def test_valid_wafer_id() -> None:
    r"""A valid wafer_id [A-Z]{2}\d{6} is accepted."""
    meta = ScanMetadata(
        wafer_id="AB123456",
        scan_timestamp=datetime.now(UTC),
        pixel_size_nm=10.0,
        scan_width_um=5.12,
        equipment_id="SIM-001",
    )
    assert meta.wafer_id == "AB123456"


@pytest.mark.parametrize(
    "bad_id",
    ["ab123456", "ABC12345", "AB12345", "AB1234567", "12345678", "AB 12345"],
)
def test_invalid_wafer_id_rejected(bad_id: str) -> None:
    """Malformed wafer_id raises ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ScanMetadata(
            wafer_id=bad_id,
            scan_timestamp=datetime.now(UTC),
            pixel_size_nm=10.0,
            scan_width_um=5.12,
            equipment_id="SIM-001",
        )


def test_pixel_size_out_of_range_rejected() -> None:
    """pixel_size_nm outside (0, 100) raises ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ScanMetadata(
            wafer_id="AB000001",
            scan_timestamp=datetime.now(UTC),
            pixel_size_nm=150.0,
            scan_width_um=5.12,
            equipment_id="SIM-001",
        )


# ---------------------------------------------------------------------------
# SensorReading checksum validation
# ---------------------------------------------------------------------------


def test_checksum_mismatch_raises(reading: SensorReading, tmp_path: Path) -> None:
    """SensorReading raises ValueError when checksum does not match the file."""
    # Copy the HDF5 to a fresh location and corrupt the checksum
    copy_path = tmp_path / "corrupt.h5"
    shutil.copy2(reading.hdf5_path, copy_path)
    with pytest.raises(ValueError, match="checksum"):
        SensorReading(
            metadata=reading.metadata,
            shape=reading.shape,
            dtype=reading.dtype,
            hdf5_path=copy_path,
            checksum_sha256="0" * 64,  # deliberately wrong
        )


def test_missing_hdf5_raises(reading: SensorReading) -> None:
    """SensorReading raises ValueError when HDF5 file does not exist."""
    with pytest.raises(ValueError, match="not found"):
        SensorReading(
            metadata=reading.metadata,
            shape=reading.shape,
            dtype=reading.dtype,
            hdf5_path=Path("/nonexistent/path/file.h5"),
            checksum_sha256="a" * 64,
        )


# ---------------------------------------------------------------------------
# DefectDetection severity
# ---------------------------------------------------------------------------


def _make_defect(depth_nm: float) -> DefectDetection:
    return DefectDetection(
        defect_id=0,
        x_pixel=10,
        y_pixel=10,
        x_nm=100.0,
        y_nm=100.0,
        confidence=0.9,
        depth_nm=depth_nm,
    )


def test_severity_minor() -> None:
    """depth_nm < 5 → minor."""
    assert _make_defect(4.9).severity == "minor"


def test_severity_minor_zero() -> None:
    """depth_nm == 0 → minor."""
    assert _make_defect(0.0).severity == "minor"


def test_severity_major() -> None:
    """5 <= depth_nm < 20 → major."""
    assert _make_defect(5.0).severity == "major"
    assert _make_defect(19.9).severity == "major"


def test_severity_critical() -> None:
    """depth_nm >= 20 → critical."""
    assert _make_defect(20.0).severity == "critical"
    assert _make_defect(50.0).severity == "critical"


def test_confidence_out_of_range_rejected() -> None:
    """Confidence outside [0, 1] raises ValidationError."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        DefectDetection(
            defect_id=0,
            x_pixel=10,
            y_pixel=10,
            x_nm=100.0,
            y_nm=100.0,
            confidence=1.5,
            depth_nm=5.0,
        )
