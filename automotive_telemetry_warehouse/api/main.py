"""FastAPI app: lifespan-managed engine, slow-query middleware, anomaly ETL hook."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from api.db import engine
from api.etl.anomaly import anomaly_listener
from api.routers import fleet

logger = logging.getLogger("telemetry_warehouse")
SLOW_QUERY_THRESHOLD_S = 0.5


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    listener_task = anomaly_listener.start()
    try:
        yield
    finally:
        await anomaly_listener.stop(listener_task)
        await engine.dispose()


app = FastAPI(title="Automotive Telemetry Data Warehouse API", lifespan=lifespan)
app.include_router(fleet.router, prefix="/api/fleet", tags=["fleet"])


@app.middleware("http")
async def slow_query_logger(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    if elapsed > SLOW_QUERY_THRESHOLD_S:
        logger.warning("slow request: %s %s took %.3fs", request.method, request.url.path, elapsed)
    return response


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
