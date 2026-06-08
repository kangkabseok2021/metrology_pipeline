"""pytest-postgresql: 3 analytics endpoints against a seeded 14-day dataset.

Expected rolling averages are computed in Python from the same seed data and
compared to the API response within +/- 0.01 — per the approved design spec.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).parents[1]))

pytestmark = pytest.mark.db


@pytest.fixture
async def client(seeded_db, db_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", db_url.replace("postgresql+psycopg2", "postgresql+asyncpg"))
    import importlib

    import api.db as db_module
    import api.main as main_module

    importlib.reload(db_module)
    importlib.reload(main_module)

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        async with main_module.app.router.lifespan_context(main_module.app):
            yield c


def _expected_rolling_7d_avg(rows: list[tuple], vehicle_id: str) -> dict:
    """Group (ts, temp) by day, average per day, then a 7-day rolling mean —
    the exact computation mv_battery_health_daily performs in SQL."""
    import pandas as pd

    df = pd.DataFrame(rows, columns=["ts", "battery_temp_c"])
    df["day"] = pd.to_datetime(df["ts"]).dt.date
    daily = df.groupby("day")["battery_temp_c"].mean().sort_index()
    rolling = daily.rolling(window=7, min_periods=1).mean()
    return {str(day): round(val, 2) for day, val in rolling.items()}


async def test_battery_health_returns_rolling_average_within_tolerance(client, seeded_db):
    vehicle_id = seeded_db["vehicle_ids"][0]
    expected_rolling = _expected_rolling_7d_avg(seeded_db["expected"][vehicle_id], vehicle_id)

    resp = await client.get(
        "/api/fleet/battery-health", params={"vehicle_id": vehicle_id, "days": 14}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body, "expected non-empty battery-health series"

    by_day = {row["day"]: row["rolling_7d_avg_temp_c"] for row in body}
    for day, expected_value in expected_rolling.items():
        assert day in by_day, f"missing day {day} in API response"
        assert abs(by_day[day] - expected_value) <= 0.01, (
            f"day {day}: API={by_day[day]} expected={expected_value}"
        )


async def test_geo_distribution_returns_non_empty_buckets_for_seeded_hour(client, seeded_db):
    resp = await client.get("/api/fleet/geo-distribution", params={"hour": 12})
    assert resp.status_code == 200
    body = resp.json()
    assert body, "expected non-empty geo-distribution buckets for hour=12"
    assert all(row["hour"] == 12 for row in body)
    assert all("lat_bucket" in row and "lon_bucket" in row and "event_count" in row for row in body)


async def test_vehicle_timeline_returns_bounded_chronological_series(client, seeded_db):
    vehicle_id = seeded_db["vehicle_ids"][0]
    expected_points = len(seeded_db["expected"][vehicle_id])

    resp = await client.get(f"/api/fleet/vehicle/{vehicle_id}/timeline", params={"limit": 50})
    assert resp.status_code == 200
    body = resp.json()

    assert 0 < len(body) <= 50
    assert len(body) <= expected_points
    timestamps = [row["ts"] for row in body]
    assert timestamps == sorted(timestamps, reverse=True), "timeline must be most-recent-first"


async def test_vehicle_timeline_returns_404_for_unknown_vehicle(client, seeded_db):
    resp = await client.get("/api/fleet/vehicle/00000000-0000-0000-0000-000000000000/timeline")
    assert resp.status_code == 404
