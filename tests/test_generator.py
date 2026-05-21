"""Tests for SensorDataGenerator: HDF5 round-trip, defect count, checksum."""

from __future__ import annotations

import hashlib

import h5py
import numpy as np
import pytest

from metrology_pipeline import SensorDataGenerator, SensorReading
from metrology_pipeline.generator import DefectSpec


def test_generate_returns_sensor_reading(reading: SensorReading) -> None:
    """Generated object is a SensorReading instance."""
    assert isinstance(reading, SensorReading)


def test_generate_returns_defect_specs(defect_specs: list[DefectSpec]) -> None:
    """Generator returns exactly the requested number of DefectSpecs."""
    assert len(defect_specs) == 5


def test_hdf5_file_exists(reading: SensorReading) -> None:
    """HDF5 file was written to disk."""
    assert reading.hdf5_path.exists()


def test_hdf5_round_trip(reading: SensorReading) -> None:
    """Height map can be read back from HDF5 with correct dtype and shape."""
    with h5py.File(reading.hdf5_path, "r") as f:
        height_map = f["scan/height_map"][()]
    assert height_map.dtype == np.float32
    assert height_map.shape == (128, 128)


def test_hdf5_wafer_id_attribute(reading: SensorReading) -> None:
    """HDF5 dataset carries wafer_id attribute matching metadata."""
    with h5py.File(reading.hdf5_path, "r") as f:
        wid = f["scan/height_map"].attrs["wafer_id"]
    assert wid == reading.metadata.wafer_id


def test_hdf5_defects_dataset(
    reading: SensorReading, defect_specs: list[DefectSpec]
) -> None:
    """HDF5 defects dataset has one row per DefectSpec."""
    with h5py.File(reading.hdf5_path, "r") as f:
        arr = f["scan/defects"][()]
    assert len(arr) == len(defect_specs)


def test_checksum_is_sha256(reading: SensorReading) -> None:
    """Stored checksum matches a freshly computed SHA-256."""
    fresh = hashlib.sha256(reading.hdf5_path.read_bytes()).hexdigest()
    assert reading.checksum_sha256 == fresh


def test_sensor_reading_shape(reading: SensorReading) -> None:
    """SensorReading shape matches generator size."""
    assert reading.shape == (128, 128)


def test_metadata_pixel_size(reading: SensorReading) -> None:
    """Pixel size matches the generator constant."""
    assert reading.metadata.pixel_size_nm == pytest.approx(
        SensorDataGenerator.PIXEL_SIZE_NM
    )
