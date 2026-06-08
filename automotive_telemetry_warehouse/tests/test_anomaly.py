"""pytest-postgresql: physical-bounds + 4-sigma statistical-outlier flagging.

12 tests total across this file and test_endpoints.py, per the design spec.
"""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parents[1]))

from api.etl.anomaly import flag_anomalies  # noqa: E402

pytestmark = pytest.mark.db


def _insert_reading(conn, vehicle_key: int, time_key: int, ts, temp: float, rpm: int) -> int:
    row = conn.execute(
        text(
            "INSERT INTO fact_telemetry (vehicle_key, time_key, ts, battery_temp_c, "
            "soc_pct, rpm, lat, lon) VALUES (:vk, :tk, :ts, :temp, 0.5, :rpm, 48.0, 8.0) "
            "RETURNING event_id"
        ),
        {"vk": vehicle_key, "tk": time_key, "ts": ts, "temp": temp, "rpm": rpm},
    )
    return row.scalar_one()


@pytest.fixture
def one_vehicle(db_engine):
    """A single vehicle + a run of hourly time_keys for direct anomaly fixtures."""
    with db_engine.begin() as conn:
        vid = str(uuid.uuid4())
        vehicle_key = conn.execute(
            text(
                "INSERT INTO dim_vehicle (vehicle_id, model, manufacture_year, "
                "battery_capacity_kwh, region) VALUES (:vid, 'Model-A', 2023, 75.0, 'EU') "
                "RETURNING vehicle_key"
            ),
            {"vid": vid},
        ).scalar_one()

        start = datetime(2025, 6, 1, tzinfo=UTC)
        time_keys = []
        for h in range(48):
            ts = start + timedelta(hours=h)
            tk = conn.execute(
                text(
                    "INSERT INTO dim_time (ts, date, hour, day_of_week) "
                    "VALUES (:ts, :date, :hour, :dow) RETURNING time_key"
                ),
                {"ts": ts, "date": ts.date(), "hour": ts.hour, "dow": ts.weekday()},
            ).scalar_one()
            time_keys.append((tk, ts))
    return {"vehicle_key": vehicle_key, "time_keys": time_keys}


@pytest.mark.parametrize(
    ("temp", "rpm", "should_flag"),
    [
        (90.0, 3000, True),    # battery_temp_c > 85  -> physical-bounds violation
        (25.0, 3000, False),   # normal temp, normal rpm -> not flagged
        (40.0, -100, True),    # rpm < 0               -> physical-bounds violation
        (40.0, 3000, False),   # normal temp, normal rpm -> not flagged
        (-35.0, 3000, True),   # battery_temp_c < -30  -> physical-bounds violation
        (40.0, 8500, True),    # rpm > 8000            -> physical-bounds violation
    ],
)
def test_physical_bounds_flagging(db_engine, one_vehicle, temp, rpm, should_flag):
    tk, ts = one_vehicle["time_keys"][0]
    with db_engine.begin() as conn:
        event_id = _insert_reading(conn, one_vehicle["vehicle_key"], tk, ts, temp, rpm)

    flag_anomalies(db_engine, run_id="test-run-physical")

    with db_engine.connect() as conn:
        flagged = conn.execute(
            text("SELECT anomaly_flag FROM fact_telemetry WHERE event_id = :eid"),
            {"eid": event_id},
        ).scalar_one()
    assert flagged is should_flag


def test_four_sigma_statistical_outlier_is_flagged(db_engine, one_vehicle):
    vehicle_key = one_vehicle["vehicle_key"]
    # 47 readings clustered tightly around 40C, then one wild 4-sigma+ outlier
    with db_engine.begin() as conn:
        for tk, ts in one_vehicle["time_keys"][:-1]:
            _insert_reading(conn, vehicle_key, tk, ts, temp=40.0 + (hash(ts) % 3) * 0.1, rpm=3000)
        outlier_tk, outlier_ts = one_vehicle["time_keys"][-1]
        outlier_id = _insert_reading(conn, vehicle_key, outlier_tk, outlier_ts, temp=70.0, rpm=3000)

    flag_anomalies(db_engine, run_id="test-run-statistical")

    with db_engine.connect() as conn:
        flagged = conn.execute(
            text("SELECT anomaly_flag FROM fact_telemetry WHERE event_id = :eid"),
            {"eid": outlier_id},
        ).scalar_one()
    assert flagged is True


def test_normal_readings_in_tight_cluster_remain_unflagged(db_engine, one_vehicle):
    vehicle_key = one_vehicle["vehicle_key"]
    event_ids = []
    with db_engine.begin() as conn:
        for tk, ts in one_vehicle["time_keys"]:
            temp = 40.0 + (hash(ts) % 3) * 0.1
            event_ids.append(_insert_reading(conn, vehicle_key, tk, ts, temp=temp, rpm=3000))

    flag_anomalies(db_engine, run_id="test-run-tight-cluster")

    with db_engine.connect() as conn:
        flagged_count = conn.execute(
            text(
                "SELECT COUNT(*) FROM fact_telemetry "
                "WHERE event_id = ANY(:ids) AND anomaly_flag = TRUE"
            ),
            {"ids": event_ids},
        ).scalar_one()
    assert flagged_count == 0
