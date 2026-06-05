import uuid
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, HTTPException
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
        raise HTTPException(status_code=404, detail="invalid code")
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
    await websocket.send_text(json.dumps(lobby))

    import asyncio

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
