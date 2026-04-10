"""Health check endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from ..db.connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


@router.get("/api/health")
async def health_check():
    """Return health status including database connectivity check."""
    try:
        async with get_db() as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users_profile")
            row = await cursor.fetchone()
            user_count = row[0] if row else 0
        return {"status": "ok", "database": "connected", "users": user_count}
    except Exception:
        logger.exception("Health check database query failed")
        return {"status": "degraded", "database": "error"}
