"""Shared fixtures for analytics DQ pipeline tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://analytics:analytics@localhost:5432/analytics",
)


def _db_reachable() -> bool:
    try:
        from sqlalchemy import create_engine, text

        e = create_engine(DB_URL, future=True, pool_pre_ping=True)
        with e.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


requires_db = pytest.mark.db


@pytest.fixture(scope="session")
def small_csv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a small (500-row) CSV for fast offline tests."""
    import sys

    sys.path.insert(0, str(Path(__file__).parents[1]))
    from generate_raw_data import generate_raw_data  # noqa: PLC0415

    tmp = tmp_path_factory.mktemp("data") / "shipments.csv"
    df = generate_raw_data(n_rows=500, seed=0)
    df.to_csv(tmp, index=False)
    return tmp


@pytest.fixture(scope="session")
def db_engine():
    """SQLAlchemy engine for DB tests; skip if PostgreSQL unreachable."""
    if not _db_reachable():
        pytest.skip("PostgreSQL not reachable — set DATABASE_URL")
    from sqlalchemy import create_engine

    return create_engine(DB_URL, future=True)
