"""Seeds a small deterministic dataset directly via SQLAlchemy Core (no CSV/COPY)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import numpy as np
from sqlalchemy import text

MODELS = ["Model-A", "Model-B", "Model-C", "Model-D", "Model-E"]
N_VEHICLES = 10
N_DAYS = 14


def seed_fourteen_day_dataset(engine, seed: int = 7) -> dict:
    """Insert N_VEHICLES vehicles x N_DAYS days x 24 hourly readings.

    Returns a dict of {vehicle_id: [(ts, battery_temp_c), ...]} for assertions.
    """
    rng = np.random.default_rng(seed)
    # Anchor to "now" (not a fixed past date): the battery-health endpoint
    # filters `day >= CURRENT_DATE - days::interval`, so seeded rows must fall
    # within the most recent N_DAYS for the API/expected comparison to overlap.
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=N_DAYS - 1)
    vehicle_ids = [str(uuid.uuid4()) for _ in range(N_VEHICLES)]
    expected: dict[str, list[tuple[datetime, float]]] = {v: [] for v in vehicle_ids}

    with engine.begin() as conn:
        vehicle_keys = {}
        for i, vid in enumerate(vehicle_ids):
            row = conn.execute(
                text(
                    "INSERT INTO dim_vehicle (vehicle_id, model, manufacture_year, "
                    "battery_capacity_kwh, region) VALUES (:vid, :model, 2023, 75.0, 'EU') "
                    "RETURNING vehicle_key"
                ),
                {"vid": vid, "model": MODELS[i % len(MODELS)]},
            )
            vehicle_keys[vid] = row.scalar_one()

        for day in range(N_DAYS):
            for hour in range(24):
                ts = start + timedelta(days=day, hours=hour)
                row = conn.execute(
                    text(
                        "INSERT INTO dim_time (ts, date, hour, day_of_week) "
                        "VALUES (:ts, :date, :hour, :dow) "
                        "ON CONFLICT (ts) DO UPDATE SET ts = EXCLUDED.ts "
                        "RETURNING time_key"
                    ),
                    {"ts": ts, "date": ts.date(), "hour": hour, "dow": ts.weekday()},
                )
                time_key = row.scalar_one()

                for vid in vehicle_ids:
                    soc = float(rng.uniform(0.2, 0.9))
                    temp = round(25 + 15 * (1 - soc) + float(rng.normal(0, 1)), 2)
                    conn.execute(
                        text(
                            "INSERT INTO fact_telemetry (vehicle_key, time_key, ts, "
                            "battery_temp_c, soc_pct, rpm, lat, lon) VALUES "
                            "(:vk, :tk, :ts, :temp, :soc, :rpm, :lat, :lon)"
                        ),
                        {
                            "vk": vehicle_keys[vid], "tk": time_key, "ts": ts,
                            "temp": temp, "soc": round(soc, 4),
                            "rpm": int(rng.integers(800, 4000)),
                            "lat": round(float(rng.uniform(45, 50)), 6),
                            "lon": round(float(rng.uniform(5, 10)), 6),
                        },
                    )
                    expected[vid].append((ts, temp))

        conn.execute(text("REFRESH MATERIALIZED VIEW mv_battery_health_daily"))
        conn.execute(text("REFRESH MATERIALIZED VIEW mv_fleet_geo_hourly"))
        conn.execute(text("REFRESH MATERIALIZED VIEW mv_vehicle_last_position"))

    return {"vehicle_ids": vehicle_ids, "expected": expected}
