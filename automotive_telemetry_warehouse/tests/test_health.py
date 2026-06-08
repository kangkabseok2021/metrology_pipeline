"""pytest-postgresql: FastAPI app boots, /api/health responds against a real DB."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).parents[1]))

pytestmark = pytest.mark.db


@pytest.fixture
async def client(db_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", db_url.replace("postgresql+psycopg2", "postgresql+asyncpg"))
    # Reload so Settings() picks up the patched env var before the app is built
    import importlib

    import api.db as db_module
    import api.main as main_module

    importlib.reload(db_module)
    importlib.reload(main_module)

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        async with main_module.app.router.lifespan_context(main_module.app):
            yield c


async def test_health_endpoint_returns_200(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
