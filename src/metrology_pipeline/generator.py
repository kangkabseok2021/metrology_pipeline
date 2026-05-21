"""Synthetic wafer height-map generator."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import h5py
import numpy as np
import numpy.typing as npt

from .models import ScanMetadata, SensorReading


@dataclass
class DefectSpec:
    """Specification for a single synthetic defect."""

    x: int
    y: int
    radius_nm: float = 30.0
    depth_nm: float = 15.0


class SensorDataGenerator:
    """Generate synthetic wafer inspection data."""

    DEFAULT_SIZE: int = 512  # smaller default for tests; 4096 for production
    PIXEL_SIZE_NM: float = 10.0

    def __init__(self, size: int = DEFAULT_SIZE) -> None:
        """Initialize generator with given image size."""
        self._size = size

    def generate(
        self,
        wafer_id: str,
        n_defects: int,
        seed: int,
        output_dir: Path = Path("/tmp"),
    ) -> tuple[SensorReading, list[DefectSpec]]:
        """Generate a synthetic wafer scan and save to HDF5."""
        rng = np.random.default_rng(seed)
        height_map, defect_specs = self._make_height_map(n_defects, rng)
        path = output_dir / f"{wafer_id}.h5"
        checksum = self._save_hdf5(path, height_map, wafer_id, defect_specs)
        metadata = ScanMetadata(
            wafer_id=wafer_id,
            scan_timestamp=datetime.now(UTC),
            pixel_size_nm=self.PIXEL_SIZE_NM,
            scan_width_um=self._size * self.PIXEL_SIZE_NM / 1000.0,
            equipment_id="SIM-001",
        )
        reading = SensorReading(
            metadata=metadata,
            shape=(self._size, self._size),
            dtype="float32",
            hdf5_path=path,
            checksum_sha256=checksum,
        )
        return reading, defect_specs

    def _make_height_map(
        self, n_defects: int, rng: np.random.Generator
    ) -> tuple[npt.NDArray[np.float32], list[DefectSpec]]:
        """Create synthetic height map with embedded defects."""
        s = self._size
        x = np.linspace(0, 1, s, dtype=np.float32)
        y = np.linspace(0, 1, s, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)
        surface = (
            0.5 * np.sin(2 * np.pi * 4 * xx) * np.sin(2 * np.pi * 4 * yy)
        ).astype(np.float32)
        noise = rng.normal(0, 0.05, (s, s)).astype(np.float32)
        sigma = 5.0
        defect_specs: list[DefectSpec] = []
        defect_map = np.zeros((s, s), dtype=np.float32)
        for _i in range(n_defects):
            cx = int(rng.integers(20, s - 20))
            cy = int(rng.integers(20, s - 20))
            depth = float(rng.uniform(2.0, 30.0))
            spec = DefectSpec(x=cx, y=cy, depth_nm=depth)
            defect_specs.append(spec)
            xi = np.arange(s)
            yi = np.arange(s)
            xxg, yyg = np.meshgrid(xi, yi)
            blob = (
                depth
                / 10.0
                * np.exp(-((xxg - cx) ** 2 + (yyg - cy) ** 2) / (2 * sigma**2))
            )
            defect_map += blob.astype(np.float32)
        return (surface + defect_map + noise), defect_specs

    def _save_hdf5(
        self,
        path: Path,
        height_map: npt.NDArray[np.float32],
        wafer_id: str,
        defects: list[DefectSpec],
    ) -> str:
        """Save height map and defect specs to HDF5, return SHA-256 checksum."""
        chunk = min(256, self._size)
        with h5py.File(path, "w") as f:
            ds = f.create_dataset(
                "scan/height_map",
                data=height_map,
                chunks=(chunk, chunk),
                compression="gzip",
            )
            ds.attrs["wafer_id"] = wafer_id
            dt = np.dtype(
                [("x", "i4"), ("y", "i4"), ("radius_nm", "f4"), ("depth_nm", "f4")]
            )
            arr = np.array(
                [(d.x, d.y, d.radius_nm, d.depth_nm) for d in defects], dtype=dt
            )
            f.create_dataset("scan/defects", data=arr)
        return hashlib.sha256(path.read_bytes()).hexdigest()
