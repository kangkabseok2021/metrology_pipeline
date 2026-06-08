"""Analytics endpoints — SQLAlchemy Core text() with bound params, no ORM.

battery-health and geo-distribution read from the Materialized Views (never
the 1.2 GB fact table — see docs/ARCHITECTURE.md). The per-vehicle timeline is
the one deliberate exception: it targets a single vehicle_key through the
dedicated idx_fact_vehicle_key index — a narrow, indexed point-lookup,
categorically different from a fleet-wide aggregate scan of the fact table.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session

router = APIRouter()


@router.get("/battery-health")
async def battery_health(
    vehicle_id: str | None = Query(default=None),
    model: str | None = Query(default=None),
    days: int = Query(default=14, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    if not vehicle_id and not model:
        raise HTTPException(400, "provide vehicle_id or model")

    # NOTE: asyncpg can't infer a bind param's type when it's compared only via
    # `:param IS NULL` (raises AmbiguousParameterError on a bare NULL) — the
    # spec's SQL hits this for optional filters. Minimal fix: CAST(:param AS ...)
    # gives asyncpg/Postgres a concrete type to prepare against regardless of
    # whether the value is NULL. (A bare `:param::type` suffix is mis-tokenized
    # by SQLAlchemy's text() bind-param parser — the adjacent colons are not
    # substituted — so CAST(...) is used instead of the `::` shorthand.)
    # NOTE: the MV's avg/max/p95/rolling columns are NUMERIC; asyncpg surfaces
    # those as Decimal, and FastAPI's default JSON encoder renders Decimal as a
    # *string* (to avoid float precision loss) — but the test compares the
    # response arithmetically against a Python float. Casting to double
    # precision here returns native floats so the JSON numbers compare cleanly.
    stmt = text(
        "SELECT vehicle_id, model, day::text AS day, "
        "avg_temp_c::double precision AS avg_temp_c, "
        "max_temp_c::double precision AS max_temp_c, "
        "p95_temp_c::double precision AS p95_temp_c, "
        "rolling_7d_avg_temp_c::double precision AS rolling_7d_avg_temp_c "
        "FROM mv_battery_health_daily "
        "WHERE (CAST(:vehicle_id AS uuid) IS NULL OR vehicle_id = CAST(:vehicle_id AS uuid)) "
        "  AND (CAST(:model AS varchar) IS NULL OR model = CAST(:model AS varchar)) "
        # `make_interval(days => :days)` avoids `:days || ' days'` string
        # concatenation, which asyncpg rejects (it binds `days` as an int and
        # won't implicitly stringify it for `||`).
        "  AND day >= (CURRENT_DATE - make_interval(days => CAST(:days AS integer))) "
        "ORDER BY vehicle_id, day"
    )
    rows = (
        await session.execute(stmt, {"vehicle_id": vehicle_id, "model": model, "days": days})
    ).mappings().all()
    return [dict(r) for r in rows]


@router.get("/geo-distribution")
async def geo_distribution(
    hour: int = Query(ge=0, le=23),
    model: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    # Same asyncpg AmbiguousParameterError fix as battery_health (see note there):
    # CAST(:model AS varchar) on the optional `model` bind param.
    stmt = text(
        "SELECT date::text AS date, hour, model, lat_bucket, lon_bucket, event_count "
        "FROM mv_fleet_geo_hourly "
        "WHERE hour = :hour "
        "  AND (CAST(:model AS varchar) IS NULL OR model = CAST(:model AS varchar)) "
        "ORDER BY event_count DESC"
    )
    rows = (await session.execute(stmt, {"hour": hour, "model": model})).mappings().all()
    return [dict(r) for r in rows]


@router.get("/vehicle/{vehicle_id}/timeline")
async def vehicle_timeline(
    vehicle_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    key_row = (
        await session.execute(
            text("SELECT vehicle_key FROM dim_vehicle WHERE vehicle_id = :vid"),
            {"vid": vehicle_id},
        )
    ).first()
    if key_row is None:
        raise HTTPException(404, f"vehicle {vehicle_id} not found")

    stmt = text(
        "SELECT ts, battery_temp_c, soc_pct, rpm, lat, lon, anomaly_flag "
        "FROM fact_telemetry "
        "WHERE vehicle_key = :vehicle_key "
        "ORDER BY ts DESC "
        "LIMIT :limit"
    )
    rows = (
        await session.execute(stmt, {"vehicle_key": key_row.vehicle_key, "limit": limit})
    ).mappings().all()
    return [dict(r) | {"ts": r["ts"].isoformat()} for r in rows]
