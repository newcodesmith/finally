"""Tests for the health check endpoint."""

from __future__ import annotations

import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

# Set DB_PATH before any app imports so the module-level DB_PATH in
# app.db.connection resolves to our temp directory.
_tmp = tempfile.mkdtemp()
_test_db_path = os.path.join(_tmp, "test_health.db")
os.environ["DB_PATH"] = _test_db_path

from app.db.schema import init_db  # noqa: E402
from app.main import app  # noqa: E402
import app.db.connection as _conn_mod  # noqa: E402

_initialized = False


async def _ensure_init():
    global _initialized
    if not _initialized:
        # Patch the cached module-level DB_PATH as a safety net in case
        # it was already imported by another test module before our env
        # override took effect.
        _conn_mod.DB_PATH = _test_db_path
        await init_db()
        _initialized = True


@pytest.fixture
async def client():
    await _ensure_init()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_returns_ok(client):
    """GET /api/health returns 200 with status ok."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


async def test_health_response_shape(client):
    """Health response contains exactly the expected fields."""
    resp = await client.get("/api/health")
    data = resp.json()
    assert set(data.keys()) == {"status"}
