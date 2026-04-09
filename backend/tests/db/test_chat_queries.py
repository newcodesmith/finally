"""Tests for chat message query functions."""

from __future__ import annotations

import pytest
import asyncio

from app.db.queries import save_chat_message, get_chat_history


# ---------------------------------------------------------------------------
# save_chat_message
# ---------------------------------------------------------------------------


async def test_save_and_retrieve_user_message():
    """A saved user message should appear in history."""
    await save_chat_message("user", "Hello, what should I buy?")
    history = await get_chat_history()

    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello, what should I buy?"
    assert "actions" not in history[0]


async def test_save_and_retrieve_assistant_message():
    """A saved assistant message should appear in history."""
    await save_chat_message("assistant", "I suggest buying AAPL.")
    history = await get_chat_history()

    assert len(history) == 1
    assert history[0]["role"] == "assistant"
    assert history[0]["content"] == "I suggest buying AAPL."


async def test_message_has_created_at():
    """Saved messages should have a created_at timestamp."""
    await save_chat_message("user", "Test message")
    history = await get_chat_history()

    assert "created_at" in history[0]
    assert len(history[0]["created_at"]) > 0


# ---------------------------------------------------------------------------
# Actions JSON round-trip
# ---------------------------------------------------------------------------


async def test_actions_json_round_trip():
    """Actions dict should survive save → load as JSON."""
    actions = {
        "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],
        "watchlist_changes": [{"ticker": "PYPL", "action": "add"}],
    }
    await save_chat_message("assistant", "Done!", actions=actions)
    history = await get_chat_history()

    assert len(history) == 1
    assert history[0]["actions"] == actions


async def test_actions_none_omitted():
    """Messages without actions should not have an 'actions' key."""
    await save_chat_message("user", "Hello")
    history = await get_chat_history()

    assert "actions" not in history[0]


async def test_actions_empty_dict():
    """An empty actions dict should round-trip correctly."""
    await save_chat_message("assistant", "Nothing to do.", actions={})
    history = await get_chat_history()

    assert history[0]["actions"] == {}


async def test_actions_complex_structure():
    """Nested structures in actions should survive the round-trip."""
    actions = {
        "trades": [
            {"ticker": "AAPL", "side": "buy", "quantity": 5},
            {"ticker": "GOOGL", "side": "sell", "quantity": 2},
        ],
        "watchlist_changes": [],
        "metadata": {"reason": "diversification", "confidence": 0.85},
    }
    await save_chat_message("assistant", "Executed trades.", actions=actions)
    history = await get_chat_history()

    assert history[0]["actions"] == actions


# ---------------------------------------------------------------------------
# Ordering and limits
# ---------------------------------------------------------------------------


async def test_history_ordered_oldest_first():
    """Messages should be returned oldest-first."""
    await save_chat_message("user", "First")
    await asyncio.sleep(0.01)  # ensure distinct timestamps
    await save_chat_message("assistant", "Second")
    await asyncio.sleep(0.01)
    await save_chat_message("user", "Third")

    history = await get_chat_history()
    contents = [m["content"] for m in history]
    assert contents == ["First", "Second", "Third"]


async def test_history_limit():
    """Limit should return only the N most recent messages, oldest-first."""
    for i in range(10):
        await save_chat_message("user", f"Message {i}")
        await asyncio.sleep(0.005)

    history = await get_chat_history(limit=3)
    assert len(history) == 3
    # Should be the last 3 messages, ordered oldest-first
    contents = [m["content"] for m in history]
    assert contents == ["Message 7", "Message 8", "Message 9"]


async def test_history_limit_larger_than_count():
    """Limit larger than actual messages should return all messages."""
    await save_chat_message("user", "Only one")
    history = await get_chat_history(limit=100)
    assert len(history) == 1


async def test_history_empty():
    """No messages should return an empty list."""
    history = await get_chat_history()
    assert history == []


# ---------------------------------------------------------------------------
# User isolation
# ---------------------------------------------------------------------------


async def test_history_user_isolation():
    """Messages from different users should not mix."""
    await save_chat_message("user", "Default user msg")
    await save_chat_message("user", "Other user msg", user_id="other")

    default_history = await get_chat_history(user_id="default")
    other_history = await get_chat_history(user_id="other")

    assert len(default_history) == 1
    assert default_history[0]["content"] == "Default user msg"
    assert len(other_history) == 1
    assert other_history[0]["content"] == "Other user msg"
