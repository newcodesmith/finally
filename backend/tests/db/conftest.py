"""Shared fixtures for database tests."""

from __future__ import annotations

import tempfile
import os

import pytest

import app.db.connection as conn_mod
from app.db.schema import init_db


@pytest.fixture(autouse=True)
async def _test_db(tmp_path, monkeypatch):
    """Override DB_PATH to use a temp SQLite file and initialize the schema."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(conn_mod, "DB_PATH", db_file)
    await init_db()
    yield
