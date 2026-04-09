"""Tests for database schema creation and seed data."""

from __future__ import annotations

import pytest

from app.db.connection import get_db
from app.db.schema import init_db, DEFAULT_WATCHLIST


EXPECTED_TABLES = {
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
}


async def test_init_db_creates_all_tables():
    """init_db should create all 6 tables defined in the schema."""
    async with get_db() as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ) as cur:
            rows = await cur.fetchall()
            table_names = {row["name"] for row in rows}

    assert table_names == EXPECTED_TABLES


async def test_init_db_seeds_default_user():
    """Default user profile should exist with $10,000 cash."""
    async with get_db() as db:
        async with db.execute("SELECT id, cash_balance FROM users_profile") as cur:
            row = await cur.fetchone()

    assert row is not None
    assert row["id"] == "default"
    assert row["cash_balance"] == 10000.0


async def test_init_db_seeds_default_user_has_created_at():
    """Default user profile should have a non-empty created_at timestamp."""
    async with get_db() as db:
        async with db.execute("SELECT created_at FROM users_profile WHERE id = 'default'") as cur:
            row = await cur.fetchone()

    assert row is not None
    assert row["created_at"] is not None
    assert len(row["created_at"]) > 0


async def test_init_db_seeds_watchlist():
    """Default watchlist should contain 10 tickers."""
    async with get_db() as db:
        async with db.execute("SELECT ticker FROM watchlist WHERE user_id = 'default'") as cur:
            rows = await cur.fetchall()
            tickers = {row["ticker"] for row in rows}

    assert len(tickers) == 10
    assert tickers == set(DEFAULT_WATCHLIST)


async def test_init_db_idempotent():
    """Running init_db a second time should not duplicate data."""
    # init_db was already called by the fixture; call it again
    await init_db()

    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) as cnt FROM users_profile") as cur:
            row = await cur.fetchone()
            assert row["cnt"] == 1

        async with db.execute("SELECT COUNT(*) as cnt FROM watchlist") as cur:
            row = await cur.fetchone()
            assert row["cnt"] == 10


async def test_init_db_idempotent_triple():
    """Running init_db three times still results in no duplicates."""
    await init_db()
    await init_db()

    async with get_db() as db:
        async with db.execute("SELECT COUNT(*) as cnt FROM users_profile") as cur:
            row = await cur.fetchone()
            assert row["cnt"] == 1

        async with db.execute("SELECT COUNT(*) as cnt FROM watchlist") as cur:
            row = await cur.fetchone()
            assert row["cnt"] == 10


async def test_tables_start_empty_except_seeded():
    """positions, trades, portfolio_snapshots, and chat_messages should be empty after init."""
    async with get_db() as db:
        for table in ("positions", "trades", "portfolio_snapshots", "chat_messages"):
            async with db.execute(f"SELECT COUNT(*) as cnt FROM {table}") as cur:
                row = await cur.fetchone()
                assert row["cnt"] == 0, f"Table {table} should be empty after init"
