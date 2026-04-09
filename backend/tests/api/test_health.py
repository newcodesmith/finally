"""Tests for GET /api/health."""

from __future__ import annotations


async def test_health_returns_ok(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"status": "ok"}


async def test_health_response_shape(client):
    """Ensure the response has exactly the expected keys."""
    resp = await client.get("/api/health")
    data = resp.json()
    assert set(data.keys()) == {"status"}
