"""Nightly DAG: check_new_data >> refresh_mv >> notify_api.

Idempotent — refresh_mv is skipped via short-circuit when no new fact_telemetry
rows have landed in the last 24h. Uses REFRESH MATERIALIZED VIEW CONCURRENTLY
so readers (Superset, the FastAPI endpoints) are never locked out.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

WAREHOUSE_CONN_ID = "telemetry_warehouse"
API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")

MATERIALIZED_VIEWS = [
    "mv_battery_health_daily",
    "mv_fleet_geo_hourly",
    "mv_vehicle_last_position",
]


def _check_new_data() -> bool:
    hook = PostgresHook(postgres_conn_id=WAREHOUSE_CONN_ID)
    count = hook.get_first(
        "SELECT COUNT(*) FROM fact_telemetry WHERE ts > NOW() - INTERVAL '24 hours'"
    )[0]
    return count > 0


def _refresh_materialized_views() -> None:
    hook = PostgresHook(postgres_conn_id=WAREHOUSE_CONN_ID)
    conn = hook.get_conn()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for view in MATERIALIZED_VIEWS:
                cur.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}")
    finally:
        conn.close()


def _notify_api() -> None:
    import urllib.request

    urllib.request.urlopen(f"{API_BASE_URL}/api/health", timeout=10)


with DAG(
    dag_id="refresh_materialized_views",
    description="Nightly refresh of fleet-telemetry Materialized Views",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["telemetry-warehouse"],
) as dag:
    check_new_data = ShortCircuitOperator(
        task_id="check_new_data",
        python_callable=_check_new_data,
    )

    refresh_mv = PythonOperator(
        task_id="refresh_mv",
        python_callable=_refresh_materialized_views,
    )

    notify_api = PythonOperator(
        task_id="notify_api",
        python_callable=_notify_api,
    )

    check_new_data >> refresh_mv >> notify_api
