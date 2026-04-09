---
phase: 03
slug: ai-chat-backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x with pytest-asyncio |
| **Config file** | backend/pyproject.toml |
| **Quick run command** | `cd backend && uv run --extra dev pytest tests/test_chat.py -v` |
| **Full suite command** | `cd backend && uv run --extra dev pytest -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run --extra dev pytest tests/test_chat.py -v`
- **After every plan wave:** Run `cd backend && uv run --extra dev pytest -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | CHAT-01 | T-03-01 | Validate input, return structured JSON | integration | `pytest tests/test_chat.py -k chat_endpoint` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | CHAT-02 | — | Portfolio context included in LLM prompt | integration | `pytest tests/test_chat.py -k context` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | CHAT-03 | — | Chat history loaded (last 20 messages) | integration | `pytest tests/test_chat.py -k history` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | CHAT-04 | T-03-02 | Auto-execute trades from LLM response | integration | `pytest tests/test_chat.py -k auto_execute` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | CHAT-05 | — | Auto-execute watchlist changes | integration | `pytest tests/test_chat.py -k watchlist` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 1 | CHAT-06 | — | Mock mode returns deterministic responses | integration | `pytest tests/test_chat.py -k mock` | ❌ W0 | ⬜ pending |
| 03-01-07 | 01 | 1 | CHAT-07 | T-03-03 | LLM failures return HTTP 200 fallback | integration | `pytest tests/test_chat.py -k fallback` | ❌ W0 | ⬜ pending |
| 03-01-08 | 01 | 1 | CHAT-08 | — | Messages stored in chat_messages table | integration | `pytest tests/test_chat.py -k store` | ❌ W0 | ⬜ pending |
| 03-01-09 | 01 | 1 | CHAT-09 | — | Structured output schema validation | integration | `pytest tests/test_chat.py -k structured` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_chat.py` — stubs for CHAT-01 through CHAT-09
- [ ] Existing conftest.py fixtures from Phase 02 cover DB isolation

*Existing infrastructure covers test framework and fixtures.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
