"""Bulk-load synthetic telemetry CSV into the Star Schema via psycopg2 COPY.

Loads CSV -> pandas -> PostgreSQL like load_bronze.py, but uses
`COPY ... FROM STDIN` for the (large) fact table instead of `to_sql`, since
dimensions need idempotent upserts first (dim_vehicle, dim_time) before the
fact rows can reference them, then fires pg_notify('etl_complete', run_id) so
the FastAPI anomaly-ETL listener wakes up.
"""

from __future__ import annotations

import argparse
import io
import os
import uuid
from pathlib import Path

import pandas as pd
import psycopg2

MODELS_TO_YEAR = {
    "Model-A": 2021, "Model-B": 2022, "Model-C": 2023, "Model-D": 2023, "Model-E": 2024,
}
MODELS_TO_CAPACITY = {
    "Model-A": 60.0, "Model-B": 75.0, "Model-C": 82.0, "Model-D": 90.0, "Model-E": 100.0,
}
REGIONS = ["DACH", "Benelux", "Nordics", "Iberia", "France"]


def _ensure_vehicles(cur, df: pd.DataFrame, rng_seed: int = 0) -> dict[str, int]:
    """Insert any not-yet-seen vehicles into dim_vehicle; return id -> key map."""
    import numpy as np

    rng = np.random.default_rng(rng_seed)
    unique = df[["vehicle_id", "model"]].drop_duplicates()

    cur.execute("SELECT vehicle_id, vehicle_key FROM dim_vehicle")
    existing = {str(vid): key for vid, key in cur.fetchall()}

    new_rows = unique[~unique["vehicle_id"].astype(str).isin(existing.keys())]
    for _, row in new_rows.iterrows():
        model = row["model"]
        cur.execute(
            "INSERT INTO dim_vehicle (vehicle_id, model, manufacture_year, "
            "battery_capacity_kwh, region) VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (vehicle_id) DO UPDATE SET vehicle_id = EXCLUDED.vehicle_id "
            "RETURNING vehicle_key",
            (
                row["vehicle_id"], model, MODELS_TO_YEAR[model],
                MODELS_TO_CAPACITY[model], REGIONS[rng.integers(0, len(REGIONS))],
            ),
        )
        existing[str(row["vehicle_id"])] = cur.fetchone()[0]

    return existing


def _ensure_times(cur, df: pd.DataFrame) -> dict[pd.Timestamp, int]:
    """Insert any not-yet-seen timestamps into dim_time; return ts -> key map.

    `df["ts"]` must already be tz-aware UTC (see load_warehouse) — dim_time.ts
    is TIMESTAMPTZ, and PostgreSQL always returns tz-aware datetimes for it, so
    comparing tz-naive CSV timestamps against tz-aware DB timestamps would raise
    `TypeError: Cannot compare tz-naive and tz-aware timestamps`.
    """
    unique_ts = df["ts"].drop_duplicates()

    cur.execute("SELECT ts, time_key FROM dim_time")
    existing = {pd.Timestamp(ts): key for ts, key in cur.fetchall()}

    new_ts = [ts for ts in unique_ts if ts not in existing]
    for ts in new_ts:
        cur.execute(
            "INSERT INTO dim_time (ts, date, hour, day_of_week) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (ts) DO UPDATE SET ts = EXCLUDED.ts RETURNING time_key",
            (ts.to_pydatetime(), ts.date(), ts.hour, ts.dayofweek),
        )
        existing[ts] = cur.fetchone()[0]

    return existing


def load_warehouse(csv_path: Path, database_url: str) -> str:
    """COPY csv_path into the Star Schema; returns the run_id sent via pg_notify.

    Accepts either a plain `postgresql://` DSN or a SQLAlchemy-style
    `postgresql+psycopg2://` URL (the form the pytest-postgresql `db_url`
    fixture returns) — psycopg2.connect() only understands the former.
    """
    df = pd.read_csv(csv_path, parse_dates=["ts"])
    # Generator emits naive UTC timestamps; localize explicitly so they compare
    # equal to the tz-aware (TIMESTAMPTZ) values PostgreSQL returns on lookup.
    df["ts"] = pd.to_datetime(df["ts"]).dt.tz_localize("UTC")
    run_id = str(uuid.uuid4())

    dsn = database_url.replace("postgresql+psycopg2", "postgresql")
    conn = psycopg2.connect(dsn)
    try:
        with conn:
            with conn.cursor() as cur:
                vehicle_keys = _ensure_vehicles(cur, df)
                time_keys = _ensure_times(cur, df)

                buf = io.StringIO()
                fact = pd.DataFrame({
                    "vehicle_key": df["vehicle_id"].astype(str).map(vehicle_keys),
                    "time_key": pd.to_datetime(df["ts"]).map(time_keys),
                    "ts": df["ts"],
                    "battery_temp_c": df["battery_temp_c"],
                    "soc_pct": df["soc_pct"],
                    "rpm": df["rpm"],
                    "lat": df["lat"],
                    "lon": df["lon"],
                })
                fact.to_csv(buf, index=False, header=False)
                buf.seek(0)
                cur.copy_expert(
                    "COPY fact_telemetry (vehicle_key, time_key, ts, battery_temp_c, "
                    "soc_pct, rpm, lat, lon) FROM STDIN WITH (FORMAT csv)",
                    buf,
                )
                cur.execute("SELECT pg_notify('etl_complete', %s)", (run_id,))
    finally:
        conn.close()

    return run_id


def main() -> None:
    ap = argparse.ArgumentParser(description="Load telemetry CSV into the Star Schema")
    ap.add_argument("--csv", type=Path, default=Path("/tmp/telemetry.csv"))
    ap.add_argument(
        "--db",
        default=os.environ.get(
            "DATABASE_URL", "postgresql://telemetry:telemetry@localhost:5432/telemetry"
        ),
    )
    args = ap.parse_args()

    run_id = load_warehouse(args.csv, args.db)
    print(f"Loaded {args.csv} -> fact_telemetry  (run_id={run_id})")


if __name__ == "__main__":
    main()
