# Web Interface Design — Pokemon Splendor

## Overview

Expose the Pokemon Splendor game engine via a real-time web interface. Supports human vs agent, agent vs agent (spectator), and mixed multiplayer games. Built on FastAPI + WebSockets (Python backend) and Svelte (frontend), with cinematic animations for each game action.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Browser (Svelte SPA)                                │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────┐ │
│  │ BoardView│  │PlayerPanels│  │ ActionOverlay    │ │
│  │ (cards,  │  │(tokens,    │  │(human input menu)│ │
│  │  tokens) │  │ hand, pts) │  └──────────────────┘ │
│  └──────────┘  └────────────┘                        │
│       ↑ Svelte stores + crossfade/fly transitions    │
│  WebSocket client (ws.ts + gameStore.ts)             │
└───────┼──────────────────────────────────────────────┘
        │ ws://localhost:8000/ws/{game_id}
┌───────┼──────────────────────────────────────────────┐
│  FastAPI server                                      │
│  ┌─────────────────────────────────────────────────┐ │
│  │ GameSession                                     │ │
│  │  - PokemonSplendorEnv                           │ │
│  │  - agent loop (asyncio task)                    │ │
│  │  - slot map {slot_idx: websocket | agent}       │ │
│  │  - spectator broadcast list                     │ │
│  └─────────────────────────────────────────────────┘ │
│  POST /game/new  →  {game_id, join_code}             │
│  WS  /ws/{game_id}  →  event stream + human input   │
└──────────────────────────────────────────────────────┘
```

The Svelte app is a static build served separately (Vite dev server in dev, `dist/` in prod). FastAPI handles all game logic; the browser is a renderer and input surface. The existing engine, agents, and models are imported directly — no subprocess wrapping.

---

## Lobby & Multiplayer

### Slot model

- The host creates a game and configures: number of players (2–4), a **default agent type per slot**, and turn delay (ms).
- Every browser that opens the join URL (or enters the join code) connects as a **spectator** initially.
- Spectators see the lobby and can **claim** any unclaimed slot to play as human. Claims can be released before the game starts.
- On Start: claimed slots → human-controlled, unclaimed slots → their configured agent type.
- The host can start at any time, including with zero claimed slots (pure agent game with spectators).
- Only the host sees the Start Game button.

### Lobby screen (all connected browsers)

```
Game: XK9F            Delay: [──●──────] 800ms
──────────────────────────────────────────────
Slot 1 │ mcts    │  [Claimed by Alan] [Release]
Slot 2 │ random  │  [Claim]
Slot 3 │ mcts    │  [Claimed by Bob]  [Release]
Slot 4 │ mcts    │  [Claim]
──────────────────────────────────────────────
Spectators: 3                    [Start Game]
```

### Session lifecycle

```
Host browser                    Other browsers
     │                               │
POST /game/new                       │
← {game_id, join_code: "XK9F"}      │
     │                               │
WS /ws/{game_id}?role=host          │
← {type: "lobby", slots: [...]}     │
     │   shares join_code ──────────►│
                              WS /ws/{game_id}
                              ← {type: "lobby", slots: [...]}
                              → {type: "claim", slot: 1}
                              ← {type: "lobby", slots: [...]}  (broadcast)
     │
host → {type: "start"}
← {type: "state", ...}  (broadcast to all)
```

---

## Event Protocol

The server sends two categories of messages over the WebSocket.

### Action events (before state update)

Emitted before the state snapshot so the client can animate the change:

```json
{"type": "take_tokens",  "player": "player_0", "tokens": ["red", "yellow", "blue"]}
{"type": "catch_card",   "player": "player_1", "card": "Bulbasaur", "slot": 3, "tier": "common"}
{"type": "reserve_card", "player": "player_0", "card": "Charizard",  "slot": 2, "tier": "rare"}
{"type": "evolve_card",  "player": "player_1", "card": "Ivysaur"}
{"type": "discard_token","player": "player_0", "token": "red"}
```

Exact fields are finalised during implementation based on what the animator needs.

### State snapshot (after each action)

Full serialised `Game` object sent after every action. The client always converges to this as the ground truth.

```json
{"type": "state", "game": { ...full board + players... }}
```

### Control messages

```json
{"type": "lobby",      "slots": [...], "spectators": 3}
{"type": "human_turn", "player": "player_0", "valid_actions": [...]}
{"type": "game_over",  "winner": "player_1", "scores": {...}}
{"type": "error",      "msg": "invalid action"}
```

### Client → server

```json
{"type": "claim",   "slot": 2}
{"type": "release", "slot": 2}
{"type": "action",  "action_id": 42}
{"type": "start"}
{"type": "config",  "delay_ms": 1200}
```

### Client flow per turn

1. Receive action event → play animation
2. Receive state snapshot → commit to Svelte store
3. If `human_turn.player` matches this browser's claimed slot → show action menu
4. All other browsers show a "waiting for player_N…" indicator

---

## Backend Structure

```
server/
  main.py           # FastAPI app, HTTP routes, WebSocket endpoint
  game_session.py   # GameSession: owns env, agent loop, slot map, broadcast
  serializer.py     # Game → JSON (state snapshots)
  agents.py         # Build agent from type string (wraps existing _make_agent logic)
  config.py         # GameConfig dataclass (num_players, slots, delay_ms)
```

### Key implementation notes

- `GameSession` runs the agent loop as an `asyncio.Task`.
- MCTS and RL agent `act()` calls run via `asyncio.to_thread()` — CPU-bound, must not block the event loop.
- Human turns: loop pauses on an `asyncio.Event`; resolves when the correct slot's WebSocket sends `{"type": "action"}`.
- Sessions stored in `{game_id: GameSession}` dict in memory — no database.
- Join codes are short random uppercase strings (e.g. 4 chars). A `/join/{code}` redirect resolves to the full game URL.

---

## Frontend Structure (Svelte + Vite)

```
frontend/
  src/
    lib/
      ws.ts               # WebSocket connection, event dispatch
      gameStore.ts        # Svelte writable stores for game state
      animationQueue.ts   # Serialises animations so they don't overlap
    components/
      Lobby.svelte         # Waiting room: slot list, claim/release, start
      Board.svelte         # Token pool + 5 tier rows of card slots
      CardSlot.svelte      # Single card (name, cost, bonus, tier badge)
      PlayerPanel.svelte   # Tokens, hand, reserved cards, points
      ActionMenu.svelte    # Human player valid action list (own turn only)
      GameSetup.svelte     # New game config form (host only)
    App.svelte
```

### Animations

- **`crossfade`** (Svelte built-in): shared-element transitions — a token keyed on the board and in the player panel flies between them automatically when store updates.
- **`fly`** (Svelte built-in): cards entering/leaving slots (deal from deck, catch into hand).
- **CSS `filter: drop-shadow` pulse**: highlights affordable cards on a player's turn.
- **`tsParticles`** (one CDN script tag): particle burst on Epic/Legendary catches.

Animation events are serialised through `animationQueue.ts` so concurrent events play sequentially rather than overlapping.

---

## Error Handling & Edge Cases

| Scenario | Handling |
|---|---|
| Human player disconnects mid-game | Slot falls back to its configured agent type |
| Host disconnects | First remaining connected participant is promoted to host |
| Invalid action from human client | Server validates against `action_mask`; responds with `error` event and re-sends `human_turn` |
| MCTS blocking event loop | All agent calls in `asyncio.to_thread()` |
| All connections close | Session removed from memory |
| Spectator joins mid-game | Receives current state snapshot immediately on connect |

---

## Testing

- **Engine** — existing `test_game.py` and `test_agents.py` unchanged.
- **Serializer** — unit tests for `Game → JSON` across all game phases.
- **GameSession integration** — drive session with mock WebSocket objects; assert event sequence (action event before state snapshot, correct `human_turn` routing).
- **Lobby** — claim/release/start flows with multiple mock connections.
- No browser automation tests in scope.

---

## Out of Scope

- Persistent game history or replay
- Authentication / named accounts
- Mobile-optimised layout
- Spectator-only chat
