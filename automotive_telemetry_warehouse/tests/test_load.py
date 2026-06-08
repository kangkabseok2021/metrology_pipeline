"""pytest-postgresql: COPY-based loader populates the Star Schema and notifies."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from generate_telemetry import generate_telemetry  # noqa: E402
from load_warehouse import load_warehouse  # noqa: E402

pytestmark = pytest.mark.db


@pytest.fixture
def small_csv(tmp_path) -> Path:
    csv_path = tmp_path / "telemetry.csv"
    generate_telemetry(n_rows=2_000, seed=11).to_csv(csv_path, index=False)
    return csv_path


def test_load_populates_dimensions_and_fact(db_url, small_csv):
    run_id = load_warehouse(small_csv, db_url)
    assert run_id

    from sqlalchemy import create_engine

    engine = create_engine(db_url, future=True)
    with engine.connect() as conn:
        n_vehicles = conn.execute(text("SELECT COUNT(*) FROM dim_vehicle")).scalar_one()
        n_times = conn.execute(text("SELECT COUNT(*) FROM dim_time")).scalar_one()
        n_facts = conn.execute(text("SELECT COUNT(*) FROM fact_telemetry")).scalar_one()
    engine.dispose()

    assert n_vehicles > 0
    assert n_times > 0
    assert n_facts == 2_000


def test_load_is_idempotent_on_rerun(db_url, small_csv):
    load_warehouse(small_csv, db_url)
    second_run_id = load_warehouse(small_csv, db_url)
    assert second_run_id

    from sqlalchemy import create_engine

    engine = create_engine(db_url, future=True)
    with engine.connect() as conn:
        n_vehicles = conn.execute(text("SELECT COUNT(*) FROM dim_vehicle")).scalar_one()
        n_facts = conn.execute(text("SELECT COUNT(*) FROM fact_telemetry")).scalar_one()
    engine.dispose()

    # Re-running with the same vehicle pool must not duplicate dimension rows;
    # the fact table grows (each run is a new ETL batch — append-only warehouse load).
    assert n_vehicles <= 500
    assert n_facts == 4_000


def test_load_fires_pg_notify_on_completion(db_url, small_csv):
    from sqlalchemy import create_engine

    engine = create_engine(db_url, future=True)
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("LISTEN etl_complete")
        raw.commit()

        load_warehouse(small_csv, db_url)

        raw.poll()
        notifies = list(raw.notifies)
    finally:
        raw.close()
        engine.dispose()

    assert any(n.channel == "etl_complete" for n in notifies)
