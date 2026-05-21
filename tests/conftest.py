"""Shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from metrology_pipeline import SensorDataGenerator, SensorReading
from metrology_pipeline.generator import DefectSpec


@pytest.fixture(scope="session")
def tmp_data(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Provide a session-scoped temporary directory."""
    return tmp_path_factory.mktemp("data")


@pytest.fixture(scope="session")
def generated(tmp_data: Path) -> tuple[SensorReading, list[DefectSpec]]:
    """Generate a 128x128 synthetic wafer scan once per session."""
    gen = SensorDataGenerator(size=128)
    reading, defects = gen.generate(
        "AB000001", n_defects=5, seed=42, output_dir=tmp_data
    )
    return reading, defects


@pytest.fixture(scope="session")
def reading(generated: tuple[SensorReading, list[DefectSpec]]) -> SensorReading:
    """Return just the SensorReading from the generated fixture."""
    return generated[0]


@pytest.fixture(scope="session")
def defect_specs(generated: tuple[SensorReading, list[DefectSpec]]) -> list[DefectSpec]:
    """Return just the DefectSpec list from the generated fixture."""
    return generated[1]
