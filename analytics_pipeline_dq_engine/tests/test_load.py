"""3 pytest tests: Bronze layer load (requires PostgreSQL)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).parents[1]))
from generate_raw_data import generate_raw_data
from load_bronze import load_bronze

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def loaded_db(db_engine, tmp_path_factory):  # type: ignore[no-untyped-def]
    """Generate 2K rows, load Bronze, return engine."""
    tmp = tmp_path_factory.mktemp("bronze") / "test.csv"
    df = generate_raw_data(n_rows=2_000, seed=7)
    df.to_csv(tmp, index=False)

    from tests.conftest import DB_URL

    load_bronze(tmp, DB_URL)
    return db_engine


def test_bronze_table_exists(loaded_db) -> None:  # type: ignore[no-untyped-def]
    inspector = inspect(loaded_db)
    tables = inspector.get_table_names(schema="bronze")
    assert "raw_shipments" in tables


def test_bronze_row_count(loaded_db) -> None:  # type: ignore[no-untyped-def]
    with loaded_db.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM bronze.raw_shipments"))
        count = result.scalar_one()
    assert count >= 2_000


def test_bronze_columns_present(loaded_db) -> None:  # type: ignore[no-untyped-def]
    inspector = inspect(loaded_db)
    cols = {c["name"] for c in inspector.get_columns("raw_shipments", schema="bronze")}
    expected = {"shipment_id", "origin_hub", "shipping_cost_usd", "ship_date"}
    assert expected.issubset(cols)
