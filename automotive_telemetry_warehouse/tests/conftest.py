"""Shared pytest-postgresql fixtures: ephemeral DB per test session, schema applied."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest_postgresql import factories
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

SCHEMA_SQL = (Path(__file__).parents[1] / "db" / "schema.sql").read_text()

postgresql_proc = factories.postgresql_proc(port=None)
postgresql = factories.postgresql("postgresql_proc")


def _sync_url(conn) -> str:
    return (
        f"postgresql+psycopg2://{conn.info.user}:@{conn.info.host}:"
        f"{conn.info.port}/{conn.info.dbname}"
    )


@pytest.fixture
def db_url(postgresql) -> str:
    """Apply schema.sql to the ephemeral DB and return its sync SQLAlchemy URL."""
    # NOTE: pytest_postgresql 8.x's `postgresql` fixture yields a psycopg3
    # `Connection` whose `.info` IS the `ConnectionInfo` (not a wrapper with a
    # nested `.info`), so `_sync_url` (which expects `conn.info.user` etc.)
    # must receive the connection itself, not `postgresql.info`.
    url = _sync_url(postgresql)
    engine = create_engine(url, future=True)
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))
    engine.dispose()
    return url


@pytest.fixture
def db_engine(db_url):
    engine = create_engine(db_url, future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def seeded_db(db_engine):
    """Seed a 14-day/10-vehicle hourly dataset; return {engine, vehicle_ids, expected}.

    `expected` maps vehicle_id -> [(ts, battery_temp_c), ...] as inserted, so
    endpoint tests can compute the same rolling average in Python and compare.
    """
    from seed_helpers import seed_fourteen_day_dataset  # noqa: PLC0415

    seed = seed_fourteen_day_dataset(db_engine)
    return {"engine": db_engine, **seed}
