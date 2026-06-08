"""LISTEN/NOTIFY anomaly-flagging worker.

Wakes on the etl_complete channel (fired by load_warehouse.py's pg_notify),
runs a physical-bounds pass, then a per-(vehicle, day) 4-sigma statistical-
outlier pass — exactly the two-pass design from the approved spec.
"""

from __future__ import annotations

import asyncio
import logging

import asyncpg
from sqlalchemy import text
from sqlalchemy.engine import Engine

from api import db

logger = logging.getLogger("telemetry_warehouse.anomaly")

PHYSICAL_BOUNDS_SQL = text(
    "UPDATE fact_telemetry SET anomaly_flag = TRUE "
    "WHERE anomaly_flag = FALSE "
    "  AND (battery_temp_c > 85 OR battery_temp_c < -30 "
    "       OR rpm > 8000 OR rpm < 0)"
)

# Per-(vehicle_key, day) 4-sigma pass: flag rows whose battery_temp_c deviates
# more than 4 standard deviations from that vehicle's mean for that calendar day.
STATISTICAL_OUTLIER_SQL = text(
    "WITH stats AS ( "
    "    SELECT f.event_id, "
    "           AVG(f.battery_temp_c) OVER w AS mean_temp, "
    "           STDDEV_POP(f.battery_temp_c) OVER w AS std_temp, "
    "           f.battery_temp_c "
    "    FROM fact_telemetry f "
    "    JOIN dim_time d ON d.time_key = f.time_key "
    "    WHERE f.anomaly_flag = FALSE "
    "    WINDOW w AS (PARTITION BY f.vehicle_key, d.date) "
    ") "
    "UPDATE fact_telemetry f SET anomaly_flag = TRUE "
    "FROM stats s "
    "WHERE f.event_id = s.event_id "
    "  AND s.std_temp > 0 "
    "  AND ABS(s.battery_temp_c - s.mean_temp) > 4 * s.std_temp"
)


def flag_anomalies(engine: Engine, run_id: str) -> int:
    """Run the physical-bounds pass then the 4-sigma pass; return rows newly flagged."""
    with engine.begin() as conn:
        physical = conn.execute(PHYSICAL_BOUNDS_SQL).rowcount
        statistical = conn.execute(STATISTICAL_OUTLIER_SQL).rowcount
    total = physical + statistical
    logger.info(
        "run_id=%s flagged %d rows (%d physical, %d statistical)",
        run_id,
        total,
        physical,
        statistical,
    )
    return total


class AnomalyListener:
    """Owns the asyncpg LISTEN connection; runs as an asyncio background task."""

    def __init__(self) -> None:
        self._conn: asyncpg.Connection | None = None

    def start(self) -> asyncio.Task:
        return asyncio.create_task(self._run(), name="anomaly-listener")

    async def stop(self, task: asyncio.Task) -> None:
        task.cancel()
        if self._conn is not None:
            await self._conn.close()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _run(self) -> None:
        # NOTE: read `db.settings` (module attribute) rather than binding `settings`
        # at import time — tests reload `api.db` with a monkeypatched DATABASE_URL,
        # which replaces the `settings` instance on the module; reading it lazily
        # here picks up that fresh instance instead of a stale import-time reference.
        dsn = db.settings.database_url.replace("postgresql+asyncpg", "postgresql")
        self._conn = await asyncpg.connect(dsn)
        await self._conn.add_listener("etl_complete", self._on_notify)
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass

    def _on_notify(self, connection, pid, channel, payload) -> None:
        from sqlalchemy import create_engine

        sync_url = db.settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        engine = create_engine(sync_url, future=True)
        try:
            flag_anomalies(engine, run_id=payload)
        finally:
            engine.dispose()


anomaly_listener = AnomalyListener()
