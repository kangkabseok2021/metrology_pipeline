"""Offline tests for the synthetic telemetry generator — no DB needed."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from generate_telemetry import MODELS, VEHICLE_POOL_SIZE, generate_telemetry  # noqa: E402


def test_returns_requested_row_count():
    df = generate_telemetry(n_rows=1_000, seed=0)
    assert len(df) == 1_000


def test_schema_columns_and_dtypes():
    df = generate_telemetry(n_rows=500, seed=0)
    expected = {
        "vehicle_id", "model", "ts", "battery_temp_c", "soc_pct",
        "rpm", "lat", "lon",
    }
    assert expected.issubset(set(df.columns))
    assert np.issubdtype(df["battery_temp_c"].dtype, np.floating)
    assert np.issubdtype(df["rpm"].dtype, np.integer)


def test_vehicle_pool_bounded_to_500_across_5_models():
    df = generate_telemetry(n_rows=20_000, seed=1)
    assert df["vehicle_id"].nunique() <= VEHICLE_POOL_SIZE
    assert set(df["model"].unique()).issubset(set(MODELS))


def test_timestamps_within_two_year_window():
    df = generate_telemetry(n_rows=5_000, seed=2)
    assert df["ts"].min() >= np.datetime64("2024-01-01")
    assert df["ts"].max() <= np.datetime64("2026-01-01")


def test_battery_temp_within_physical_bounds():
    df = generate_telemetry(n_rows=20_000, seed=3)
    # generator clamps to realistic bounds; ageing drift is tiny (+0.002C/day)
    assert df["battery_temp_c"].between(-30, 85).all()


def test_battery_temp_correlates_inversely_with_soc():
    df = generate_telemetry(n_rows=50_000, seed=4)
    # battery_temp_c = 25 + 15*(1 - SoC) + noise -> low SoC, higher mean temp
    low_soc = df[df["soc_pct"] < 0.2]["battery_temp_c"].mean()
    high_soc = df[df["soc_pct"] > 0.8]["battery_temp_c"].mean()
    assert low_soc > high_soc


def test_rpm_and_gps_within_plausible_ranges():
    df = generate_telemetry(n_rows=20_000, seed=5)
    assert df["rpm"].between(0, 8_000).all()
    assert df["lat"].between(-90, 90).all()
    assert df["lon"].between(-180, 180).all()


def test_deterministic_with_seed():
    a = generate_telemetry(n_rows=1_000, seed=42)
    b = generate_telemetry(n_rows=1_000, seed=42)
    assert a.equals(b)
