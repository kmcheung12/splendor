# Web Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the Pokemon Splendor game engine as a real-time multiplayer web app — spectator-first lobby, cinematic animations, human and/or AI players per slot.

**Architecture:** FastAPI server wraps the existing `PokemonSplendorEnv` in a `GameSession` that runs the agent loop as an asyncio task and pushes structured events + state snapshots over WebSocket to all connected browsers. A Svelte SPA renders the board, animates each action via built-in `crossfade`/`fly` transitions, and lets human players interact by clicking board elements directly.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, pytest-asyncio (backend) · Svelte 5, Vite, TypeScript (frontend) · tsParticles (particles, CDN)

**Spec:** `docs/superpowers/specs/2026-06-02-web-interface-design.md`

---

## File Map

**New backend files:**
- `server/__init__.py`
- `server/main.py` — FastAPI app, HTTP routes, WebSocket endpoint
- `server/config.py` — `GameConfig` dataclass
- `server/serializer.py` — `Game → JSON`
- `server/action_events.py` — action int → structured event dict
- `server/agents.py` — agent factory (wraps `_make_agent` logic)
- `server/game_session.py` — `GameSession`: loop, slots, broadcast, human pausing
- `tests/server/__init__.py`
- `tests/server/test_serializer.py`
- `tests/server/test_action_events.py`
- `tests/server/test_game_session.py`

**Modified:**
- `pyproject.toml` — add fastapi, uvicorn, websockets, pytest-asyncio

**New frontend files (all under `frontend/`):**
- `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`
- `src/App.svelte`
- `src/lib/ws.ts` — WebSocket client + event bus
- `src/lib/gameStore.ts` — Svelte writable stores
- `src/lib/animationQueue.ts` — serial animation queue
- `src/lib/types.ts` — shared TypeScript types
- `src/components/Lobby.svelte`
- `src/components/Board.svelte`
- `src/components/CardSlot.svelte`
- `src/components/CardStack.svelte`
- `src/components/PlayerPanel.svelte`
- `src/components/StatusChip.svelte`
- `src/components/ActionMenu.svelte`
- `src/components/GameOver.svelte`

---

## Task 1: Add backend dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add fastapi, uvicorn, websockets, pytest-asyncio to pyproject.toml**

```toml
[project]
name = "pokemon-splendor"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pettingzoo>=1.24.0",
    "gymnasium>=0.29.0",
    "numpy>=1.26.0",
    "stable-baselines3>=2.3.0",
    "sb3-contrib>=2.3.0",
    "torch>=2.2.0",
    "rich>=13.0.0",
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "websockets>=12.0",
]

[project.scripts]
pokemon-splendor = "pokemon_splendor.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[dependency-groups]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0", "httpx>=0.27.0"]
```

- [ ] **Step 2: Install dependencies**

```bash
uv sync
```

Expected: resolves without error, `fastapi`, `uvicorn`, `websockets` appear in `uv.lock`.

- [ ] **Step 3: Create server package and tests/server package**

```bash
mkdir -p server tests/server
touch server/__init__.py tests/server/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock server/__init__.py tests/server/__init__.py
git commit -m "feat: add fastapi/uvicorn/websockets deps and server scaffold"
```

---

## Task 2: GameConfig

**Files:**
- Create: `server/config.py`

- [ ] **Step 1: Write `server/config.py`**

```python
from dataclasses import dataclass, field


@dataclass
class SlotConfig:
    index: int
    agent_type: str  # "random", "mcts", "early-capture", etc.


@dataclass
class GameConfig:
    num_players: int
    slots: list[SlotConfig]
    delay_ms: int = 800

    def __post_init__(self):
        assert 2 <= self.num_players <= 4
        assert len(self.slots) == self.num_players
        assert self.delay_ms >= 0
```

- [ ] **Step 2: Commit**

```bash
git add server/config.py
git commit -m "feat: add GameConfig dataclass"
```

---

## Task 3: Game serializer

**Files:**
- Create: `server/serializer.py`
- Create: `tests/server/test_serializer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/server/test_serializer.py
from pathlib import Path
import pytest
from pokemon_splendor.engine.env import PokemonSplendorEnv
from server.serializer import serialize_game


def _env():
    env = PokemonSplendorEnv(Path("data/pokemon.jsonl"), num_players=2)
    env.reset(seed=42)
    return env


def test_serialize_game_top_level_keys():
    result = serialize_game(_env().game)
    assert set(result.keys()) == {"round", "phase", "turn", "players", "board", "board_tokens"}


def test_board_tokens_all_types():
    result = serialize_game(_env().game)
    assert set(result["board_tokens"].keys()) == {"red", "yellow", "blue", "pink", "black", "master"}
    assert result["board_tokens"]["master"] == 5


def test_board_revealed_slots():
    result = serialize_game(_env().game)
    board = result["board"]
    assert len(board["common_revealed"]) == 4
    assert len(board["uncommon_revealed"]) == 4
    assert len(board["rare_revealed"]) == 4
    assert len(board["epic_revealed"]) == 1
    assert len(board["legendary_revealed"]) == 1


def test_board_deck_counts_positive():
    result = serialize_game(_env().game)
    board = result["board"]
    assert board["common_deck_count"] > 0
    assert board["rare_deck_count"] > 0


def test_player_fields():
    result = serialize_game(_env().game)
    p = result["players"][0]
    assert set(p.keys()) == {"name", "points", "tokens", "cards", "reserved_cards"}
    assert p["points"] == 0
    assert p["tokens"] == {"red": 0, "yellow": 0, "blue": 0, "pink": 0, "black": 0, "master": 0}


def test_serialize_pokemon_fields():
    env = _env()
    board = env.game.board
    card = next(c for c in board.common_revealed if c is not None)
    result = serialize_game(env.game)
    slot = next(c for c in result["board"]["common_revealed"] if c is not None)
    assert set(slot.keys()) == {"name", "tier", "cost", "bonus", "evolve", "evolve_into", "point", "evolved"}
    assert slot["tier"] == "common"
    assert isinstance(slot["cost"], list)


def test_none_slot_serializes_as_none():
    result = serialize_game(_env().game)
    # Some slots may be None (empty); they should serialize as None not raise
    for slot in result["board"]["common_revealed"]:
        assert slot is None or isinstance(slot, dict)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/server/test_serializer.py -v
```

Expected: `ModuleNotFoundError: No module named 'server.serializer'`

- [ ] **Step 3: Write `server/serializer.py`**

```python
from collections import Counter
from pokemon_splendor.models import Game, Player, Board, Pokemon, PokeballType


def _token_counts(tokens) -> dict[str, int]:
    counts = Counter(t.name.value for t in tokens)
    return {pt.value: counts.get(pt.value, 0) for pt in PokeballType}


def _serialize_pokemon(p: Pokemon | None) -> dict | None:
    if p is None:
        return None
    return {
        "name": p.name,
        "tier": p.tier.value,
        "cost": [t.name.value for t in p.cost],
        "bonus": [b.name.value for b in p.bonus],
        "evolve": [b.name.value for b in p.evolve],
        "evolve_into": p.evolve_into,
        "point": p.point,
        "evolved": p.evolved,
    }


def _serialize_player(p: Player) -> dict:
    return {
        "name": p.name,
        "points": p.points,
        "tokens": _token_counts(p.tokens),
        "cards": [_serialize_pokemon(c) for c in p.cards],
        "reserved_cards": [_serialize_pokemon(c) for c in p.reserved_cards],
    }


def _serialize_board(b: Board) -> dict:
    return {
        "common_revealed":   [_serialize_pokemon(p) for p in b.common_revealed],
        "uncommon_revealed": [_serialize_pokemon(p) for p in b.uncommon_revealed],
        "rare_revealed":     [_serialize_pokemon(p) for p in b.rare_revealed],
        "epic_revealed":     [_serialize_pokemon(p) for p in b.epic_revealed],
        "legendary_revealed":[_serialize_pokemon(p) for p in b.legendary_revealed],
        "common_deck_count":   len(b.common_deck),
        "uncommon_deck_count": len(b.uncommon_deck),
        "rare_deck_count":     len(b.rare_deck),
        "epic_deck_count":     len(b.epic_deck),
        "legendary_deck_count":len(b.legendary_deck),
    }


def serialize_game(game: Game) -> dict:
    return {
        "round": game.round,
        "phase": game.phase.value,
        "turn": game.turn.name,
        "players": [_serialize_player(p) for p in game.players],
        "board": _serialize_board(game.board),
        "board_tokens": {pt.value: game.tokens.get(pt, 0) for pt in PokeballType},
    }
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/server/test_serializer.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server/serializer.py tests/server/test_serializer.py
git commit -m "feat: add game serializer (Game → JSON)"
```

---

## Task 4: Action event builder

**Files:**
- Create: `server/action_events.py`
- Create: `tests/server/test_action_events.py`

Action events are emitted *before* the state snapshot so the client can animate what changed. Each event carries enough info for the animator (player, card name, slot index, tier, token types).

- [ ] **Step 1: Write failing tests**

```python
# tests/server/test_action_events.py
from pathlib import Path
import pytest
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.engine.actions import (
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START,
    CATCH_RESERVED_START, RESERVE_MASTER_START, DISCARD_START,
    EVOLVE_START, EVOLVE_PASS,
)
from server.action_events import build_action_event


def _env():
    env = PokemonSplendorEnv(Path("data/pokemon.jsonl"), num_players=2)
    env.reset(seed=42)
    return env


def test_take_diff_tokens():
    env = _env()
    event = build_action_event(env.game, "player_0", TAKE_DIFF_START)  # red only
    assert event["type"] == "take_tokens"
    assert event["player"] == "player_0"
    assert "red" in event["tokens"]


def test_take_same_tokens():
    env = _env()
    event = build_action_event(env.game, "player_0", TAKE_SAME_START)  # 2× red
    assert event["type"] == "take_tokens"
    assert event["tokens"] == ["red", "red"]


def test_catch_board_card():
    env = _env()
    all_slots = (
        env.game.board.common_revealed + env.game.board.uncommon_revealed +
        env.game.board.rare_revealed + env.game.board.epic_revealed +
        env.game.board.legendary_revealed
    )
    slot_idx = next(i for i, c in enumerate(all_slots) if c is not None)
    event = build_action_event(env.game, "player_0", CATCH_BOARD_START + slot_idx)
    assert event["type"] == "catch_card"
    assert event["slot"] == slot_idx
    assert event["card"] == all_slots[slot_idx].name
    assert event["from_reserve"] is False


def test_discard_token():
    env = _env()
    event = build_action_event(env.game, "player_0", DISCARD_START)
    assert event["type"] == "discard_token"
    assert event["token"] == "red"


def test_evolve_pass():
    env = _env()
    event = build_action_event(env.game, "player_0", EVOLVE_PASS)
    assert event["type"] == "pass"


def test_all_events_have_player():
    env = _env()
    for action in [TAKE_DIFF_START, TAKE_SAME_START, DISCARD_START, EVOLVE_PASS]:
        event = build_action_event(env.game, "player_0", action)
        assert event["player"] == "player_0"
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/server/test_action_events.py -v
```

Expected: `ModuleNotFoundError: No module named 'server.action_events'`

- [ ] **Step 3: Write `server/action_events.py`**

```python
from pokemon_splendor.models import Game, PokeballType
from pokemon_splendor.engine.actions import (
    TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START, DISCARD_START,
    EVOLVE_START, EVOLVE_PASS,
)


def build_action_event(game: Game, player_name: str, action: int) -> dict:
    base = {"player": player_name}

    if TAKE_DIFF_START <= action < TAKE_SAME_START:
        combo = TAKE_DIFF_COMBOS[action - TAKE_DIFF_START]
        return {**base, "type": "take_tokens", "tokens": [pt.value for pt in combo]}

    if TAKE_SAME_START <= action < CATCH_BOARD_START:
        pt = NORMAL_TYPES[action - TAKE_SAME_START]
        return {**base, "type": "take_tokens", "tokens": [pt.value, pt.value]}

    if CATCH_BOARD_START <= action < CATCH_RESERVED_START:
        slot_idx = action - CATCH_BOARD_START
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed + game.board.epic_revealed +
            game.board.legendary_revealed
        )
        card = all_slots[slot_idx]
        return {
            **base,
            "type": "catch_card",
            "card": card.name if card else None,
            "slot": slot_idx,
            "tier": card.tier.value if card else None,
            "from_reserve": False,
        }

    if CATCH_RESERVED_START <= action < RESERVE_MASTER_START:
        idx = action - CATCH_RESERVED_START
        player = next(p for p in game.players if p.name == player_name)
        card = player.reserved_cards[idx] if idx < len(player.reserved_cards) else None
        return {
            **base,
            "type": "catch_card",
            "card": card.name if card else None,
            "slot": idx,
            "tier": card.tier.value if card else None,
            "from_reserve": True,
        }

    if RESERVE_MASTER_START <= action < RESERVE_NO_MASTER_START:
        slot_idx = action - RESERVE_MASTER_START
        reservable = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed
        )
        card = reservable[slot_idx] if slot_idx < len(reservable) else None
        return {
            **base,
            "type": "reserve_card",
            "card": card.name if card else None,
            "slot": slot_idx,
            "tier": card.tier.value if card else None,
            "took_master": True,
        }

    if RESERVE_NO_MASTER_START <= action < DISCARD_START:
        slot_idx = action - RESERVE_NO_MASTER_START
        reservable = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed
        )
        card = reservable[slot_idx] if slot_idx < len(reservable) else None
        return {
            **base,
            "type": "reserve_card",
            "card": card.name if card else None,
            "slot": slot_idx,
            "tier": card.tier.value if card else None,
            "took_master": False,
        }

    if DISCARD_START <= action < EVOLVE_START:
        pt = list(PokeballType)[action - DISCARD_START]
        return {**base, "type": "discard_token", "token": pt.value}

    if EVOLVE_START <= action < EVOLVE_PASS:
        player = next(p for p in game.players if p.name == player_name)
        idx = action - EVOLVE_START
        card = player.cards[idx] if idx < len(player.cards) else None
        return {**base, "type": "evolve_card", "card": card.name if card else None, "card_index": idx}

    return {**base, "type": "pass"}
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/server/test_action_events.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server/action_events.py tests/server/test_action_events.py
git commit -m "feat: add action event builder (action int → structured event)"
```

---

## Task 5: Agents factory

**Files:**
- Create: `server/agents.py`

- [ ] **Step 1: Write `server/agents.py`**

Wraps the existing `_make_agent` logic from `__main__.py` into a standalone importable function.

```python
from pokemon_splendor.engine.env import PokemonSplendorEnv


def make_agent(agent_type: str, env: PokemonSplendorEnv, player_name: str,
               mcts_sims: int = 200, mcts_depth: int = 4):
    """Return an agent object with a `.act(obs, mask) -> int` method, or a callable."""
    import numpy as np

    if agent_type == "random":
        class _Random:
            def act(self, obs, mask):
                return int(np.random.choice(np.where(mask)[0]))
        return _Random()

    if agent_type == "early-capture":
        from pokemon_splendor.agents.early_capture import EarlyCaptureAgent
        return EarlyCaptureAgent(env, player_name)

    if agent_type == "high-point":
        from pokemon_splendor.agents.high_point import HighPointCaptureAgent
        return HighPointCaptureAgent(env, player_name)

    if agent_type == "bonus-engine":
        from pokemon_splendor.agents.bonus_engine import BonusEngineAgent
        return BonusEngineAgent(env, player_name)

    if agent_type == "evolution-chain":
        from pokemon_splendor.agents.evolution_chain import EvolutionChainAgent
        return EvolutionChainAgent(env, player_name)

    if agent_type == "denial":
        from pokemon_splendor.agents.denial import DenialAgent
        return DenialAgent(env, player_name)

    if agent_type == "mcts":
        from pokemon_splendor.agents.mcts import MCTSAgent, make_early_capture_policy
        return MCTSAgent(env, player_name, n_simulations=mcts_sims, depth=mcts_depth,
                         opponent_policy=make_early_capture_policy())

    if agent_type.endswith(".zip"):
        from pokemon_splendor.agents.rl import RLAgent
        return RLAgent(agent_type)

    raise ValueError(f"Unknown agent type: {agent_type!r}")
```

- [ ] **Step 2: Commit**

```bash
git add server/agents.py
git commit -m "feat: add server agent factory"
```

---

## Task 6: GameSession

**Files:**
- Create: `server/game_session.py`
- Create: `tests/server/test_game_session.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/server/test_game_session.py
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
    ws.send_text.side_effect = lambda t: msgs.append(json.loads(t))
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
    ws.send_text.side_effect = lambda t: msgs.append(json.loads(t))
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
uv run pytest tests/server/test_game_session.py -v
```

Expected: `ModuleNotFoundError: No module named 'server.game_session'`

- [ ] **Step 3: Write `server/game_session.py`**

```python
import asyncio
import json
import random
import string
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import WebSocket
from pokemon_splendor.engine.env import PokemonSplendorEnv
from server.config import GameConfig
from server.serializer import serialize_game
from server.action_events import build_action_event
from server.agents import make_agent


def _generate_join_code(length: int = 4) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


@dataclass
class Slot:
    index: int
    agent_type: str
    websocket: WebSocket | None = None
    claimed_by: str | None = None


class GameSession:
    def __init__(self, config: GameConfig, jsonl_path: Path):
        self.config = config
        self.jsonl_path = jsonl_path
        self.join_code = _generate_join_code()
        self.slots: list[Slot] = [
            Slot(index=i, agent_type=config.slots[i].agent_type)
            for i in range(config.num_players)
        ]
        self.spectators: list[WebSocket] = []
        self.host_ws: WebSocket | None = None
        self._human_event: asyncio.Event = asyncio.Event()
        self._pending_action: int | None = None

    # ── Slot management ──────────────────────────────────────────────────────

    def claim_slot(self, slot_idx: int, ws: WebSocket, name: str) -> bool:
        slot = self.slots[slot_idx]
        if slot.websocket is not None:
            return False
        slot.websocket = ws
        slot.claimed_by = name
        return True

    def release_slot(self, ws: WebSocket) -> None:
        for slot in self.slots:
            if slot.websocket is ws:
                slot.websocket = None
                slot.claimed_by = None
                return

    def disconnect(self, ws: WebSocket) -> None:
        """Called when a WebSocket disconnects — release any claimed slot."""
        self.release_slot(ws)
        if ws in self.spectators:
            self.spectators.remove(ws)
        if ws is self.host_ws:
            # Promote first available spectator/player as host
            candidates = [s.websocket for s in self.slots if s.websocket and s.websocket is not ws]
            candidates += [w for w in self.spectators if w is not ws]
            self.host_ws = candidates[0] if candidates else None

    def slot_for(self, ws: WebSocket) -> Slot | None:
        return next((s for s in self.slots if s.websocket is ws), None)

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def broadcast(self, msg: dict) -> None:
        text = json.dumps(msg)
        targets: list[WebSocket] = [s.websocket for s in self.slots if s.websocket]
        targets += self.spectators
        if self.host_ws and self.host_ws not in targets:
            targets.append(self.host_ws)
        for ws in targets:
            try:
                await ws.send_text(text)
            except Exception:
                pass

    async def send_to(self, ws: WebSocket, msg: dict) -> None:
        try:
            await ws.send_text(json.dumps(msg))
        except Exception:
            pass

    def lobby_state(self) -> dict:
        return {
            "type": "lobby",
            "join_code": self.join_code,
            "delay_ms": self.config.delay_ms,
            "slots": [
                {"index": s.index, "agent_type": s.agent_type, "claimed_by": s.claimed_by}
                for s in self.slots
            ],
            "spectators": len(self.spectators),
        }

    # ── Human action ──────────────────────────────────────────────────────────

    def receive_action(self, action_id: int) -> None:
        self._pending_action = action_id
        self._human_event.set()

    # ── Game loop ─────────────────────────────────────────────────────────────

    async def run(self) -> None:
        env = PokemonSplendorEnv(self.jsonl_path, num_players=self.config.num_players)
        env.reset()

        # Build agent for each slot (None = human-controlled)
        agents: dict[str, object | None] = {}
        for slot in self.slots:
            name = env.possible_agents[slot.index]
            agents[name] = None if slot.websocket else make_agent(slot.agent_type, env, name)

        await self.broadcast({"type": "state", "game": serialize_game(env.game)})

        for _ in range(100_000):
            if not env.agents:
                break
            agent_name = env.agent_selection
            obs, _, term, trunc, _ = env.last()
            if term or trunc:
                break

            slot = next((s for s in self.slots if env.possible_agents[s.index] == agent_name), None)
            is_human = slot is not None and slot.websocket is not None

            await self.broadcast({"type": "thinking", "player": agent_name})

            if is_human:
                mask = env.action_mask(agent_name)
                valid = [int(i) for i in range(len(mask)) if mask[i]]
                await self.broadcast({"type": "human_turn", "player": agent_name, "valid_actions": valid})
                self._human_event.clear()
                await self._human_event.wait()
                action = self._pending_action
            else:
                agent = agents[agent_name]
                mask = env.action_mask(agent_name)
                action = await asyncio.to_thread(agent.act, obs, mask)
                if self.config.delay_ms > 0:
                    await asyncio.sleep(self.config.delay_ms / 1000)

            await self.broadcast(build_action_event(env.game, agent_name, action))
            env.step(action)
            await self.broadcast({"type": "state", "game": serialize_game(env.game)})

        winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
        await self.broadcast({
            "type": "game_over",
            "winner": winner.name,
            "scores": {p.name: p.points for p in env.game.players},
        })
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/server/test_game_session.py -v
```

Expected: all 5 tests PASS (may take ~10s for game completion tests).

- [ ] **Step 5: Commit**

```bash
git add server/game_session.py tests/server/test_game_session.py
git commit -m "feat: add GameSession with async game loop and human turn pausing"
```

---

## Task 7: FastAPI app + WebSocket endpoint

**Files:**
- Create: `server/main.py`

- [ ] **Step 1: Write `server/main.py`**

```python
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware

from server.config import GameConfig, SlotConfig
from server.game_session import GameSession

DATA_PATH = Path("data/pokemon.jsonl")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: dict[str, GameSession] = {}
_code_to_id: dict[str, str] = {}


@app.post("/game/new")
async def new_game(
    num_players: int = Body(2),
    agent_types: list[str] = Body(["random", "random"]),
    delay_ms: int = Body(800),
):
    assert len(agent_types) == num_players
    game_id = str(uuid.uuid4())[:8]
    config = GameConfig(
        num_players=num_players,
        slots=[SlotConfig(i, t) for i, t in enumerate(agent_types)],
        delay_ms=delay_ms,
    )
    session = GameSession(config, DATA_PATH)
    _sessions[game_id] = session
    _code_to_id[session.join_code] = game_id
    return {"game_id": game_id, "join_code": session.join_code}


@app.get("/join/{code}")
async def join_by_code(code: str):
    game_id = _code_to_id.get(code.upper())
    if not game_id:
        return {"error": "invalid code"}, 404
    return {"game_id": game_id}


@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    session = _sessions.get(game_id)
    if not session:
        await websocket.close(code=4004)
        return

    await websocket.accept()
    is_host = session.host_ws is None
    if is_host:
        session.host_ws = websocket
    else:
        session.spectators.append(websocket)

    # Send current lobby state
    lobby = session.lobby_state()
    lobby["is_host"] = is_host
    await websocket.send_text(__import__("json").dumps(lobby))

    import asyncio, json

    try:
        async for text in websocket.iter_text():
            msg = json.loads(text)
            mtype = msg.get("type")

            if mtype == "claim":
                slot_idx = msg["slot"]
                name = msg.get("name", f"Player{slot_idx+1}")
                ok = session.claim_slot(slot_idx, websocket, name)
                await session.broadcast(session.lobby_state())
                if not ok:
                    await websocket.send_text(json.dumps({"type": "error", "msg": "slot taken"}))

            elif mtype == "release":
                session.release_slot(websocket)
                await session.broadcast(session.lobby_state())

            elif mtype == "config":
                if websocket is session.host_ws:
                    session.config.delay_ms = msg.get("delay_ms", session.config.delay_ms)
                    await session.broadcast(session.lobby_state())

            elif mtype == "start":
                if websocket is session.host_ws:
                    asyncio.create_task(session.run())

            elif mtype == "action":
                slot = session.slot_for(websocket)
                if slot:
                    session.receive_action(int(msg["action_id"]))

    except WebSocketDisconnect:
        pass
    finally:
        session.disconnect(websocket)
        await session.broadcast(session.lobby_state())
        # Clean up empty sessions
        all_gone = (
            session.host_ws is None
            and not session.spectators
            and all(s.websocket is None for s in session.slots)
        )
        if all_gone:
            _sessions.pop(game_id, None)
            _code_to_id.pop(session.join_code, None)
```

- [ ] **Step 2: Smoke-test the server starts**

```bash
uv run uvicorn server.main:app --reload --port 8000
```

Expected: `Uvicorn running on http://127.0.0.1:8000`. Stop with Ctrl-C.

- [ ] **Step 3: Commit**

```bash
git add server/main.py
git commit -m "feat: add FastAPI app with WebSocket endpoint and lobby routes"
```

---

## Task 8: Frontend project scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/App.svelte`
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/main.ts`

- [ ] **Step 1: Scaffold Svelte + Vite project**

```bash
cd frontend && npm create vite@latest . -- --template svelte-ts && npm install
```

Expected: `node_modules/` created, `src/App.svelte` exists.

- [ ] **Step 2: Replace `vite.config.ts` to proxy WebSocket to backend**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/game': 'http://localhost:8000',
      '/join': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
```

- [ ] **Step 3: Create shared TypeScript types**

```typescript
// frontend/src/lib/types.ts

export interface SlotInfo {
  index: number
  agent_type: string
  claimed_by: string | null
}

export interface LobbyState {
  type: 'lobby'
  join_code: string
  delay_ms: number
  slots: SlotInfo[]
  spectators: number
  is_host?: boolean
}

export interface PokemonCard {
  name: string
  tier: string
  cost: string[]
  bonus: string[]
  evolve: string[]
  evolve_into: string
  point: number
  evolved: boolean
}

export interface PlayerState {
  name: string
  points: number
  tokens: Record<string, number>
  cards: PokemonCard[]
  reserved_cards: PokemonCard[]
}

export interface BoardState {
  common_revealed: (PokemonCard | null)[]
  uncommon_revealed: (PokemonCard | null)[]
  rare_revealed: (PokemonCard | null)[]
  epic_revealed: (PokemonCard | null)[]
  legendary_revealed: (PokemonCard | null)[]
  common_deck_count: number
  uncommon_deck_count: number
  rare_deck_count: number
  epic_deck_count: number
  legendary_deck_count: number
}

export interface GameState {
  round: number
  phase: string
  turn: string
  players: PlayerState[]
  board: BoardState
  board_tokens: Record<string, number>
}

export type ActionEvent =
  | { type: 'take_tokens'; player: string; tokens: string[] }
  | { type: 'catch_card'; player: string; card: string | null; slot: number; tier: string | null; from_reserve: boolean }
  | { type: 'reserve_card'; player: string; card: string | null; slot: number; tier: string | null; took_master: boolean }
  | { type: 'discard_token'; player: string; token: string }
  | { type: 'evolve_card'; player: string; card: string | null; card_index: number }
  | { type: 'pass'; player: string }

export type ServerMessage =
  | LobbyState
  | { type: 'state'; game: GameState }
  | ActionEvent
  | { type: 'thinking'; player: string }
  | { type: 'human_turn'; player: string; valid_actions: number[] }
  | { type: 'game_over'; winner: string; scores: Record<string, number> }
  | { type: 'error'; msg: string }
```

- [ ] **Step 4: Create minimal `App.svelte` (will be expanded in later tasks)**

```svelte
<!-- frontend/src/App.svelte -->
<script lang="ts">
  let view: 'setup' | 'lobby' | 'game' = 'setup'
</script>

<main>
  {#if view === 'setup'}
    <p>Setup (coming soon)</p>
  {:else if view === 'lobby'}
    <p>Lobby (coming soon)</p>
  {:else}
    <p>Game (coming soon)</p>
  {/if}
</main>
```

- [ ] **Step 5: Verify dev server starts**

```bash
cd frontend && npm run dev
```

Expected: `Local: http://localhost:5173/`. Stop with Ctrl-C.

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Svelte+Vite frontend with shared TypeScript types"
```

---

## Task 9: WebSocket client + game stores

**Files:**
- Create: `frontend/src/lib/ws.ts`
- Create: `frontend/src/lib/gameStore.ts`
- Create: `frontend/src/lib/animationQueue.ts`

- [ ] **Step 1: Write `frontend/src/lib/gameStore.ts`**

```typescript
// frontend/src/lib/gameStore.ts
import { writable, derived } from 'svelte/store'
import type { GameState, LobbyState, ActionEvent } from './types'

export const gameState = writable<GameState | null>(null)
export const lobbyState = writable<LobbyState | null>(null)
export const mySlot = writable<number | null>(null)         // claimed slot index
export const isHost = writable(false)
export const activePlayer = writable<string | null>(null)   // whose turn
export const thinkingPlayer = writable<string | null>(null) // showing thinking chip
export const humanTurnActions = writable<number[]>([])      // valid action ids when it's our turn
export const pendingActionEvent = writable<ActionEvent | null>(null)
export const gameOver = writable<{ winner: string; scores: Record<string, number> } | null>(null)
export const phase = writable<string>('main')

// Derived: is it currently this browser's turn to act?
export const isMyTurn = derived(
  [activePlayer, mySlot, gameState, humanTurnActions],
  ([$active, $slot, $game, $actions]) => {
    if ($slot === null || !$game || $actions.length === 0) return false
    return $active === $game.players[$slot]?.name
  }
)
```

- [ ] **Step 2: Write `frontend/src/lib/animationQueue.ts`**

```typescript
// frontend/src/lib/animationQueue.ts

type AnimFn = () => Promise<void>

class AnimationQueue {
  private queue: AnimFn[] = []
  private running = false

  enqueue(fn: AnimFn): void {
    this.queue.push(fn)
    if (!this.running) this._drain()
  }

  private async _drain(): Promise<void> {
    this.running = true
    while (this.queue.length > 0) {
      const fn = this.queue.shift()!
      await fn()
    }
    this.running = false
  }
}

export const animQueue = new AnimationQueue()

// Helper: resolve after `ms` milliseconds
export const delay = (ms: number) => new Promise<void>(r => setTimeout(r, ms))
```

- [ ] **Step 3: Write `frontend/src/lib/ws.ts`**

```typescript
// frontend/src/lib/ws.ts
import type { ServerMessage, ActionEvent } from './types'
import {
  gameState, lobbyState, mySlot, isHost,
  activePlayer, thinkingPlayer, humanTurnActions,
  pendingActionEvent, gameOver, phase,
} from './gameStore'
import { animQueue, delay } from './animationQueue'
import { get } from 'svelte/store'

let ws: WebSocket | null = null

export function connect(gameId: string): void {
  ws = new WebSocket(`/ws/${gameId}`)
  ws.onmessage = (e) => handleMessage(JSON.parse(e.data) as ServerMessage)
  ws.onclose = () => { ws = null }
}

export function sendAction(actionId: number): void {
  ws?.send(JSON.stringify({ type: 'action', action_id: actionId }))
}

export function claimSlot(slot: number, name: string): void {
  ws?.send(JSON.stringify({ type: 'claim', slot, name }))
}

export function releaseSlot(): void {
  ws?.send(JSON.stringify({ type: 'release' }))
  mySlot.set(null)
}

export function startGame(): void {
  ws?.send(JSON.stringify({ type: 'start' }))
}

export function setDelay(ms: number): void {
  ws?.send(JSON.stringify({ type: 'config', delay_ms: ms }))
}

function handleMessage(msg: ServerMessage): void {
  switch (msg.type) {
    case 'lobby':
      lobbyState.set(msg)
      if (msg.is_host) isHost.set(true)
      break

    case 'state':
      gameState.set(msg.game)
      activePlayer.set(msg.game.turn)
      phase.set(msg.game.phase)
      thinkingPlayer.set(null)
      humanTurnActions.set([])
      break

    case 'thinking':
      thinkingPlayer.set(msg.player)
      break

    case 'human_turn':
      humanTurnActions.set(msg.valid_actions)
      thinkingPlayer.set(msg.player)
      break

    case 'game_over':
      gameOver.set({ winner: msg.winner, scores: msg.scores })
      break

    case 'take_tokens':
    case 'catch_card':
    case 'reserve_card':
    case 'discard_token':
    case 'evolve_card':
    case 'pass':
      animQueue.enqueue(async () => {
        pendingActionEvent.set(msg as ActionEvent)
        await delay(400)  // animation duration
        pendingActionEvent.set(null)
      })
      break
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat: add WebSocket client, Svelte stores, and animation queue"
```

---

## Task 10: Board component

**Files:**
- Create: `frontend/src/components/Board.svelte`

The board renders the 5×4 card grid and token pool. Token pool shows one coloured circle per token. Deck slots show card back + count badge.

- [ ] **Step 1: Write `frontend/src/components/Board.svelte`**

```svelte
<!-- frontend/src/components/Board.svelte -->
<script lang="ts">
  import { gameState } from '../lib/gameStore'
  import CardSlot from './CardSlot.svelte'
  import type { PokemonCard } from '../lib/types'

  const TOKEN_COLORS: Record<string, string> = {
    red: '#e74c3c', yellow: '#f1c40f', blue: '#3498db',
    pink: '#e91e96', black: '#555', master: '#f39c12',
  }
  const TOKEN_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']

  $: board = $gameState?.board
  $: boardTokens = $gameState?.board_tokens ?? {}

  // Flatten tokens into repeated icon list
  $: tokenIcons = TOKEN_ORDER.flatMap(t =>
    Array(boardTokens[t] ?? 0).fill(t)
  )

  // Grid rows: [deck_count, ...revealed_slots]
  $: rows: Array<{ tier: string; deckCount: number; revealed: (PokemonCard | null)[] }> = board ? [
    { tier: 'legendary', deckCount: board.legendary_deck_count, revealed: board.legendary_revealed },
    { tier: 'epic',      deckCount: board.epic_deck_count,      revealed: board.epic_revealed },
    { tier: 'rare',      deckCount: board.rare_deck_count,      revealed: board.rare_revealed },
    { tier: 'uncommon',  deckCount: board.uncommon_deck_count,  revealed: board.uncommon_revealed },
    { tier: 'common',    deckCount: board.common_deck_count,    revealed: board.common_revealed },
  ] : []
</script>

<div class="board">
  <!-- Token pool -->
  <div class="token-pool">
    {#each tokenIcons as t}
      <span class="token" style="background:{TOKEN_COLORS[t]}" title={t}></span>
    {/each}
  </div>

  <!-- Card grid: rows 1–5 -->
  {#each rows as row, rowIdx}
    <div class="card-row tier-{row.tier}">
      <!-- Column 1: deck back or empty (epic/legendary share row 1) -->
      {#if rowIdx === 0}
        <!-- Row 1 col 1 is empty -->
        <div class="card-cell empty"></div>
      {:else}
        <div class="card-cell deck-back tier-{row.tier}">
          <span class="deck-count">{row.deckCount}</span>
        </div>
      {/if}

      <!-- Revealed slots -->
      {#each row.revealed as card, slotIdx}
        <div class="card-cell">
          <CardSlot {card} tier={row.tier} />
        </div>
      {/each}
    </div>
  {/each}
</div>

<style>
  .board { display: flex; flex-direction: column; gap: 6px; padding: 12px; }

  .token-pool {
    display: flex; flex-wrap: wrap; gap: 4px;
    justify-content: center; padding: 8px 0;
  }

  .token {
    display: inline-block; width: 18px; height: 18px;
    border-radius: 50%; border: 1px solid rgba(0,0,0,.25);
  }

  .card-row {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 6px;
  }

  .card-cell { min-height: 110px; }
  .card-cell.empty {}

  .deck-back {
    border-radius: 8px; display: flex; align-items: center;
    justify-content: center; cursor: default; position: relative;
  }
  .deck-back.tier-common    { background: linear-gradient(135deg,#8B6914,#c9a64a); }
  .deck-back.tier-uncommon  { background: linear-gradient(135deg,#7f8c8d,#bdc3c7); }
  .deck-back.tier-rare      { background: linear-gradient(135deg,#c8a415,#f5d60a); }
  .deck-back.tier-epic      { background: linear-gradient(135deg,#6c3483,#a569bd); }
  .deck-back.tier-legendary { background: linear-gradient(135deg,#154360,#2e86c1,#e74c3c,#f39c12); }

  .deck-count {
    font-size: 1.1rem; font-weight: bold; color: white;
    text-shadow: 0 1px 2px rgba(0,0,0,.6);
  }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Board.svelte
git commit -m "feat: add Board component (5x4 grid + token pool)"
```

---

## Task 11: CardSlot component

**Files:**
- Create: `frontend/src/components/CardSlot.svelte`

Full-detail card with TCG aesthetic: tier-coloured gradient, name, points, cost/bonus/evolve rows.

- [ ] **Step 1: Write `frontend/src/components/CardSlot.svelte`**

```svelte
<!-- frontend/src/components/CardSlot.svelte -->
<script lang="ts">
  import type { PokemonCard } from '../lib/types'

  export let card: PokemonCard | null
  export let tier: string
  export let highlight = false   // glows when it's a valid action target

  const TIER_GRAD: Record<string, string> = {
    common:    'linear-gradient(135deg,#8B6914,#c9a64a)',
    uncommon:  'linear-gradient(135deg,#7f8c8d,#bdc3c7)',
    rare:      'linear-gradient(135deg,#c8a415,#f5d60a)',
    epic:      'linear-gradient(135deg,#6c3483,#a569bd)',
    legendary: 'linear-gradient(135deg,#154360,#2e86c1,#e74c3c,#f39c12)',
  }

  const TOKEN_COLORS: Record<string, string> = {
    red: '#e74c3c', yellow: '#f1c40f', blue: '#3498db',
    pink: '#e91e96', black: '#555', master: '#f39c12',
  }
</script>

{#if card}
  <div
    class="card"
    class:highlight
    style="background:{TIER_GRAD[tier] ?? TIER_GRAD.common}"
    on:click
  >
    <div class="header">
      <span class="name">{card.name}</span>
      <span class="points">{card.point}</span>
    </div>

    <div class="row label">Cost</div>
    <div class="row icons">
      {#each card.cost as t}
        <span class="pip" style="background:{TOKEN_COLORS[t]}"></span>
      {/each}
      {#if card.cost.length === 0}<span class="none">—</span>{/if}
    </div>

    <div class="row label">Bonus</div>
    <div class="row icons">
      {#each card.bonus as b}
        <span class="pip" style="background:{TOKEN_COLORS[b]}"></span>
      {/each}
      {#if card.bonus.length === 0}<span class="none">—</span>{/if}
    </div>

    {#if card.evolve.length > 0}
      <div class="row label">Evolves →</div>
      <div class="row icons">
        <span class="evolve-name">{card.evolve_into}</span>
        {#each card.evolve as b}
          <span class="pip" style="background:{TOKEN_COLORS[b]}"></span>
        {/each}
      </div>
    {/if}
  </div>
{:else}
  <div class="card empty"></div>
{/if}

<style>
  .card {
    border-radius: 8px; padding: 6px 8px; min-height: 100px;
    display: flex; flex-direction: column; gap: 2px;
    box-shadow: 0 2px 4px rgba(0,0,0,.3);
    cursor: pointer; transition: transform .15s, filter .15s;
    user-select: none;
  }
  .card:hover { transform: translateY(-2px); }
  .card.empty { background: rgba(255,255,255,.05); border: 1px dashed rgba(255,255,255,.2); cursor: default; }
  .card.highlight { filter: drop-shadow(0 0 6px #f1c40f); animation: pulse 1s ease-in-out infinite; }

  @keyframes pulse {
    0%, 100% { filter: drop-shadow(0 0 4px #f1c40f); }
    50%       { filter: drop-shadow(0 0 12px #f1c40f); }
  }

  .header { display: flex; justify-content: space-between; align-items: flex-start; }
  .name { font-size: .75rem; font-weight: bold; color: white; text-shadow: 0 1px 2px rgba(0,0,0,.6); flex:1; }
  .points {
    font-size: .9rem; font-weight: bold; color: white;
    background: rgba(0,0,0,.35); border-radius: 50%;
    width: 22px; height: 22px; display: flex; align-items: center; justify-content: center;
  }

  .row.label { font-size: .55rem; color: rgba(255,255,255,.7); text-transform: uppercase; margin-top: 2px; }
  .row.icons { display: flex; flex-wrap: wrap; gap: 2px; }

  .pip { width: 10px; height: 10px; border-radius: 50%; border: 1px solid rgba(255,255,255,.4); }
  .none { font-size: .6rem; color: rgba(255,255,255,.5); }
  .evolve-name { font-size: .6rem; color: rgba(255,255,255,.8); margin-right: 2px; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CardSlot.svelte
git commit -m "feat: add CardSlot component (TCG aesthetic, full detail)"
```

---

## Task 12: CardStack + PlayerPanel

**Files:**
- Create: `frontend/src/components/CardStack.svelte`
- Create: `frontend/src/components/PlayerPanel.svelte`

`CardStack` renders owned cards stacked by bonus colour, showing only the top 1/3 strip. Evolved base cards show face-down behind their evolved form.

- [ ] **Step 1: Write `frontend/src/components/CardStack.svelte`**

```svelte
<!-- frontend/src/components/CardStack.svelte -->
<script lang="ts">
  import type { PokemonCard } from '../lib/types'

  export let cards: PokemonCard[]

  const TOKEN_COLORS: Record<string, string> = {
    red: '#e74c3c', yellow: '#f1c40f', blue: '#3498db',
    pink: '#e91e96', black: '#555', master: '#f39c12',
  }
  const TIER_GRAD: Record<string, string> = {
    common:    'linear-gradient(135deg,#8B6914,#c9a64a)',
    uncommon:  'linear-gradient(135deg,#7f8c8d,#bdc3c7)',
    rare:      'linear-gradient(135deg,#c8a415,#f5d60a)',
    epic:      'linear-gradient(135deg,#6c3483,#a569bd)',
    legendary: 'linear-gradient(135deg,#154360,#2e86c1,#e74c3c,#f39c12)',
  }

  // Group by primary bonus colour (first bonus, or 'none')
  $: groups = (() => {
    const map: Record<string, PokemonCard[]> = {}
    for (const c of cards) {
      const key = c.bonus[0] ?? 'none'
      ;(map[key] ??= []).push(c)
    }
    return Object.entries(map)
  })()
</script>

<div class="card-stacks">
  {#each groups as [color, stack]}
    <div class="stack">
      {#each stack as card, i}
        <div
          class="strip"
          class:face-down={card.evolved}
          style="
            background: {card.evolved ? '#333' : (TIER_GRAD[card.tier] ?? TIER_GRAD.common)};
            top: {i * 18}px;
            z-index: {i};
          "
        >
          {#if !card.evolved}
            <span class="strip-name">{card.name}</span>
            {#if card.evolve_into}
              <span class="strip-arrow">→ {card.evolve_into}</span>
            {/if}
            {#each card.bonus as b}
              <span class="strip-pip" style="background:{TOKEN_COLORS[b]}"></span>
            {/each}
          {/if}
        </div>
      {/each}
    </div>
  {/each}
</div>

<style>
  .card-stacks { display: flex; gap: 8px; flex-wrap: wrap; }

  .stack { position: relative; width: 90px; height: calc(18px * 4 + 32px); }

  .strip {
    position: absolute; left: 0; right: 0; height: 32px;
    border-radius: 6px 6px 0 0; padding: 4px 6px;
    display: flex; align-items: center; gap: 3px;
    box-shadow: 0 2px 3px rgba(0,0,0,.3);
    overflow: hidden;
  }
  .strip.face-down { opacity: .5; }

  .strip-name { font-size: .6rem; font-weight: bold; color: white; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .strip-arrow { font-size: .5rem; color: rgba(255,255,255,.7); white-space: nowrap; }
  .strip-pip { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; border: 1px solid rgba(255,255,255,.4); }
</style>
```

- [ ] **Step 2: Write `frontend/src/components/PlayerPanel.svelte`**

```svelte
<!-- frontend/src/components/PlayerPanel.svelte -->
<script lang="ts">
  import type { PlayerState } from '../lib/types'
  import CardStack from './CardStack.svelte'
  import { activePlayer } from '../lib/gameStore'

  export let player: PlayerState
  export let position: 'top' | 'bottom' | 'left' | 'right' = 'bottom'

  const TOKEN_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']
  const TOKEN_COLORS: Record<string, string> = {
    red: '#e74c3c', yellow: '#f1c40f', blue: '#3498db',
    pink: '#e91e96', black: '#555', master: '#f39c12',
  }

  $: isActive = $activePlayer === player.name
  $: tokenIcons = TOKEN_ORDER.flatMap(t => Array(player.tokens[t] ?? 0).fill(t))
</script>

<div class="panel" class:active={isActive} data-position={position}>
  <div class="identity">
    <span class="pname">{player.name}</span>
    <span class="pts">{player.points} pts</span>
  </div>

  <div class="tokens">
    {#each tokenIcons as t}
      <span class="tok" style="background:{TOKEN_COLORS[t]}" title={t}></span>
    {/each}
    {#if tokenIcons.length === 0}<span class="none">no tokens</span>{/if}
  </div>

  <CardStack cards={player.cards} />

  {#if player.reserved_cards.length > 0}
    <div class="reserved-label">Reserved</div>
    <CardStack cards={player.reserved_cards} />
  {/if}
</div>

<style>
  .panel {
    display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
    padding: 8px 12px; border-radius: 10px;
    background: rgba(255,255,255,.06); border: 2px solid transparent;
    transition: border-color .3s, box-shadow .3s;
  }
  .panel.active {
    border-color: #f1c40f;
    box-shadow: 0 0 12px rgba(241,196,15,.4);
  }
  .identity { display: flex; flex-direction: column; gap: 2px; min-width: 70px; }
  .pname { font-weight: bold; color: white; font-size: .85rem; }
  .pts { font-size: 1.1rem; font-weight: bold; color: #f1c40f; }
  .tokens { display: flex; flex-wrap: wrap; gap: 3px; }
  .tok { width: 14px; height: 14px; border-radius: 50%; border: 1px solid rgba(255,255,255,.3); }
  .none { font-size: .7rem; color: rgba(255,255,255,.4); }
  .reserved-label { font-size: .6rem; color: rgba(255,255,255,.5); width: 100%; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CardStack.svelte frontend/src/components/PlayerPanel.svelte
git commit -m "feat: add CardStack and PlayerPanel components"
```

---

## Task 13: StatusChip

**Files:**
- Create: `frontend/src/components/StatusChip.svelte`

- [ ] **Step 1: Write `frontend/src/components/StatusChip.svelte`**

```svelte
<!-- frontend/src/components/StatusChip.svelte -->
<script lang="ts">
  import { thinkingPlayer, activePlayer, phase, gameState } from '../lib/gameStore'

  $: displayName = $thinkingPlayer ?? $activePlayer ?? '…'
  $: isThinking = !!$thinkingPlayer
  $: label = isThinking ? `${displayName} — thinking…` : `▶ ${displayName} — ${$phase}`
</script>

<div class="chip" class:thinking={isThinking}>
  {#if isThinking}
    <span class="spinner">⟳</span>
  {/if}
  {label}
</div>

<style>
  .chip {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 12px; border-radius: 20px;
    background: rgba(0,0,0,.5); color: white;
    font-size: .8rem; font-weight: 500;
    border: 1px solid rgba(255,255,255,.15);
    transition: background .3s;
  }
  .chip.thinking { background: rgba(52,73,94,.8); }

  .spinner {
    display: inline-block;
    animation: spin 1s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/StatusChip.svelte
git commit -m "feat: add StatusChip component (turn/thinking indicator)"
```

---

## Task 14: Animations (crossfade + fly)

This task wires Svelte's `crossfade` and `fly` into `Board.svelte` and `PlayerPanel.svelte` so tokens and cards animate when state updates.

**Files:**
- Modify: `frontend/src/lib/gameStore.ts` — add keyed token store for crossfade
- Modify: `frontend/src/components/Board.svelte` — add crossfade keys + fly on cards
- Modify: `frontend/src/components/PlayerPanel.svelte` — add crossfade receive on tokens

- [ ] **Step 1: Add crossfade transition pair to `gameStore.ts`**

Append to the bottom of `frontend/src/lib/gameStore.ts`:

```typescript
import { crossfade } from 'svelte/transition'
import { quintOut } from 'svelte/easing'

export const [sendToken, receiveToken] = crossfade({
  duration: 450,
  easing: quintOut,
  fallback(node) {
    return { duration: 300, css: (t) => `opacity:${t}` }
  },
})
```

- [ ] **Step 2: Update token rendering in `Board.svelte` to use `sendToken`**

In `Board.svelte`, update the token pool template. Replace:

```svelte
    {#each tokenIcons as t}
      <span class="token" style="background:{TOKEN_COLORS[t]}" title={t}></span>
    {/each}
```

With:

```svelte
    {#each tokenIcons as t, i (t + '-board-' + i)}
      <span
        class="token"
        style="background:{TOKEN_COLORS[t]}"
        title={t}
        use:sendToken={{ key: t + '-' + i }}
      ></span>
    {/each}
```

Also add the import at the top of the `<script>`:

```typescript
  import { sendToken } from '../lib/gameStore'
```

- [ ] **Step 3: Update token rendering in `PlayerPanel.svelte` to use `receiveToken`**

In `PlayerPanel.svelte`, replace:

```svelte
    {#each tokenIcons as t}
      <span class="tok" style="background:{TOKEN_COLORS[t]}" title={t}></span>
    {/each}
```

With:

```svelte
    {#each tokenIcons as t, i (t + '-player-' + i)}
      <span
        class="tok"
        style="background:{TOKEN_COLORS[t]}"
        title={t}
        use:receiveToken={{ key: t + '-' + i }}
      ></span>
    {/each}
```

Add import:

```typescript
  import { receiveToken } from '../lib/gameStore'
```

- [ ] **Step 4: Add `fly` transition to card slots in `Board.svelte`**

In `Board.svelte`, update the card cells in the `{#each row.revealed}` loop. Replace:

```svelte
      {#each row.revealed as card, slotIdx}
        <div class="card-cell">
          <CardSlot {card} tier={row.tier} />
        </div>
      {/each}
```

With:

```svelte
      {#each row.revealed as card, slotIdx (card?.name ?? `empty-${row.tier}-${slotIdx}`)}
        <div class="card-cell" in:fly={{ y: -30, duration: 400 }}>
          <CardSlot {card} tier={row.tier} />
        </div>
      {/each}
```

Add import:

```typescript
  import { fly } from 'svelte/transition'
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/gameStore.ts frontend/src/components/Board.svelte frontend/src/components/PlayerPanel.svelte
git commit -m "feat: add crossfade token animations and fly card transitions"
```

---

## Task 15: ActionMenu (click-to-act)

**Files:**
- Create: `frontend/src/components/ActionMenu.svelte`
- Modify: `frontend/src/components/Board.svelte` — pass highlight props + emit click events
- Modify: `frontend/src/components/CardSlot.svelte` — emit click when highlighted

When it's the human player's turn, valid cards glow and valid token piles pulse. Clicking a target opens a confirm popup. Cancel dismisses it.

- [ ] **Step 1: Write `frontend/src/components/ActionMenu.svelte`**

```svelte
<!-- frontend/src/components/ActionMenu.svelte -->
<script lang="ts">
  import { humanTurnActions, isMyTurn, gameState } from '../lib/gameStore'
  import { sendAction } from '../lib/ws'
  import { createEventDispatcher } from 'svelte'
  import { fly } from 'svelte/transition'

  export let anchorX = 0
  export let anchorY = 0
  export let actions: number[] = []   // subset of valid actions for this target
  export let labels: string[] = []    // human-readable label per action

  const dispatch = createEventDispatcher<{ cancel: void }>()

  function confirm(actionId: number) {
    sendAction(actionId)
    dispatch('cancel')
  }
</script>

{#if actions.length > 0}
  <div
    class="popup"
    style="left:{anchorX}px; top:{anchorY}px"
    transition:fly={{ y: -8, duration: 150 }}
  >
    {#each actions as id, i}
      <button class="action-btn" on:click={() => confirm(id)}>{labels[i] ?? id}</button>
    {/each}
    <button class="cancel-btn" on:click={() => dispatch('cancel')}>Cancel</button>
  </div>
{/if}

<style>
  .popup {
    position: fixed; z-index: 100;
    background: #1a1a2e; border: 1px solid rgba(255,255,255,.2);
    border-radius: 8px; padding: 8px;
    display: flex; flex-direction: column; gap: 4px;
    box-shadow: 0 4px 20px rgba(0,0,0,.6);
    min-width: 160px;
  }
  .action-btn, .cancel-btn {
    padding: 6px 10px; border-radius: 5px; border: none; cursor: pointer;
    font-size: .8rem; text-align: left;
  }
  .action-btn { background: rgba(255,255,255,.1); color: white; }
  .action-btn:hover { background: rgba(241,196,15,.3); }
  .cancel-btn { background: rgba(231,76,60,.15); color: #e74c3c; margin-top: 4px; }
  .cancel-btn:hover { background: rgba(231,76,60,.3); }
</style>
```

- [ ] **Step 2: Wire highlight + confirm into `Board.svelte`**

Add to the `<script>` block in `Board.svelte`:

```typescript
  import { humanTurnActions, isMyTurn, gameState } from '../lib/gameStore'
  import ActionMenu from './ActionMenu.svelte'

  let popup: { x: number; y: number; actions: number[]; labels: string[] } | null = null

  function handleCardClick(e: MouseEvent, slotIdx: number, tier: string) {
    if (!$isMyTurn) return
    // Find valid actions for this board slot
    const CATCH_BOARD_START = 30
    const RESERVE_MASTER_START = 47
    const RESERVE_NO_MASTER_START = 59

    // Map tier rows to absolute slot index
    const tierOffsets: Record<string, number> = {
      common: 0, uncommon: 4, rare: 8, epic: 12, legendary: 13,
    }
    const absSlot = (tierOffsets[tier] ?? 0) + slotIdx

    const catchAction = CATCH_BOARD_START + absSlot
    const reserveMaster = RESERVE_MASTER_START + absSlot
    const reserveNoMaster = RESERVE_NO_MASTER_START + absSlot

    const valid = $humanTurnActions
    const relevant = [catchAction, reserveMaster, reserveNoMaster].filter(a => valid.includes(a))
    if (relevant.length === 0) return

    const labels = relevant.map(a => actionLabel(a))
    const rect = (e.target as HTMLElement).getBoundingClientRect()
    popup = { x: rect.left, y: rect.bottom + 4, actions: relevant, labels }
  }

  function handleTokenClick(e: MouseEvent, tokenType: string) {
    if (!$isMyTurn) return
    const TAKE_DIFF_COMBOS = [
      ['red'],['yellow'],['blue'],['pink'],['black'],
      ['red','yellow'],['red','blue'],['red','pink'],['red','black'],
      ['yellow','blue'],['yellow','pink'],['yellow','black'],
      ['blue','pink'],['blue','black'],['pink','black'],
      ['red','yellow','blue'],['red','yellow','pink'],['red','yellow','black'],
      ['red','blue','pink'],['red','blue','black'],['red','pink','black'],
      ['yellow','blue','pink'],['yellow','blue','black'],['yellow','pink','black'],
      ['blue','pink','black'],
    ]
    const TAKE_SAME_TYPES = ['red','yellow','blue','pink','black']
    const valid = $humanTurnActions

    // Single-colour combos
    const singleIdx = TAKE_DIFF_COMBOS.findIndex(c => c.length === 1 && c[0] === tokenType)
    const sameIdx = TAKE_SAME_TYPES.indexOf(tokenType)

    const relevant: number[] = []
    if (singleIdx >= 0 && valid.includes(singleIdx)) relevant.push(singleIdx)
    if (sameIdx >= 0 && valid.includes(25 + sameIdx)) relevant.push(25 + sameIdx)

    if (relevant.length === 0) return
    const labels = relevant.map(a => actionLabel(a))
    const rect = (e.target as HTMLElement).getBoundingClientRect()
    popup = { x: rect.left, y: rect.bottom + 4, actions: relevant, labels }
  }

  function actionLabel(actionId: number): string {
    // Brief description for confirm popup
    if (actionId >= 30 && actionId < 44) return 'Catch'
    if (actionId >= 44 && actionId < 47) return 'Catch (reserved)'
    if (actionId >= 47 && actionId < 59) return 'Reserve + Master ball'
    if (actionId >= 59 && actionId < 71) return 'Reserve'
    if (actionId >= 0  && actionId < 25) return 'Take tokens'
    if (actionId >= 25 && actionId < 30) return 'Take 2×'
    return 'Action'
  }
```

Add `ActionMenu` and popup dismissal to the template. After the grid closing tag, add:

```svelte
{#if popup}
  <ActionMenu
    anchorX={popup.x} anchorY={popup.y}
    actions={popup.actions} labels={popup.labels}
    on:cancel={() => popup = null}
  />
{/if}
```

Update the `handleCardClick` call in the card cell loop:

```svelte
      {#each row.revealed as card, slotIdx (card?.name ?? `empty-${row.tier}-${slotIdx}`)}
        <div class="card-cell" in:fly={{ y: -30, duration: 400 }}>
          <CardSlot
            {card} tier={row.tier}
            highlight={$isMyTurn && card !== null}
            on:click={(e) => handleCardClick(e, slotIdx, row.tier)}
          />
        </div>
      {/each}
```

Update the token pool loop for token click handling:

```svelte
    {#each tokenIcons as t, i (t + '-board-' + i)}
      <span
        class="token"
        class:pulse={$isMyTurn}
        style="background:{TOKEN_COLORS[t]}"
        title={t}
        use:sendToken={{ key: t + '-' + i }}
        on:click={(e) => handleTokenClick(e, t)}
      ></span>
    {/each}
```

Add `.token.pulse` to Board styles:

```css
  .token.pulse { cursor: pointer; animation: tok-pulse 1.2s ease-in-out infinite; }
  @keyframes tok-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,255,255,.4); }
    50%       { box-shadow: 0 0 0 5px rgba(255,255,255,0); }
  }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ActionMenu.svelte frontend/src/components/Board.svelte
git commit -m "feat: add click-to-act action menu with confirm/cancel"
```

---

## Task 16: Lobby screen

**Files:**
- Create: `frontend/src/components/Lobby.svelte`
- Modify: `frontend/src/App.svelte`

- [ ] **Step 1: Write `frontend/src/components/Lobby.svelte`**

```svelte
<!-- frontend/src/components/Lobby.svelte -->
<script lang="ts">
  import { lobbyState, mySlot, isHost } from '../lib/gameStore'
  import { claimSlot, releaseSlot, startGame, setDelay } from '../lib/ws'
  import { createEventDispatcher } from 'svelte'

  const dispatch = createEventDispatcher<{ started: void }>()

  let playerName = 'Player'

  function claim(idx: number) {
    claimSlot(idx, playerName)
    mySlot.set(idx)
  }
  function release() {
    releaseSlot()
  }
  function handleStart() {
    startGame()
    dispatch('started')
  }
</script>

{#if $lobbyState}
  <div class="lobby">
    <h2>Game: <span class="code">{$lobbyState.join_code}</span></h2>
    <p>Share this code with friends to join.</p>

    <label class="name-row">
      Your name: <input bind:value={playerName} maxlength={16} />
    </label>

    <div class="slots">
      {#each $lobbyState.slots as slot}
        <div class="slot" class:claimed={slot.claimed_by !== null}>
          <span class="slot-idx">Slot {slot.index + 1}</span>
          <span class="agent">default: {slot.agent_type}</span>
          {#if slot.claimed_by}
            <span class="claimer">{slot.claimed_by}</span>
            {#if $mySlot === slot.index}
              <button on:click={release}>Release</button>
            {/if}
          {:else}
            <button on:click={() => claim(slot.index)} disabled={$mySlot !== null}>Claim</button>
          {/if}
        </div>
      {/each}
    </div>

    <label class="delay-row">
      Turn delay: {$lobbyState.delay_ms}ms
      <input type="range" min="0" max="3000" step="100"
        value={$lobbyState.delay_ms}
        on:input={(e) => setDelay(+(e.target as HTMLInputElement).value)}
        disabled={!$isHost}
      />
    </label>

    <div class="footer">
      <span class="spectators">{$lobbyState.spectators} spectator(s)</span>
      {#if $isHost}
        <button class="start-btn" on:click={handleStart}>Start Game</button>
      {/if}
    </div>
  </div>
{/if}

<style>
  .lobby { max-width: 480px; margin: 60px auto; padding: 24px; background: rgba(255,255,255,.07); border-radius: 12px; color: white; }
  h2 { margin-bottom: 4px; }
  .code { font-family: monospace; font-size: 1.4rem; color: #f1c40f; letter-spacing: .15em; }
  .name-row { display: flex; gap: 8px; align-items: center; margin: 12px 0; }
  .name-row input { background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2); border-radius: 4px; color: white; padding: 4px 8px; }
  .slots { display: flex; flex-direction: column; gap: 6px; margin: 16px 0; }
  .slot { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: rgba(255,255,255,.05); border-radius: 8px; }
  .slot.claimed { background: rgba(241,196,15,.1); }
  .slot-idx { font-weight: bold; min-width: 50px; }
  .agent { color: rgba(255,255,255,.5); font-size: .8rem; flex: 1; }
  .claimer { color: #2ecc71; font-size: .85rem; }
  button { background: rgba(255,255,255,.1); color: white; border: 1px solid rgba(255,255,255,.2); border-radius: 5px; padding: 4px 10px; cursor: pointer; }
  button:hover { background: rgba(255,255,255,.2); }
  button:disabled { opacity: .4; cursor: not-allowed; }
  .delay-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .delay-row input { flex: 1; }
  .footer { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; }
  .spectators { color: rgba(255,255,255,.5); font-size: .8rem; }
  .start-btn { background: #27ae60; border-color: #27ae60; font-weight: bold; padding: 8px 20px; }
  .start-btn:hover { background: #2ecc71; }
</style>
```

- [ ] **Step 2: Rewrite `frontend/src/App.svelte` to wire everything together**

```svelte
<!-- frontend/src/App.svelte -->
<script lang="ts">
  import { onMount } from 'svelte'
  import { connect } from './lib/ws'
  import { gameState, lobbyState, isHost, gameOver } from './lib/gameStore'
  import Lobby from './components/Lobby.svelte'
  import Board from './components/Board.svelte'
  import PlayerPanel from './components/PlayerPanel.svelte'
  import StatusChip from './components/StatusChip.svelte'
  import GameOver from './components/GameOver.svelte'

  let view: 'setup' | 'lobby' | 'game' = 'setup'
  let gameId = ''

  // Setup form state
  let numPlayers = 2
  let agentTypes = ['random', 'random', 'random', 'random']
  let delayMs = 800

  const AGENT_OPTIONS = ['random', 'early-capture', 'high-point', 'bonus-engine', 'evolution-chain', 'denial', 'mcts']

  async function createGame() {
    const res = await fetch('/game/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        num_players: numPlayers,
        agent_types: agentTypes.slice(0, numPlayers),
        delay_ms: delayMs,
      }),
    })
    const data = await res.json()
    gameId = data.game_id
    connect(gameId)
    view = 'lobby'
  }

  async function joinGame(code: string) {
    const res = await fetch(`/join/${code}`)
    const data = await res.json()
    if (data.game_id) {
      gameId = data.game_id
      connect(gameId)
      view = 'lobby'
    }
  }

  let joinCode = ''
</script>

<div class="app">
  {#if view === 'setup'}
    <div class="setup">
      <h1>Pokemon Splendor</h1>

      <section>
        <h2>Create Game</h2>
        <label>Players: <input type="number" min="2" max="4" bind:value={numPlayers} /></label>
        {#each Array(numPlayers) as _, i}
          <label>Slot {i+1}:
            <select bind:value={agentTypes[i]}>
              {#each AGENT_OPTIONS as opt}<option>{opt}</option>{/each}
            </select>
          </label>
        {/each}
        <label>Delay (ms): <input type="number" min="0" max="3000" step="100" bind:value={delayMs} /></label>
        <button on:click={createGame}>Create & Host</button>
      </section>

      <section>
        <h2>Join Game</h2>
        <input placeholder="Join code" bind:value={joinCode} maxlength={4} style="text-transform:uppercase" />
        <button on:click={() => joinGame(joinCode)}>Join</button>
      </section>
    </div>

  {:else if view === 'lobby'}
    <Lobby on:started={() => { view = 'game' }} />

  {:else if view === 'game'}
    {#if $gameState}
      <div class="game-layout">
        <!-- Top player(s) -->
        {#each $gameState.players.slice(0, Math.floor($gameState.players.length / 2)) as player}
          <PlayerPanel {player} position="top" />
        {/each}

        <div class="center">
          <StatusChip />
          <Board />
        </div>

        <!-- Bottom player(s) -->
        {#each $gameState.players.slice(Math.floor($gameState.players.length / 2)) as player}
          <PlayerPanel {player} position="bottom" />
        {/each}
      </div>
    {/if}

    {#if $gameOver}
      <GameOver winner={$gameOver.winner} scores={$gameOver.scores} />
    {/if}
  {/if}
</div>

<style>
  :global(body) { margin: 0; background: #0d0d1a; font-family: sans-serif; }

  .app { min-height: 100vh; color: white; }

  .setup {
    max-width: 400px; margin: 60px auto; padding: 24px;
    background: rgba(255,255,255,.07); border-radius: 12px;
    display: flex; flex-direction: column; gap: 24px;
  }
  h1 { text-align: center; color: #f1c40f; }
  section { display: flex; flex-direction: column; gap: 8px; }
  label { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-size: .9rem; }
  input, select { background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2); border-radius: 4px; color: white; padding: 4px 8px; }
  button { background: #27ae60; color: white; border: none; border-radius: 6px; padding: 8px 16px; cursor: pointer; font-size: .9rem; }
  button:hover { background: #2ecc71; }

  .game-layout {
    display: flex; flex-direction: column;
    min-height: 100vh; padding: 8px; gap: 8px;
  }
  .center { display: flex; flex-direction: column; align-items: center; gap: 8px; flex: 1; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Lobby.svelte frontend/src/App.svelte
git commit -m "feat: add Lobby screen and wire App.svelte navigation"
```

---

## Task 17: Game over banner + confetti

**Files:**
- Create: `frontend/src/components/GameOver.svelte`
- Modify: `frontend/index.html` — add tsParticles CDN script

- [ ] **Step 1: Add tsParticles to `frontend/index.html`**

In `frontend/index.html`, add before `</body>`:

```html
<script src="https://cdn.jsdelivr.net/npm/tsparticles-confetti@2/tsparticles.confetti.bundle.min.js"></script>
```

- [ ] **Step 2: Write `frontend/src/components/GameOver.svelte`**

```svelte
<!-- frontend/src/components/GameOver.svelte -->
<script lang="ts">
  import { fly } from 'svelte/transition'
  import { onMount } from 'svelte'

  export let winner: string
  export let scores: Record<string, number>

  onMount(() => {
    // Fire confetti burst — tsParticles loaded via CDN
    const fn = (window as any).confetti
    if (fn) {
      fn({ particleCount: 120, spread: 80, origin: { y: 0.7 } })
      setTimeout(() => fn({ particleCount: 80, spread: 60, origin: { y: 0.6 } }), 400)
    }
  })
</script>

<div class="overlay" transition:fly={{ y: -40, duration: 400 }}>
  <div class="banner">
    <span class="crown">👑</span>
    <h2>{winner} wins!</h2>
    <div class="scores">
      {#each Object.entries(scores).sort((a,b) => b[1]-a[1]) as [name, pts]}
        <div class="score-row" class:winner={name === winner}>
          <span>{name}</span><span>{pts} pts</span>
        </div>
      {/each}
    </div>
    <button on:click={() => location.reload()}>New Game</button>
  </div>
</div>

<style>
  .overlay {
    position: fixed; top: 0; left: 0; right: 0;
    display: flex; justify-content: center;
    z-index: 200; pointer-events: none;
  }
  .banner {
    pointer-events: all;
    margin-top: 24px; padding: 20px 32px;
    background: rgba(10,10,30,.95); border: 1px solid rgba(241,196,15,.4);
    border-radius: 12px; text-align: center; color: white;
    box-shadow: 0 8px 32px rgba(0,0,0,.6);
    min-width: 240px;
  }
  .crown { font-size: 2rem; }
  h2 { margin: 8px 0; color: #f1c40f; font-size: 1.4rem; }
  .scores { margin: 12px 0; display: flex; flex-direction: column; gap: 4px; }
  .score-row { display: flex; justify-content: space-between; gap: 24px; font-size: .9rem; }
  .score-row.winner { color: #f1c40f; font-weight: bold; }
  button { background: #27ae60; color: white; border: none; border-radius: 6px; padding: 8px 20px; cursor: pointer; margin-top: 8px; }
  button:hover { background: #2ecc71; }
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/GameOver.svelte frontend/index.html
git commit -m "feat: add game-over banner with confetti"
```

---

## Task 18: End-to-end smoke test

- [ ] **Step 1: Start the backend**

```bash
uv run uvicorn server.main:app --reload --port 8000
```

- [ ] **Step 2: Start the frontend (separate terminal)**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Open http://localhost:5173 and create a 2-player random vs random game**

Expected: setup form shows, click "Create & Host" → lobby screen shows join code.

- [ ] **Step 4: Click "Start Game"**

Expected: game view appears, board renders, status chip cycles through players, cards animate in, game concludes with game-over banner and confetti.

- [ ] **Step 5: Open a second browser tab, enter the join code, claim a slot, start game**

Expected: both tabs show the same board state; on the human player's turn, valid cards glow and clicking one opens the confirm popup; opponent (AI) moves show animations.

- [ ] **Step 6: Run all backend tests**

```bash
uv run pytest tests/ -v
```

Expected: all tests PASS.
