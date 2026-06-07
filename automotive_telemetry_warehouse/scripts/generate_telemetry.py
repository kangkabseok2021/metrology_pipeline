"""Generate synthetic fleet-telemetry data (NumPy-vectorised, deterministic).

Mirrors the shape of analytics_pipeline_dq_engine/generate_raw_data.py but with
fleet-telemetry-specific physics: battery_temp_c is SoC-dependent with a slow
per-vehicle ageing drift, which is what makes the Superset "distribution
widening over time" box-plot panel meaningful rather than decorative.
"""

from __future__ import annotations

import argparse
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

MODELS = ["Model-A", "Model-B", "Model-C", "Model-D", "Model-E"]
VEHICLE_POOL_SIZE = 500
START = np.datetime64("2024-01-01T00:00:00")
END = np.datetime64("2026-01-01T00:00:00")
RESOLUTION_SECONDS = 5


def _build_vehicle_pool(rng: np.random.Generator) -> pd.DataFrame:
    """500 vehicles spread evenly across 5 models, each with a fixed ageing rate."""
    raw = rng.integers(0, 256, size=(VEHICLE_POOL_SIZE, 16), dtype=np.uint8)
    ids = [str(uuid.UUID(bytes=row.tobytes())) for row in raw]
    models = np.tile(MODELS, VEHICLE_POOL_SIZE // len(MODELS))
    rng.shuffle(models)
    return pd.DataFrame({
        "vehicle_id": ids,
        "model": models,
        # +0.002 C/day per-vehicle ageing drift (battery ageing simulation)
        "drift_c_per_day": np.full(VEHICLE_POOL_SIZE, 0.002),
    })


def generate_telemetry(n_rows: int = 500_000, seed: int = 42) -> pd.DataFrame:
    """Return a DataFrame of synthetic fleet-telemetry rows."""
    rng = np.random.default_rng(seed)

    pool = _build_vehicle_pool(rng)
    row_idx = rng.integers(0, VEHICLE_POOL_SIZE, size=n_rows)
    vehicle_id = pool["vehicle_id"].to_numpy()[row_idx]
    model = pool["model"].to_numpy()[row_idx]
    drift_rate = pool["drift_c_per_day"].to_numpy()[row_idx]

    # Uniform-random timestamps over the 2-year window, snapped to 5s resolution
    span_seconds = int((END - START) / np.timedelta64(1, "s"))
    offsets = rng.integers(0, span_seconds // RESOLUTION_SECONDS, size=n_rows) * RESOLUTION_SECONDS
    ts = START + offsets.astype("timedelta64[s]")
    days_elapsed = offsets / 86_400.0

    soc_pct = rng.uniform(0.05, 1.0, size=n_rows)
    noise = rng.normal(0, 2, size=n_rows)
    ageing = drift_rate * days_elapsed
    battery_temp_c = np.clip(25 + 15 * (1 - soc_pct) + noise + ageing, -30, 85)

    rpm = rng.integers(0, 8_000, size=n_rows)
    lat = rng.uniform(35.0, 60.0, size=n_rows).round(6)   # rough European fleet bbox
    lon = rng.uniform(-10.0, 25.0, size=n_rows).round(6)

    return pd.DataFrame({
        "vehicle_id": vehicle_id,
        "model": model,
        "ts": ts,
        "battery_temp_c": battery_temp_c.round(2),
        "soc_pct": soc_pct.round(4),
        "rpm": rpm,
        "lat": lat,
        "lon": lon,
    })


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic fleet telemetry CSV")
    ap.add_argument("--rows", type=int, default=500_000)
    ap.add_argument("--output", type=Path, default=Path("/tmp/telemetry.csv"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="generate 1 row, print schema, exit")
    args = ap.parse_args()

    if args.dry_run:
        df = generate_telemetry(n_rows=1, seed=args.seed)
        print(df.dtypes)
        return

    df = generate_telemetry(n_rows=args.rows, seed=args.seed)
    df.to_csv(args.output, index=False)
    print(f"Generated {len(df):,} rows -> {args.output}")


if __name__ == "__main__":
    main()
