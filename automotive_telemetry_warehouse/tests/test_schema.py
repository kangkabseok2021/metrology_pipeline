"""pytest-postgresql: DDL applies, BRIN/partial indexes exist, MVs refresh."""

from __future__ import annotations

from sqlalchemy import inspect, text


def test_ddl_creates_expected_tables(db_engine):
    insp = inspect(db_engine)
    tables = set(insp.get_table_names())
    assert {"fact_telemetry", "dim_vehicle", "dim_time"}.issubset(tables)


def test_brin_index_exists_on_ts(db_engine):
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'idx_fact_ts_brin'"
            )
        ).fetchone()
    assert row is not None
    assert "using brin" in row[0].lower()


def test_partial_index_exists_on_anomaly_flag(db_engine):
    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'idx_fact_anomaly'"
            )
        ).fetchone()
    assert row is not None
    assert "where (anomaly_flag = true)" in row[0].lower()


def test_materialized_views_exist_and_refresh_without_error(db_engine):
    with db_engine.connect() as conn:
        names = {
            r[0]
            for r in conn.execute(
                text("SELECT matviewname FROM pg_matviews")
            ).fetchall()
        }
    assert {
        "mv_battery_health_daily", "mv_fleet_geo_hourly", "mv_vehicle_last_position",
    }.issubset(names)

    with db_engine.begin() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW mv_battery_health_daily"))
        conn.execute(text("REFRESH MATERIALIZED VIEW mv_fleet_geo_hourly"))
        conn.execute(text("REFRESH MATERIALIZED VIEW mv_vehicle_last_position"))
