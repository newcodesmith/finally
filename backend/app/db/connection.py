"""SQLite connection management."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import aiosqlite

DB_PATH = os.environ.get("DB_PATH", "./db/finally.db")


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
