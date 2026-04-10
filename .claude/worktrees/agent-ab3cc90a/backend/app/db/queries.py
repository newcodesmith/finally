"""All database query functions."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from .connection import get_db

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------


async def get_watchlist_tickers(user_id: str = "default") -> list[str]:
    """Return ordered list of ticker strings for the user's watchlist."""
    async with get_db() as db:
        async with db.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at ASC",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [row["ticker"] for row in rows]


async def add_watchlist_ticker(ticker: str, user_id: str = "default") -> bool:
    """Add ticker to watchlist. Returns True if added, False if already exists."""
    ticker = ticker.upper().strip()
    async with get_db() as db:
        try:
            await db.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, ticker, _now()),
            )
            await db.commit()
            return True
        except Exception:
            # UNIQUE constraint violation — already exists
            return False


async def remove_watchlist_ticker(ticker: str, user_id: str = "default") -> bool:
    """Remove ticker from watchlist. Returns True if removed, False if not found."""
    ticker = ticker.upper().strip()
    async with get_db() as db:
        async with db.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ) as cur:
            await db.commit()
            return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Portfolio / Profile
# ---------------------------------------------------------------------------


async def get_cash_balance(user_id: str = "default") -> float:
    """Return current cash balance."""
    async with get_db() as db:
        async with db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
            return row["cash_balance"] if row else 10000.0


async def get_positions(user_id: str = "default") -> list[dict]:
    """Return list of {ticker, quantity, avg_cost} dicts."""
    async with get_db() as db:
        async with db.execute(
            "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? ORDER BY ticker ASC",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def execute_trade(
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    user_id: str = "default",
) -> dict:
    """Execute a market order trade.

    Returns:
        {
            "success": bool,
            "error": str | None,
            "cash_balance": float,
            "position": {ticker, quantity, avg_cost} | None,
        }
    """
    ticker = ticker.upper().strip()
    if quantity <= 0:
        return {"success": False, "error": "Quantity must be positive", "cash_balance": 0.0, "position": None}

    async with get_db() as db:
        # Get current cash
        async with db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ) as cur:
            profile_row = await cur.fetchone()
        cash = profile_row["cash_balance"] if profile_row else 10000.0

        # Get current position
        async with db.execute(
            "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ) as cur:
            pos_row = await cur.fetchone()

        now = _now()

        if side == "buy":
            cost = quantity * price
            if cost > cash:
                return {
                    "success": False,
                    "error": f"Insufficient cash: need ${cost:.2f}, have ${cash:.2f}",
                    "cash_balance": cash,
                    "position": None,
                }
            new_cash = cash - cost

            if pos_row:
                old_qty = pos_row["quantity"]
                old_avg = pos_row["avg_cost"]
                new_qty = old_qty + quantity
                new_avg = (old_qty * old_avg + quantity * price) / new_qty
                await db.execute(
                    "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
                    (new_qty, new_avg, now, user_id, ticker),
                )
            else:
                await db.execute(
                    "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), user_id, ticker, quantity, price, now),
                )
                new_qty = quantity
                new_avg = price

        elif side == "sell":
            owned = pos_row["quantity"] if pos_row else 0.0
            if quantity > owned:
                return {
                    "success": False,
                    "error": f"Insufficient shares: trying to sell {quantity}, own {owned}",
                    "cash_balance": cash,
                    "position": None,
                }
            new_cash = cash + quantity * price
            new_qty = owned - quantity
            new_avg = pos_row["avg_cost"] if pos_row else 0.0

            if new_qty <= 0:
                await db.execute(
                    "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
                    (user_id, ticker),
                )
                new_qty = 0.0
                new_avg = 0.0
            else:
                await db.execute(
                    "UPDATE positions SET quantity = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
                    (new_qty, now, user_id, ticker),
                )
        else:
            return {"success": False, "error": f"Invalid side: {side}", "cash_balance": cash, "position": None}

        # Update cash balance
        await db.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (new_cash, user_id),
        )

        # Record the trade
        await db.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, ticker, side, quantity, price, now),
        )

        await db.commit()

    position = {"ticker": ticker, "quantity": new_qty, "avg_cost": new_avg} if new_qty > 0 else None
    return {
        "success": True,
        "error": None,
        "cash_balance": new_cash,
        "position": position,
    }


async def get_portfolio_history(user_id: str = "default") -> list[dict]:
    """Return all portfolio value snapshots as [{recorded_at, total_value}]."""
    async with get_db() as db:
        async with db.execute(
            "SELECT recorded_at, total_value FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at ASC",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(row) for row in rows]


async def record_portfolio_snapshot(total_value: float, user_id: str = "default") -> None:
    """Record a portfolio snapshot and prune rows older than 24 hours."""
    now = datetime.now(tz=timezone.utc)
    cutoff = (now - timedelta(hours=24)).isoformat()

    async with get_db() as db:
        await db.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, total_value, now.isoformat()),
        )
        # Prune old snapshots
        await db.execute(
            "DELETE FROM portfolio_snapshots WHERE user_id = ? AND recorded_at < ?",
            (user_id, cutoff),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


async def get_chat_history(limit: int = 20, user_id: str = "default") -> list[dict]:
    """Return the most recent `limit` chat messages, oldest first."""
    async with get_db() as db:
        async with db.execute(
            """
            SELECT role, content, actions, created_at
            FROM (
                SELECT role, content, actions, created_at
                FROM chat_messages
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ) sub
            ORDER BY created_at ASC
            """,
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
            result = []
            for row in rows:
                msg = {
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                }
                if row["actions"]:
                    msg["actions"] = json.loads(row["actions"])
                result.append(msg)
            return result


async def save_chat_message(
    role: str,
    content: str,
    actions: dict | None = None,
    user_id: str = "default",
) -> None:
    """Persist a chat message."""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                user_id,
                role,
                content,
                json.dumps(actions) if actions else None,
                _now(),
            ),
        )
        await db.commit()
