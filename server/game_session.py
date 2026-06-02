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

            # If this was a human slot but player disconnected, build fallback agent now
            if not is_human and agents[agent_name] is None and slot is not None:
                agents[agent_name] = make_agent(slot.agent_type, env, agent_name)

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
