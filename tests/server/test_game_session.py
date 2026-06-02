import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest
from server.config import GameConfig, SlotConfig
from server.game_session import GameSession


JSONL = Path("data/pokemon.jsonl")


def _config(num_players=2, agent_types=None, delay_ms=0):
    agent_types = agent_types or ["random"] * num_players
    return GameConfig(
        num_players=num_players,
        slots=[SlotConfig(i, t) for i, t in enumerate(agent_types)],
        delay_ms=delay_ms,
    )


def _mock_ws():
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


async def _collect_messages(ws, count: int, session_task) -> list[dict]:
    msgs = []
    async def capture(text):
        msgs.append(json.loads(text))
    ws.send_text.side_effect = capture
    await asyncio.wait_for(session_task, timeout=10.0)
    return msgs


@pytest.mark.asyncio
async def test_session_broadcasts_initial_state():
    session = GameSession(_config(), JSONL)
    ws = _mock_ws()
    session.spectators.append(ws)
    msgs = []
    async def capture(text):
        msgs.append(json.loads(text))
    ws.send_text.side_effect = capture
    task = asyncio.create_task(session.run())
    await asyncio.wait_for(task, timeout=10.0)
    types = [m["type"] for m in msgs]
    assert "state" in types


@pytest.mark.asyncio
async def test_session_ends_with_game_over():
    session = GameSession(_config(delay_ms=0), JSONL)
    ws = _mock_ws()
    session.spectators.append(ws)
    msgs = []
    async def capture(text):
        msgs.append(json.loads(text))
    ws.send_text.side_effect = capture
    task = asyncio.create_task(session.run())
    await asyncio.wait_for(task, timeout=30.0)
    types = [m["type"] for m in msgs]
    assert "game_over" in types


@pytest.mark.asyncio
async def test_claim_slot():
    session = GameSession(_config(), JSONL)
    ws = _mock_ws()
    assert session.claim_slot(0, ws, "Alan") is True
    assert session.slots[0].websocket is ws
    assert session.claim_slot(0, _mock_ws(), "Bob") is False  # already claimed


@pytest.mark.asyncio
async def test_release_slot():
    session = GameSession(_config(), JSONL)
    ws = _mock_ws()
    session.claim_slot(0, ws, "Alan")
    session.release_slot(ws)
    assert session.slots[0].websocket is None


@pytest.mark.asyncio
async def test_lobby_state_structure():
    session = GameSession(_config(), JSONL)
    lobby = session.lobby_state()
    assert lobby["type"] == "lobby"
    assert len(lobby["slots"]) == 2
    assert "join_code" in lobby
    assert "spectators" in lobby
