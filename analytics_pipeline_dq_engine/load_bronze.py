"""Load raw CSV into PostgreSQL bronze.raw_shipments (idempotent)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


def load_bronze(csv_path: Path, database_url: str) -> int:
    """Drop-and-reload bronze.raw_shipments; returns inserted row count."""
    engine = create_engine(database_url, future=True)

    # Read with dtype=str to preserve all raw dirty values
    df = pd.read_csv(csv_path, dtype=str)

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze"))
        conn.execute(text("DROP TABLE IF EXISTS bronze.raw_shipments CASCADE"))

    df.to_sql(
        name="raw_shipments",
        con=engine,
        schema="bronze",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=5_000,
    )
    return len(df)


def main() -> None:
    ap = argparse.ArgumentParser(description="Load Bronze layer")
    ap.add_argument("--csv", type=Path, default=Path("/tmp/raw_shipments.csv"))
    ap.add_argument(
        "--db",
        default=os.environ.get("DATABASE_URL", "postgresql://analytics:analytics@localhost:5432/analytics"),
    )
    args = ap.parse_args()

    n = load_bronze(args.csv, args.db)
    print(f"Loaded {n:,} rows → bronze.raw_shipments")


if __name__ == "__main__":
    main()
