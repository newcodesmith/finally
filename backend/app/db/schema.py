"""Database schema creation and seed data."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from .connection import get_db

logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users_profile (
    id TEXT PRIMARY KEY DEFAULT 'default',
    cash_balance REAL NOT NULL DEFAULT 10000.0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE(user_id, ticker)
);

CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, ticker)
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    executed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'default',
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    actions TEXT,
    created_at TEXT NOT NULL
);
"""

DEFAULT_WATCHLIST = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]


async def init_db() -> None:
    """Create tables and seed default data if missing."""
    async with get_db() as db:
        # Create all tables
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()

        # Seed default user profile if empty
        async with db.execute("SELECT COUNT(*) FROM users_profile") as cur:
            row = await cur.fetchone()
            if row[0] == 0:
                now = datetime.now(tz=timezone.utc).isoformat()
                await db.execute(
                    "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
                    ("default", 10000.0, now),
                )
                logger.info("Seeded default user profile")

        # Seed default watchlist if empty
        async with db.execute("SELECT COUNT(*) FROM watchlist") as cur:
            row = await cur.fetchone()
            if row[0] == 0:
                now = datetime.now(tz=timezone.utc).isoformat()
                for ticker in DEFAULT_WATCHLIST:
                    await db.execute(
                        "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                        (str(uuid.uuid4()), "default", ticker, now),
                    )
                logger.info("Seeded default watchlist with %d tickers", len(DEFAULT_WATCHLIST))

        await db.commit()
        logger.info("Database initialized")
