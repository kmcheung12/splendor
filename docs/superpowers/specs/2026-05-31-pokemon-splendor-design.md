# Pokémon Splendor — Design Spec

**Date:** 2026-05-31  
**Status:** Approved

---

## Overview

A Python CLI implementation of Pokémon Splendor — a Pokémon-themed variant of the board game Splendor. Supports human vs computer play and reinforcement learning training via a PettingZoo AEC environment. Multiple rule-based agents serve as benchmarks and opponents.

---

## Data Model (`models.py`)

```
PokeballType (enum): Red, Yellow, Blue, Pink, Black, Master

PokeballToken:
  name: PokeballType

Bonus(PokeballToken):
  (inherits name)

Tier (enum): Common, Uncommon, Rare, Epic, Legendary

Pokemon:
  name: str
  tier: Tier
  cost: list[PokeballToken]
  bonus: list[Bonus]          # permanent discount given to owner; only active when evolved=False
  evolve: list[Bonus]         # bonus prerequisites required to evolve this card
  evolve_into: str            # name of the Pokémon this card evolves into
  point: int                  # excluded from scoring when evolved=True
  evolved: bool               # True = this card has been evolved into a higher form

Player:
  name: str
  tokens: list[PokeballToken]
  cards: list[Pokemon]        # caught Pokémon (evolved=True cards stay here for chain tracking)
  reserved_cards: list[Pokemon]
  points: int

Board:
  common_deck: list[Pokemon]
  uncommon_deck: list[Pokemon]
  rare_deck: list[Pokemon]
  epic_deck: list[Pokemon]
  legendary_deck: list[Pokemon]
  common_revealed: list[Pokemon]    # 4 slots
  uncommon_revealed: list[Pokemon]  # 4 slots
  rare_revealed: list[Pokemon]      # 4 slots
  epic_revealed: list[Pokemon]      # 1 slot
  legendary_revealed: list[Pokemon] # 1 slot

Game:
  players: list[Player]
  turn: Player
  starting_player: Player
  round: int
  board: Board
  tokens: dict[PokeballType, int]  # pool of available tokens
```

---

## Rules

### Setup
- Starting player chosen at random
- All players start with no tokens or cards
- Board seeded with revealed cards per tier: Common 4, Uncommon 4, Rare 4, Epic 1, Legendary 1
- Remaining cards form face-down decks per tier
- Initial token counts by player count:
  - 2 players: 4 normal tokens per type, 5 Master tokens
  - 3 players: 5 normal tokens per type, 5 Master tokens
  - 4 players: 7 normal tokens per type, 5 Master tokens

### Turn Structure

**Step 1 — Main action (choose exactly one):**

1. **Take different tokens**: take 1, 2, or 3 tokens of different types (no Master). May take fewer than 3 if fewer than 3 types available on the board.
2. **Take 2 same tokens**: take 2 tokens of the same type, only if that type has 4 or more on the board.
3. **Catch a Pokémon**: pay its cost from tokens in hand (bonuses from owned non-evolved cards reduce cost 1-for-1 per type; Master token is wild for any type). Pokémon may come from the board or from the player's reserved cards; catching a reserved card removes it from `reserved_cards`. Epic and Legendary Pokémon require at least one Master token as part of their cost — that Master satisfies the requirement and any remaining cost may be paid with normal tokens or additional Masters as wilds.
4. **Reserve a Pokémon**: take a face-up card from the board (Common, Uncommon, Rare only — Epic and Legendary cannot be reserved) into hand. Optionally take one Master token. Player may reserve without taking the Master token. Max 3 reserved cards.

**Step 2 — Discard (mandatory if over token limit):**  
If the player holds more than 10 tokens after their main action, they discard one token at a time (any type) until at exactly 10.

**Step 3 — Evolve (optional, at most one per turn):**  
If the player owns a Pokémon whose `evolve` bonus requirements are met by their card bonuses whose `evolved` flag is `False`, and a card matching `evolve_into` exists on the revealed board or in their reserved cards, they may take that card for free. The source Pokémon is marked `evolved=True` (excluded from bonus and point calculations). The evolved card is added to the player's collection.

Evolution may happen immediately after catching a Pokémon in the same turn (e.g., catch Charmeleon, then evolve Charmander you already owned).

**Board refill:**  
After a card is caught from the revealed board, it is immediately replaced by the top card of that tier's deck. Empty slots remain empty when the deck is exhausted.

### Win Condition
- When any player reaches 18 points, the current round continues until all players have taken their turn
- Player with the highest points after the round ends wins
- Tiebreak: player with more cards wins

---

## Project Structure

```
splendor/
  src/
    pokemon_splendor/
      models.py       # all dataclasses and enums
      engine/         # PokemonSplendorEnv (PettingZoo AECEnv), action logic, masking
      agents/         # all agent implementations
      data/           # JSONL loader
      cli/            # terminal renderer
      __main__.py     # entry point
  data/
    pokemon.jsonl
  tests/
  pyproject.toml
```

---

## Engine (`engine/`)

### PettingZoo AEC Environment

Implements `pettingzoo.AECEnv`. All game logic lives here.

**Key methods:**
- `reset()` — shuffle decks, seed board, assign starting player
- `step(action: int)` — validate action against mask, apply to game state, advance turn
- `observe(agent: str) -> dict` — return flat observation vector for the agent
- `action_mask(agent: str) -> np.ndarray` — boolean mask of valid actions

### Action Space (71 main actions + post-action)

| Category | Count | Notes |
|---|---|---|
| Take different tokens (1–3 types) | 25 | C(5,1)+C(5,2)+C(5,3); masked by board availability |
| Take 2 same tokens | 5 | Masked when fewer than 4 of that type on board |
| Catch from board | 14 | 4+4+4+1+1 slots |
| Catch from reserved | 3 | Slots 0–2; masked when slot empty |
| Reserve + take Master | 12 | Common+Uncommon+Rare slots; masked when Master count = 0 |
| Reserve without Master | 12 | Same slots; always available when reserving |
| **Total** | **71** | |

**Post-action steps** (each uses its own action mask):
- **Discard**: choose one token type to discard (6 options); repeated until exactly 10 tokens held
- **Evolve**: choose one eligible Pokémon to evolve, or pass

### Observation Space

Flat vector per agent (all cards are visible — no hidden information):
- Board token counts: 6 values
- Revealed cards: 14 slots × 20 values (cost×6, bonus×6, evolve×6, points×1, tier×1)
- Per player (repeated for all players): tokens×6, cards per tier×5, points×1, reserved count×1
- Current player indicator: 1 value

### Rewards
- Sparse: Win `+1`, Lose `-1`, Draw `0`
- Dense (optional, configurable): points delta per turn

---

## Agents (`agents/`)

All agents implement: `act(observation: dict, action_mask: np.ndarray) -> int`

| Agent | Strategy |
|---|---|
| `RandomAgent` | Samples uniformly from valid actions |
| `HumanAgent` | Renders state, reads numbered action from stdin |
| `RLAgent` | Neural network policy (PPO via Stable Baselines3); action masking at logit level |
| `EarlyCaptureAgent` | Prioritizes Pokémon catchable in fewest rounds given tokens, bonuses, board supply. Tiebreak: random |
| `HighPointCaptureAgent` | Prioritizes highest points-per-expected-round ratio. Tiebreak: random |
| `BonusEngineAgent` | Prioritizes low-tier high-bonus cards to build permanent discounts before targeting points |
| `EvolutionChainAgent` | Identifies highest-value evolution chains and works backwards catching prerequisites first |
| `DenialAgent` | Reserves cards opponents are closest to catching, even at personal cost |

---

## Data Layer (`data/loader.py`)

Reads `pokemon.jsonl` line by line. Each line:

```json
{
  "name": "charmander",
  "tier": "common",
  "cost": {"red": 2, "blue": 1},
  "bonus": {"red": 1},
  "evolve": {"red": 2, "blue": 1},
  "evolve_into": "charmeleon",
  "point": 0
}
```

- Fields omitted default to zero/empty
- `evolved` is runtime state, never stored in file
- Multiple cards may share the same name and tier with different costs
- Loader validates required fields and raises on malformed entries
- Returns `list[Pokemon]` shuffled per tier before board seeding

---

## CLI Renderer (`cli/renderer.py`)

Renders each turn:
- Board token counts per type
- Revealed cards per tier (name, cost, bonus, points)
- All players' tokens, caught cards, reserved cards, points
- Current player indicator
- Numbered list of valid actions (for HumanAgent input)

Suppressed during headless training. Enabled with `--render` flag in any mode.

---

## Entry Point (`__main__.py`)

```
# Human vs agents
uv run pokemon-splendor --players human,random,bonus-engine

# RL training headless
uv run pokemon-splendor --mode train --agents rl,rl --episodes 100000 --save model.zip

# RL training with rendering
uv run pokemon-splendor --mode train --agents rl,rl --episodes 100000 --save model.zip --render

# Benchmark agents
uv run pokemon-splendor --mode benchmark --players early-capture,high-point,denial,evolution-chain --games 1000
```

**Modes:**
- `play` (default) — renders every turn, supports HumanAgent
- `train` — trains RL agent, saves model weights; headless unless `--render`
- `benchmark` — runs N games, prints win rates per agent

---

## Testing

Game rules must be thoroughly tested. All tests live in `tests/` and run via `pytest`.

**Unit tests — `tests/test_rules.py`:**
- Token taking: valid 1/2/3 different token combinations; 2-same only when ≥4 available; no Master token allowed
- Token taking: fewer than 3 types taken when board has fewer than 3 available types
- Catch: cost reduced correctly by bonuses (only cards with `evolved=False`); Master token as wild; Epic/Legendary requires Master
- Catch from reserved: card removed from `reserved_cards` on catch
- Reserve: Epic/Legendary cannot be reserved; max 3 reserved enforced; Master token optional on reserve
- Discard: player discards one at a time until exactly 10; triggered only when over 10
- Evolution: `evolve` requirements checked against bonuses of cards with `evolved=False` only; evolved card taken from board or reserved; source card marked `evolved=True`; only one evolution per turn; free (no token cost)
- Evolution timing: can evolve immediately after catching in the same turn
- Board refill: revealed slot replaced from deck on catch; slot left empty when deck exhausted
- Win condition: round completes when 18 points triggered; highest score wins; tiebreak by card count
- Turn order: round-robin from starting player

**Integration tests — `tests/test_game.py`:**
- Full game to completion with RandomAgents: game always terminates, winner always declared
- Action mask correctness: only valid actions unmasked at each game state
- Discard mask: only token types held by player are valid discard options
- Evolve mask: only eligible evolutions shown; pass always available

**Data tests — `tests/test_loader.py`:**
- Valid JSONL loads correctly into `list[Pokemon]`
- Missing optional fields default to zero/empty
- Malformed entries raise clear errors
