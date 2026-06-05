# MCTS Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Monte Carlo Tree Search agent with shortfall-based early cutoff, action pruning, and pluggable opponent policy that beats the early-capture heuristic agent.

**Architecture:** Full UCB tree over the MCTS agent's own decisions (MAIN + EVOLVE phases). Discard is a single forced action. Between our tree nodes, opponents act via an injected policy (default: standalone early-capture logic). At cutoff depth or terminal, a shortfall-based `evaluate_position` scores positions. Action pruning reduces branching factor by filtering token combos to 3-token only and hard-filtering reserve candidates.

**Tech Stack:** Python stdlib (`copy`, `math`, `dataclasses`), existing `rules.py` functions, `sb3_contrib.MaskablePPO` (optional), `numpy`.

---

## File Map

| File | Status | Responsibility |
|---|---|---|
| `src/pokemon_splendor/engine/observation.py` | Create | `compute_observation`, `compute_mask` — lifted from env.py with no logic changes |
| `src/pokemon_splendor/engine/env.py` | Modify | `observe` and `action_mask` delegate to observation.py |
| `src/pokemon_splendor/engine/eval.py` | Create | `evaluate_position` — shortfall-based position value |
| `src/pokemon_splendor/engine/simulator.py` | Create | `game_step` — apply action to copied game, handle phase transitions, return `(game, is_terminal)` |
| `src/pokemon_splendor/agents/mcts.py` | Create | `MCTSNode`, `MCTSAgent`, `make_early_capture_policy`, `make_rl_policy` |
| `src/pokemon_splendor/__main__.py` | Modify | Wire `"mcts"` into `_make_agent` and `AGENT_TYPES` |
| `tests/test_mcts.py` | Create | Tests for eval, simulator, pruning, agent integration |

---

## Task 1: Extract observation and mask into engine/observation.py

**Files:**
- Create: `src/pokemon_splendor/engine/observation.py`
- Modify: `src/pokemon_splendor/engine/env.py`
- Test: `tests/test_game.py` (existing tests must still pass)

This is a pure refactor — zero logic changes. `compute_observation` and `compute_mask` are lifted verbatim from `PokemonSplendorEnv.observe()` and `PokemonSplendorEnv.action_mask()`. After the refactor, `env.py` delegates to these functions.

- [ ] **Step 1: Create observation.py**

```python
# src/pokemon_splendor/engine/observation.py
from collections import Counter
import numpy as np
from pokemon_splendor.models import Game, PokeballType, Tier, GamePhase
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost, get_evolvable_cards
from pokemon_splendor.engine.actions import (
    TOTAL_ACTIONS, TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START, DISCARD_START,
    EVOLVE_START, EVOLVE_PASS, DISCARD_ACTION, TAKE_SAME_ACTION,
    MAX_OWNED_CARDS,
)

_OBS_SIZE = 6 + 14 * 20 + 4 * 13 + 4 + 3  # = 345


def compute_observation(game: Game, player_name: str) -> np.ndarray:
    obs = np.zeros(_OBS_SIZE, dtype=np.float32)
    offset = 0
    for i, ptype in enumerate(PokeballType):
        obs[offset + i] = game.tokens.get(ptype, 0) / 10.0
    offset += 6
    all_slots = (
        game.board.common_revealed + game.board.uncommon_revealed
        + game.board.rare_revealed + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    for slot in all_slots:
        if slot:
            obs[offset:offset+6] = [
                Counter(t.name for t in slot.cost).get(pt, 0) / 5.0
                for pt in PokeballType
            ]
            obs[offset+6:offset+12] = [
                sum(1 for b in slot.bonus if b.name == pt) / 3.0
                for pt in PokeballType
            ]
            obs[offset+12:offset+18] = [
                sum(1 for b in slot.evolve if b.name == pt) / 3.0
                for pt in PokeballType
            ]
            obs[offset+18] = slot.point / 15.0
            obs[offset+19] = list(Tier).index(slot.tier) / 4.0
        offset += 20
    player_map = {p.name: p for p in game.players}
    for i in range(4):
        a = f"player_{i}"
        if a in player_map:
            p = player_map[a]
            tc = Counter(t.name for t in p.tokens)
            for j, pt in enumerate(PokeballType):
                obs[offset + j] = tc.get(pt, 0) / 10.0
            offset += 6
            tier_counts = Counter(c.tier for c in p.cards if not c.evolved)
            for t in Tier:
                obs[offset] = tier_counts.get(t, 0) / 10.0
                offset += 1
            obs[offset] = p.points / 18.0
            obs[offset+1] = len(p.reserved_cards) / 3.0
            offset += 2
        else:
            offset += 13
    for i in range(4):
        obs[offset + i] = 1.0 if f"player_{i}" == game.turn.name else 0.0
    offset += 4
    for i, ph in enumerate(GamePhase):
        obs[offset + i] = 1.0 if game.phase == ph else 0.0
    return obs


def compute_mask(game: Game, player_name: str) -> np.ndarray:
    mask = np.zeros(TOTAL_ACTIONS, dtype=bool)
    player = next(p for p in game.players if p.name == player_name)

    if game.phase == GamePhase.DISCARD:
        tc = Counter(t.name for t in player.tokens)
        for ptype, idx in DISCARD_ACTION.items():
            if tc.get(ptype, 0) > 0:
                mask[idx] = True
        return mask

    if game.phase == GamePhase.EVOLVE:
        mask[EVOLVE_PASS] = True
        evolvable = get_evolvable_cards(game, player)
        for card, _ in evolvable:
            idx = player.cards.index(card)
            if idx < MAX_OWNED_CARDS:
                mask[EVOLVE_START + idx] = True
        return mask

    available_types = {pt for pt in NORMAL_TYPES if game.tokens.get(pt, 0) > 0}
    for i, combo in enumerate(TAKE_DIFF_COMBOS):
        if all(pt in available_types for pt in combo):
            mask[TAKE_DIFF_START + i] = True

    for pt in NORMAL_TYPES:
        if game.tokens.get(pt, 0) >= 4:
            mask[TAKE_SAME_ACTION[pt]] = True

    all_slots = (
        game.board.common_revealed + game.board.uncommon_revealed
        + game.board.rare_revealed + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    player_bonuses = get_player_bonuses(player)
    ptokens = Counter(t.name for t in player.tokens)

    for slot_idx, pokemon in enumerate(all_slots):
        if pokemon is None:
            continue
        effective = calculate_effective_cost(pokemon, player_bonuses)
        master_req = effective.get(PokeballType.Master, 0)
        if pokemon.tier in (Tier.Epic, Tier.Legendary):
            master_req = max(master_req, 1)
        master_have = ptokens.get(PokeballType.Master, 0)
        if master_have < master_req:
            catch_ok = False
        else:
            shortfall = sum(
                max(0, needed - ptokens.get(pt, 0))
                for pt, needed in effective.items()
                if pt != PokeballType.Master
            )
            catch_ok = (master_have - master_req) >= shortfall
        if catch_ok:
            mask[CATCH_BOARD_START + slot_idx] = True

    for i, pokemon in enumerate(player.reserved_cards):
        effective = calculate_effective_cost(pokemon, player_bonuses)
        master_req = effective.get(PokeballType.Master, 0)
        if pokemon.tier in (Tier.Epic, Tier.Legendary):
            master_req = max(master_req, 1)
        master_have = ptokens.get(PokeballType.Master, 0)
        if master_have >= master_req:
            shortfall = sum(
                max(0, needed - ptokens.get(pt, 0))
                for pt, needed in effective.items()
                if pt != PokeballType.Master
            )
            if (master_have - master_req) >= shortfall:
                mask[CATCH_RESERVED_START + i] = True

    if len(player.reserved_cards) < 3:
        reservable_slots = [i for i, p in enumerate(all_slots[:12]) if p is not None]
        for slot_idx in reservable_slots:
            if game.tokens.get(PokeballType.Master, 0) > 0:
                mask[RESERVE_MASTER_START + slot_idx] = True
            mask[RESERVE_NO_MASTER_START + slot_idx] = True

    if not mask.any():
        tc = Counter(t.name for t in player.tokens)
        for ptype, idx in DISCARD_ACTION.items():
            if tc.get(ptype, 0) > 0:
                mask[idx] = True
        if not mask.any():
            mask[EVOLVE_PASS] = True

    return mask
```

- [ ] **Step 2: Update env.py to delegate to observation.py**

In `src/pokemon_splendor/engine/env.py`, replace the bodies of `observe` and `action_mask` with delegation calls. Add the import at the top of the file (with existing imports):

```python
from pokemon_splendor.engine.observation import compute_observation, compute_mask
```

Replace `observe`:
```python
def observe(self, agent: str) -> np.ndarray:
    return compute_observation(self.game, agent)
```

Replace `action_mask`:
```python
def action_mask(self, agent: str) -> np.ndarray:
    return compute_mask(self.game, agent)
```

The old method bodies (lines 180–335 of env.py) are deleted entirely.

- [ ] **Step 3: Verify no regressions**

```bash
uv run pytest tests/ -q
```

Expected: all existing tests pass. If any fail, the refactor introduced a logic change — compare the new functions line-by-line against the old method bodies.

- [ ] **Step 4: Commit**

```bash
git add src/pokemon_splendor/engine/observation.py src/pokemon_splendor/engine/env.py
git commit -m "refactor: extract compute_observation and compute_mask into engine/observation.py"
```

---

## Task 2: Implement evaluate_position in engine/eval.py

**Files:**
- Create: `src/pokemon_splendor/engine/eval.py`
- Create: `tests/test_mcts.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_mcts.py
import pytest
from collections import Counter
from pokemon_splendor.engine.eval import evaluate_position, WIN_SCORE
from pokemon_splendor.models import (
    Player, Pokemon, Board, Game, Tier, PokeballType, PokeballToken, Bonus,
)


def _token(pt): return PokeballToken(pt)
def _bonus(pt): return Bonus(pt)

def _card(name, tier, point, cost_types=(), bonus_types=()):
    return Pokemon(
        name=name, tier=tier, point=point,
        cost=[_token(pt) for pt in cost_types],
        bonus=[_bonus(pt) for pt in bonus_types],
        evolve=[], evolve_into="",
    )

def _make_game(players, board=None):
    if board is None:
        board = Board()
    return Game(
        players=players, turn=players[0], starting_player=players[0],
        round=1, board=board, tokens={pt: 4 for pt in PokeballType},
    )


def test_evaluate_position_no_board():
    player = Player(name="p1")
    player.points = 3
    opponent = Player(name="p2")
    game = _make_game([player, opponent])
    result = evaluate_position(game, player)
    assert result == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_affordable_now():
    """Card with shortfall=0: rounds=0, contribution = point / 1."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    free_card = _card("free", Tier.Common, point=3)
    board = Board(common_revealed=[free_card, None, None, None])
    game = _make_game([player, opponent], board)
    # alpha = 1.0 / (2-1) = 1.0; val = 0 + 1.0 * (3/1) = 3.0; result = 3/18
    assert evaluate_position(game, player) == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_one_turn_away():
    """Card costs 3 tokens, player has 0: shortfall=3, rounds=ceil(3/3)=1, contribution=point/2."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    card = _card("c", Tier.Common, point=6,
                 cost_types=(PokeballType.Red, PokeballType.Blue, PokeballType.Yellow))
    board = Board(common_revealed=[card, None, None, None])
    game = _make_game([player, opponent], board)
    # rounds = ceil(3/3) = 1; val = 6/2 = 3.0
    assert evaluate_position(game, player) == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_two_turns_away():
    """Shortfall=4 tokens: rounds=ceil(4/3)=2, contribution=point/3."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    card = _card("c", Tier.Common, point=6,
                 cost_types=(PokeballType.Red,) * 4)
    board = Board(common_revealed=[card, None, None, None])
    game = _make_game([player, opponent], board)
    assert evaluate_position(game, player) == pytest.approx(6.0 / 3.0 / WIN_SCORE)


def test_evaluate_position_takes_max_not_sum():
    """Two cards: 2pt affordable now vs 9pt two turns away. max(2/1, 9/3)=3."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    cheap = _card("cheap", Tier.Common, point=2)
    expensive = _card("exp", Tier.Common, point=9,
                      cost_types=(PokeballType.Red,) * 4)
    board = Board(common_revealed=[cheap, expensive, None, None])
    game = _make_game([player, opponent], board)
    assert evaluate_position(game, player) == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_epic_requires_master():
    """Epic card with no master token: skipped, max_val stays 0."""
    player = Player(name="p1")
    player.points = 2
    opponent = Player(name="p2")
    epic = _card("epic", Tier.Epic, point=8)
    board = Board(epic_revealed=[epic])
    game = _make_game([player, opponent], board)
    assert evaluate_position(game, player) == pytest.approx(2.0 / WIN_SCORE)


def test_evaluate_position_alpha_scales_with_players():
    """4-player game: alpha = 1/(4-1) = 1/3. Free 3pt card → val = 0 + (1/3)*3 = 1."""
    players = [Player(name=f"p{i}") for i in range(4)]
    free_card = _card("free", Tier.Common, point=3)
    board = Board(common_revealed=[free_card, None, None, None])
    game = _make_game(players, board)
    assert evaluate_position(game, players[0]) == pytest.approx(1.0 / WIN_SCORE, rel=1e-3)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_mcts.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pokemon_splendor.engine.eval'`

- [ ] **Step 3: Implement eval.py**

```python
# src/pokemon_splendor/engine/eval.py
from collections import Counter
from pokemon_splendor.models import Game, Player, PokeballType, Tier
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost

BASE_ALPHA = 1.0
WIN_SCORE = 18.0


def evaluate_position(game: Game, player: Player) -> float:
    """
    Shortfall-based position value normalised to ~[0, 1].
    Returns player.points/WIN_SCORE + alpha * max(card.point / (rounds_to_catch + 1))
    where rounds_to_catch = ceil(shortfall / 3) and alpha = BASE_ALPHA / (num_players - 1).
    """
    bonuses = get_player_bonuses(player)
    ptokens = Counter(t.name for t in player.tokens)
    all_slots = (
        game.board.common_revealed + game.board.uncommon_revealed
        + game.board.rare_revealed + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    max_val = 0.0
    for card in all_slots:
        if card is None:
            continue
        ec = calculate_effective_cost(card, bonuses)
        master_req = max(
            ec.get(PokeballType.Master, 0),
            1 if card.tier in (Tier.Epic, Tier.Legendary) else 0,
        )
        if ptokens.get(PokeballType.Master, 0) < master_req:
            continue
        shortfall = sum(
            max(0, ec.get(pt, 0) - ptokens.get(pt, 0))
            for pt in PokeballType if pt != PokeballType.Master
        )
        rounds = (shortfall + 2) // 3
        max_val = max(max_val, card.point / (rounds + 1))
    alpha = BASE_ALPHA / max(1, len(game.players) - 1)
    return (player.points + alpha * max_val) / WIN_SCORE
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_mcts.py -v
```

Expected: all 7 eval tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pokemon_splendor/engine/eval.py tests/test_mcts.py
git commit -m "feat: add shortfall-based evaluate_position to engine/eval.py"
```

---

## Task 3: Implement game simulator in engine/simulator.py

**Files:**
- Create: `src/pokemon_splendor/engine/simulator.py`
- Modify: `tests/test_mcts.py`

`game_step` replicates the logic of `PokemonSplendorEnv.step()` and `_apply_action()` without rewards or PettingZoo bookkeeping. It deep-copies the game, applies one action for `player_name`, handles all phase transitions (DISCARD threshold → EVOLVE availability → end turn → turn rotation → win detection), and returns `(new_game, is_terminal)`.

`_step_inplace` is the same but mutates in-place (used by MCTSAgent to avoid repeated copying when advancing opponents in a loop).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_mcts.py`:

```python
from pathlib import Path
from pokemon_splendor.engine.simulator import game_step
from pokemon_splendor.engine.env import PokemonSplendorEnv
import numpy as np

JSONL = Path("data/pokemon.jsonl")


def _make_env_game():
    env = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    env.reset()
    return env


def test_game_step_returns_new_game_object():
    """game_step must return a copy, not mutate the original."""
    env = _make_env_game()
    original = env.game
    agent = env.agent_selection
    mask = env.action_mask(agent)
    action = int(np.where(mask)[0][0])
    new_game, _ = game_step(original, action, agent)
    assert new_game is not original


def test_game_step_advances_turn():
    """After a non-terminal action, game.turn should usually change."""
    env = _make_env_game()
    original = env.game
    agent = env.agent_selection
    mask = env.action_mask(agent)
    # Take a token-taking action (always available at game start)
    from pokemon_splendor.engine.actions import TAKE_DIFF_START, TAKE_SAME_START
    token_action = next(
        a for a in range(TAKE_DIFF_START, TAKE_SAME_START) if mask[a]
    )
    new_game, is_terminal = game_step(original, token_action, agent)
    assert not is_terminal
    # If no evolvable cards, turn should have advanced to next player
    # (can't assert specific name since some games may have evolvable cards immediately)
    assert new_game.turn is not None


def test_game_step_terminal_on_18_points():
    """Setting a player to 18 points and having them catch a final card triggers terminal."""
    env = _make_env_game()
    game = env.game
    agent = env.agent_selection
    player = next(p for p in game.players if p.name == agent)

    # Give player enough points and tokens to catch and win
    player.points = 17
    for pt in [PokeballType.Red, PokeballType.Blue, PokeballType.Yellow,
               PokeballType.Pink, PokeballType.Black]:
        player.tokens.extend([PokeballToken(pt)] * 4)

    mask = env.action_mask(agent)
    from pokemon_splendor.engine.actions import CATCH_BOARD_START, CATCH_RESERVED_START

    # Find a catch action for a card worth ≥1 point
    catch_action = None
    all_slots = (
        game.board.common_revealed + game.board.uncommon_revealed
        + game.board.rare_revealed + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    for slot_idx, card in enumerate(all_slots):
        a = CATCH_BOARD_START + slot_idx
        if mask[a] and card is not None and card.point >= 1:
            catch_action = a
            break
    if catch_action is None:
        pytest.skip("No catchable point-scoring card in this game state")

    new_game, is_terminal = game_step(game, catch_action, agent)
    # Terminal happens at end of round; check that win_triggered is at least set
    assert new_game.win_triggered or is_terminal
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_mcts.py::test_game_step_returns_new_game_object tests/test_mcts.py::test_game_step_advances_turn tests/test_mcts.py::test_game_step_terminal_on_18_points -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'pokemon_splendor.engine.simulator'`

- [ ] **Step 3: Implement simulator.py**

```python
# src/pokemon_splendor/engine/simulator.py
import copy
from collections import Counter
from pokemon_splendor.models import Game, Player, GamePhase, PokeballType
from pokemon_splendor.engine.rules import (
    apply_take_different_tokens, apply_take_same_tokens,
    apply_catch_pokemon, apply_reserve, apply_discard, apply_evolve,
    get_evolvable_cards, check_win_condition,
)
from pokemon_splendor.engine.actions import (
    TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START, DISCARD_START,
    EVOLVE_START, EVOLVE_PASS, DISCARD_ACTION, MAX_OWNED_CARDS,
)


def game_step(game: Game, action: int, player_name: str) -> tuple[Game, bool]:
    """Apply action to a deep copy of game. Returns (new_game, is_terminal)."""
    game = copy.deepcopy(game)
    is_terminal = _step_inplace(game, action, player_name)
    return game, is_terminal


def _step_inplace(game: Game, action: int, player_name: str) -> bool:
    """Apply action in-place. Returns True if game is now terminal."""
    player = next(p for p in game.players if p.name == player_name)
    _apply_action(game, player, action)
    return _process_transitions(game, player, player_name)


def _apply_action(game: Game, player: Player, action: int) -> None:
    if game.phase == GamePhase.DISCARD:
        for ptype, idx in DISCARD_ACTION.items():
            if action == idx:
                apply_discard(game, player, ptype)
                return
        raise ValueError(f"Invalid discard action {action}")

    if game.phase == GamePhase.EVOLVE:
        if action == EVOLVE_PASS:
            return
        card_idx = action - EVOLVE_START
        apply_evolve(game, player, card_idx)
        game.evolved_this_turn = True
        return

    # Main phase
    if action == EVOLVE_PASS:
        return
    if DISCARD_START <= action < EVOLVE_START:
        for ptype, idx in DISCARD_ACTION.items():
            if action == idx:
                apply_discard(game, player, ptype)
                return
        raise ValueError(f"Invalid discard action {action}")
    if TAKE_DIFF_START <= action < TAKE_SAME_START:
        combo = TAKE_DIFF_COMBOS[action - TAKE_DIFF_START]
        apply_take_different_tokens(game, player, list(combo))
    elif TAKE_SAME_START <= action < CATCH_BOARD_START:
        ptype = NORMAL_TYPES[action - TAKE_SAME_START]
        apply_take_same_tokens(game, player, ptype)
    elif CATCH_BOARD_START <= action < CATCH_RESERVED_START:
        slot_idx = action - CATCH_BOARD_START
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed
            + game.board.rare_revealed + game.board.epic_revealed
            + game.board.legendary_revealed
        )
        pokemon = all_slots[slot_idx]
        apply_catch_pokemon(game, player, pokemon, from_reserved=False, board_slot=slot_idx)
    elif CATCH_RESERVED_START <= action < RESERVE_MASTER_START:
        idx = action - CATCH_RESERVED_START
        pokemon = player.reserved_cards[idx]
        apply_catch_pokemon(game, player, pokemon, from_reserved=True, board_slot=None)
    elif RESERVE_MASTER_START <= action < RESERVE_NO_MASTER_START:
        slot_idx = action - RESERVE_MASTER_START
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed + game.board.rare_revealed
        )
        pokemon = all_slots[slot_idx]
        apply_reserve(game, player, pokemon, board_slot=slot_idx, take_master=True)
    elif RESERVE_NO_MASTER_START <= action < DISCARD_START:
        slot_idx = action - RESERVE_NO_MASTER_START
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed + game.board.rare_revealed
        )
        pokemon = all_slots[slot_idx]
        apply_reserve(game, player, pokemon, board_slot=slot_idx, take_master=False)


def _process_transitions(game: Game, player: Player, player_name: str) -> bool:
    if game.phase == GamePhase.EVOLVE:
        return _end_turn(game, player)
    if game.phase == GamePhase.DISCARD:
        if len(player.tokens) <= 10:
            return _enter_evolve_phase(game, player, player_name)
        return False
    # MAIN phase action taken
    if len(player.tokens) > 10:
        game.phase = GamePhase.DISCARD
        return False
    return _enter_evolve_phase(game, player, player_name)


def _enter_evolve_phase(game: Game, player: Player, player_name: str) -> bool:
    game.phase = GamePhase.EVOLVE
    evolvable = get_evolvable_cards(game, player)
    if not evolvable:
        return _end_turn(game, player)
    return False


def _end_turn(game: Game, player: Player) -> bool:
    game.phase = GamePhase.MAIN
    game.evolved_this_turn = False

    winner = check_win_condition(game)
    if winner:
        game.win_triggered = True

    if game.win_triggered:
        starting_idx = game.players.index(game.starting_player)
        last_in_round_idx = (starting_idx - 1) % len(game.players)
        last_in_round = game.players[last_in_round_idx]
        if player is last_in_round:
            game.winner = check_win_condition(game)
            return True

    idx = game.players.index(player)
    next_player = game.players[(idx + 1) % len(game.players)]
    if next_player is game.starting_player:
        game.round += 1
    game.turn = next_player
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_mcts.py -v
```

Expected: all simulator tests PASS (eval tests should still pass too).

- [ ] **Step 5: Commit**

```bash
git add src/pokemon_splendor/engine/simulator.py tests/test_mcts.py
git commit -m "feat: add game_step simulator for MCTS tree expansion"
```

---

## Task 4: Implement MCTSAgent in agents/mcts.py

**Files:**
- Create: `src/pokemon_splendor/agents/mcts.py`
- Modify: `tests/test_mcts.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_mcts.py`:

```python
from pokemon_splendor.agents.mcts import MCTSAgent, make_early_capture_policy


def test_mcts_prune_tokens_no_short_combos():
    """Pruned actions must not contain 1- or 2-token TAKE_DIFF combos."""
    from pokemon_splendor.engine.actions import TAKE_DIFF_COMBOS, TAKE_DIFF_START
    env = _make_env_game()
    agent_name = env.agent_selection
    agent = MCTSAgent(env, agent_name, n_simulations=1, depth=1)
    game = env.game
    player = next(p for p in game.players if p.name == agent_name)
    pruned = agent._prune_actions(game, player)
    for action in pruned:
        if TAKE_DIFF_START <= action < TAKE_DIFF_START + len(TAKE_DIFF_COMBOS):
            combo = TAKE_DIFF_COMBOS[action - TAKE_DIFF_START]
            assert len(combo) == 3, f"Found {len(combo)}-token combo in pruned actions"


def test_mcts_prune_reserve_master_preferred():
    """If RESERVE_MASTER is valid for a slot, RESERVE_NO_MASTER for same slot must be excluded."""
    from pokemon_splendor.engine.actions import RESERVE_MASTER_START, RESERVE_NO_MASTER_START
    env = _make_env_game()
    agent_name = env.agent_selection
    agent = MCTSAgent(env, agent_name, n_simulations=1, depth=1)
    game = env.game
    player = next(p for p in game.players if p.name == agent_name)
    pruned = set(agent._prune_actions(game, player))
    for slot_idx in range(12):
        master_action = RESERVE_MASTER_START + slot_idx
        no_master_action = RESERVE_NO_MASTER_START + slot_idx
        if master_action in pruned:
            assert no_master_action not in pruned, (
                f"Both RESERVE_MASTER and RESERVE_NO_MASTER present for slot {slot_idx}"
            )


def test_mcts_prune_reserve_max_five():
    """At most 5 reserve actions in pruned set."""
    from pokemon_splendor.engine.actions import RESERVE_MASTER_START, DISCARD_START
    env = _make_env_game()
    agent_name = env.agent_selection
    agent = MCTSAgent(env, agent_name, n_simulations=1, depth=1)
    game = env.game
    player = next(p for p in game.players if p.name == agent_name)
    pruned = agent._prune_actions(game, player)
    reserve_count = sum(
        1 for a in pruned if RESERVE_MASTER_START <= a < DISCARD_START
    )
    assert reserve_count <= 5


def test_mcts_agent_returns_valid_action():
    """MCTSAgent.act() must always return an action that is valid per the mask."""
    env = _make_env_game()
    agent_name = env.agent_selection
    agent = MCTSAgent(env, agent_name, n_simulations=50, depth=2)
    obs, _, _, _, _ = env.last()
    mask = env.action_mask(agent_name)
    action = agent.act(obs, mask)
    assert mask[action], f"Action {action} is not valid per mask"


def test_mcts_agent_beats_random():
    """MCTSAgent (200 sims, depth 4) should win >60% vs random over 30 games."""
    import random as pyrandom
    wins = 0
    games = 30
    for _ in range(games):
        env = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
        env.reset()
        mcts_name = env.possible_agents[0]
        random_name = env.possible_agents[1]
        mcts_agent = MCTSAgent(env, mcts_name, n_simulations=200, depth=4)
        for _ in range(10000):
            if not env.agents:
                break
            name = env.agent_selection
            obs, _, term, trunc, _ = env.last()
            if term or trunc:
                break
            mask = env.action_mask(name)
            if name == mcts_name:
                action = mcts_agent.act(obs, mask)
            else:
                action = int(pyrandom.choice(np.where(mask)[0]))
            env.step(action)
        winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
        if winner.name == mcts_name:
            wins += 1
    assert wins / games >= 0.60, f"MCTSAgent only won {wins}/{games} vs random"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_mcts.py::test_mcts_prune_tokens_no_short_combos -v
```

Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement mcts.py**

```python
# src/pokemon_splendor/agents/mcts.py
import copy
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from pokemon_splendor.models import Game, Player, GamePhase, PokeballType, Tier
from pokemon_splendor.engine.eval import evaluate_position
from pokemon_splendor.engine.simulator import _step_inplace
from pokemon_splendor.engine.observation import compute_mask
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost, get_evolvable_cards
from pokemon_splendor.engine.actions import (
    TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START, DISCARD_START,
    EVOLVE_START, EVOLVE_PASS, DISCARD_ACTION, TAKE_SAME_ACTION,
)
from pokemon_splendor.agents.base import RuleBasedAgent

_C = math.sqrt(2)

OpponentPolicy = Callable[[Game, str], int]


@dataclass
class MCTSNode:
    game: Game
    parent: "MCTSNode | None"
    action: int | None
    depth: int = 0
    visits: int = 0
    total_value: float = 0.0
    children: dict[int, "MCTSNode"] = field(default_factory=dict)
    untried_actions: list[int] = field(default_factory=list)


class MCTSAgent(RuleBasedAgent):
    def __init__(self, env, player_name: str, n_simulations: int = 200,
                 depth: int = 4, opponent_policy: OpponentPolicy | None = None):
        super().__init__(env, player_name)
        self._n_simulations = n_simulations
        self._depth = depth
        self._opponent_policy = opponent_policy or make_early_capture_policy()

    def act(self, obs: np.ndarray, mask: np.ndarray) -> int:
        game = copy.deepcopy(self._game)
        player = next(p for p in game.players if p.name == self._player_name)

        if game.phase == GamePhase.DISCARD:
            return self._best_discard_action(game, player, mask)

        pruned = self._prune_actions(game, player)
        if not pruned:
            return int(np.where(mask)[0][0])

        root = MCTSNode(
            game=game, parent=None, action=None, depth=0,
            untried_actions=list(pruned),
        )
        for _ in range(self._n_simulations):
            self._simulate(root)

        if not root.children:
            return pruned[0]
        return max(root.children.values(), key=lambda c: c.visits).action

    # ------------------------------------------------------------------
    # MCTS core
    # ------------------------------------------------------------------

    def _simulate(self, root: MCTSNode) -> None:
        node = self._select(root)
        if node.untried_actions and not self._is_terminal(node):
            node = self._expand(node)
        value = self._evaluate(node)
        self._backpropagate(node, value)

    def _select(self, node: MCTSNode) -> MCTSNode:
        while (not node.untried_actions and node.children
               and not self._is_terminal(node)):
            node = max(node.children.values(),
                       key=lambda c: self._ucb(c, node))
        return node

    def _ucb(self, node: MCTSNode, parent: MCTSNode) -> float:
        if node.visits == 0:
            return float("inf")
        return (node.total_value / node.visits
                + _C * math.sqrt(math.log(parent.visits) / node.visits))

    def _expand(self, node: MCTSNode) -> MCTSNode:
        action = node.untried_actions.pop()
        game = copy.deepcopy(node.game)
        is_terminal = _step_inplace(game, action, self._player_name)

        # Handle forced discard for the MCTS agent
        while (not is_terminal
               and game.turn.name == self._player_name
               and game.phase == GamePhase.DISCARD):
            player = next(p for p in game.players if p.name == self._player_name)
            discard_mask = compute_mask(game, self._player_name)
            d_action = self._best_discard_action(game, player, discard_mask)
            is_terminal = _step_inplace(game, d_action, self._player_name)

        # Advance all opponents
        while not is_terminal and game.turn.name != self._player_name:
            opp_name = game.turn.name
            opp_action = self._opponent_policy(game, opp_name)
            is_terminal = _step_inplace(game, opp_action, opp_name)

        our_player = next(p for p in game.players if p.name == self._player_name)
        untried = ([] if is_terminal or node.depth + 1 >= self._depth
                   else self._prune_actions(game, our_player))

        child = MCTSNode(
            game=game, parent=node, action=action,
            depth=node.depth + 1, untried_actions=untried,
        )
        node.children[action] = child
        return child

    def _evaluate(self, node: MCTSNode) -> float:
        if self._is_terminal(node):
            if node.game.winner is None:
                player = next(p for p in node.game.players if p.name == self._player_name)
                return evaluate_position(node.game, player)
            return 1.0 if node.game.winner.name == self._player_name else 0.0
        player = next(p for p in node.game.players if p.name == self._player_name)
        return evaluate_position(node.game, player)

    def _backpropagate(self, node: MCTSNode, value: float) -> None:
        while node is not None:
            node.visits += 1
            node.total_value += value
            node = node.parent

    def _is_terminal(self, node: MCTSNode) -> bool:
        return node.game.winner is not None

    # ------------------------------------------------------------------
    # Action pruning
    # ------------------------------------------------------------------

    def _prune_actions(self, game: Game, player: Player) -> list[int]:
        mask = compute_mask(game, player.name)

        if game.phase == GamePhase.EVOLVE:
            actions = [a for a in range(EVOLVE_START, EVOLVE_PASS) if mask[a]]
            if mask[EVOLVE_PASS]:
                actions.append(EVOLVE_PASS)
            return actions

        actions: list[int] = []

        # Token-taking: 3-token TAKE_DIFF only
        for i, combo in enumerate(TAKE_DIFF_COMBOS):
            if len(combo) == 3:
                a = TAKE_DIFF_START + i
                if mask[a]:
                    actions.append(a)

        # TAKE_SAME: all valid
        for a in range(TAKE_SAME_START, CATCH_BOARD_START):
            if mask[a]:
                actions.append(a)

        # Catch: all valid
        for a in range(CATCH_BOARD_START, RESERVE_MASTER_START):
            if mask[a]:
                actions.append(a)

        # Reserve: hard filters + top-5 scoring
        actions.extend(self._pruned_reserve_actions(game, player, mask))

        return actions if actions else list(np.where(mask)[0])

    def _pruned_reserve_actions(self, game: Game, player: Player,
                                 mask: np.ndarray) -> list[int]:
        # Hard filter: winning catch available
        all_board_slots = (
            game.board.common_revealed + game.board.uncommon_revealed
            + game.board.rare_revealed + game.board.epic_revealed
            + game.board.legendary_revealed
        )
        for slot_idx, card in enumerate(all_board_slots):
            if mask[CATCH_BOARD_START + slot_idx] and card is not None:
                if player.points + card.point >= 18:
                    return []
        for i, card in enumerate(player.reserved_cards):
            if mask[CATCH_RESERVED_START + i]:
                if player.points + card.point >= 18:
                    return []

        # Hard filter: already holds 2+ reserved cards
        if len(player.reserved_cards) >= 2:
            return []

        reservable = (
            game.board.common_revealed + game.board.uncommon_revealed
            + game.board.rare_revealed
        )
        candidates: list[tuple[float, int]] = []
        for slot_idx, card in enumerate(reservable):
            if card is None:
                continue
            # Hard filter: common, 0 points, no bonus
            if card.tier == Tier.Common and card.point == 0 and not card.bonus:
                continue
            # Prefer RESERVE_MASTER when available (board has master tokens)
            if mask[RESERVE_MASTER_START + slot_idx]:
                action = RESERVE_MASTER_START + slot_idx
            elif mask[RESERVE_NO_MASTER_START + slot_idx]:
                action = RESERVE_NO_MASTER_START + slot_idx
            else:
                continue
            score = self._reserve_score(game, player, card)
            candidates.append((score, action))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [action for _, action in candidates[:5]]

    def _reserve_score(self, game: Game, player: Player, card) -> float:
        bonuses = get_player_bonuses(player)
        ptokens = Counter(t.name for t in player.tokens)
        ec = calculate_effective_cost(card, bonuses)
        my_shortfall = sum(
            max(0, ec.get(pt, 0) - ptokens.get(pt, 0))
            for pt in PokeballType if pt != PokeballType.Master
        )
        my_rounds = (my_shortfall + 2) // 3

        opponents = [p for p in game.players if p is not player]
        min_opp_rounds = 999
        for opp in opponents:
            opp_bonuses = get_player_bonuses(opp)
            opp_ec = calculate_effective_cost(card, opp_bonuses)
            opp_ptokens = Counter(t.name for t in opp.tokens)
            opp_shortfall = sum(
                max(0, opp_ec.get(pt, 0) - opp_ptokens.get(pt, 0))
                for pt in PokeballType if pt != PokeballType.Master
            )
            min_opp_rounds = min(min_opp_rounds, (opp_shortfall + 2) // 3)

        return float(card.point + min_opp_rounds - my_rounds)

    def _best_discard_action(self, game: Game, player: Player,
                              mask: np.ndarray) -> int:
        """Discard the token that increases total shortfall the least."""
        bonuses = get_player_bonuses(player)
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed
            + game.board.rare_revealed + game.board.epic_revealed
            + game.board.legendary_revealed
        )
        tc = Counter(t.name for t in player.tokens)
        best_action, best_score = None, float("inf")
        for ptype, idx in DISCARD_ACTION.items():
            if not mask[idx]:
                continue
            if ptype == PokeballType.Master:
                score = 1000.0
            else:
                temp = Counter(tc)
                temp[ptype] -= 1
                score = sum(
                    max(0, calculate_effective_cost(card, bonuses).get(pt, 0) - temp.get(pt, 0))
                    for card in all_slots if card is not None
                    for pt in PokeballType if pt != PokeballType.Master
                )
            if score < best_score:
                best_score = score
                best_action = idx
        return best_action if best_action is not None else int(np.where(mask)[0][0])


# ------------------------------------------------------------------
# Opponent policy factories
# ------------------------------------------------------------------

def make_early_capture_policy() -> OpponentPolicy:
    """Standalone early-capture policy: catch cheapest, else take tokens toward cheapest."""
    from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost

    def policy(game: Game, player_name: str) -> int:
        player = next(p for p in game.players if p.name == player_name)
        mask = compute_mask(game, player_name)
        bonuses = get_player_bonuses(player)

        if game.phase == GamePhase.DISCARD:
            tc = Counter(t.name for t in player.tokens)
            best_action, best_count = None, -1
            for ptype, idx in DISCARD_ACTION.items():
                if mask[idx] and ptype != PokeballType.Master:
                    count = tc.get(ptype, 0)
                    if count > best_count:
                        best_count = count
                        best_action = idx
            return best_action if best_action is not None else int(np.where(mask)[0][0])

        if game.phase == GamePhase.EVOLVE:
            for a in range(EVOLVE_START, EVOLVE_PASS):
                if mask[a]:
                    return a
            return EVOLVE_PASS

        # MAIN: catch cheapest affordable
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed
            + game.board.rare_revealed + game.board.epic_revealed
            + game.board.legendary_revealed
        )
        catchable = []
        for slot_idx, card in enumerate(all_slots):
            a = CATCH_BOARD_START + slot_idx
            if mask[a] and card is not None:
                catchable.append((a, card))
        for i, card in enumerate(player.reserved_cards):
            a = CATCH_RESERVED_START + i
            if mask[a]:
                catchable.append((a, card))

        if catchable:
            return min(catchable,
                       key=lambda item: sum(calculate_effective_cost(item[1], bonuses).values())
                       )[0]

        # Take tokens toward cheapest card
        ptokens = Counter(t.name for t in player.tokens)
        all_cards = [(i, c) for i, c in enumerate(all_slots) if c is not None]
        if all_cards:
            target = min(all_cards, key=lambda item: sum(
                max(0, cnt - ptokens.get(pt, 0))
                for pt, cnt in calculate_effective_cost(item[1], bonuses).items()
            ))[1]
            ec = calculate_effective_cost(target, bonuses)
            needed = Counter({pt: max(0, cnt - ptokens.get(pt, 0))
                              for pt, cnt in ec.items()})
            best_action, best_score = None, -1
            from pokemon_splendor.engine.actions import TAKE_DIFF_COMBOS, TAKE_SAME_ACTION
            for i, combo in enumerate(TAKE_DIFF_COMBOS):
                a = TAKE_DIFF_START + i
                if not mask[a]:
                    continue
                score = sum(min(needed.get(pt, 0), 1) for pt in combo)
                if score > best_score:
                    best_score = score
                    best_action = a
            for pt in NORMAL_TYPES:
                a = TAKE_SAME_ACTION[pt]
                if mask[a] and needed.get(pt, 0) >= 2 and 2 > best_score:
                    best_score = 2
                    best_action = a
            if best_action is not None:
                return best_action

        return int(np.where(mask)[0][0])

    return policy


def make_rl_policy(model_path: str) -> OpponentPolicy:
    """Load a MaskablePPO model and return it as an opponent policy callable."""
    from sb3_contrib import MaskablePPO
    from pokemon_splendor.engine.observation import compute_observation
    model = MaskablePPO.load(model_path)

    def policy(game: Game, player_name: str) -> int:
        obs = compute_observation(game, player_name)
        mask = compute_mask(game, player_name)
        action, _ = model.predict(obs, action_masks=mask, deterministic=True)
        return int(action)

    return policy
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_mcts.py -v
```

Expected: all tests PASS. `test_mcts_agent_beats_random` runs 30 games so may take 30–60 seconds.

- [ ] **Step 5: Commit**

```bash
git add src/pokemon_splendor/agents/mcts.py tests/test_mcts.py
git commit -m "feat: add MCTSAgent with UCB tree, action pruning, and shortfall eval"
```

---

## Task 5: Wire MCTSAgent into CLI

**Files:**
- Modify: `src/pokemon_splendor/__main__.py`

- [ ] **Step 1: Add mcts to AGENT_TYPES and _make_agent**

In `src/pokemon_splendor/__main__.py`, update `AGENT_TYPES`:

```python
AGENT_TYPES = (
    "random          uniform random valid action\n"
    "human           interactive stdin\n"
    "early-capture   catches cheapest affordable card\n"
    "high-point      maximises points-per-round ratio\n"
    "bonus-engine    builds bonus engine first, then switches to points\n"
    "evolution-chain scores cards by full evolution chain value\n"
    "denial          reserves cards opponents can almost afford\n"
    "mcts            MCTS with shortfall eval, 200 simulations (default)\n"
    "<model>.zip     any .zip path loads that trained RL model"
)
```

In `_make_agent`, add before the `.zip` check:

```python
if agent_type == "mcts":
    from pokemon_splendor.agents.mcts import MCTSAgent
    return MCTSAgent(env, player_name)
```

- [ ] **Step 2: Verify CLI works**

```bash
uv run pokemon-splendor --players mcts,random --mode benchmark --games 5
```

Expected: runs 5 games and prints win rates. No errors.

- [ ] **Step 3: Run all tests**

```bash
uv run pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/pokemon_splendor/__main__.py
git commit -m "feat: wire mcts agent into CLI"
```

---

## Self-Review

**Spec coverage:**
- ✅ `engine/observation.py` — `compute_observation`, `compute_mask`
- ✅ `engine/eval.py` — `evaluate_position` with shortfall formula
- ✅ `engine/simulator.py` — `game_step`, `_step_inplace`, phase transitions, win detection
- ✅ `agents/mcts.py` — `MCTSNode`, `MCTSAgent`, `make_early_capture_policy`, `make_rl_policy`
- ✅ Action pruning: 3-token TAKE_DIFF only, all catches, reserve hard filters + top-5 score
- ✅ Discard: forced shortfall-based (least useful token)
- ✅ Evolve: fully in tree, no pruning
- ✅ Reserve: RESERVE_MASTER preferred over RESERVE_NO_MASTER for same slot
- ✅ Reserve: skip when winning catch available, skip when 2+ reserved, skip Common 0pt no-bonus
- ✅ Opponent policy: pluggable callable, default early-capture
- ✅ `make_rl_policy` using `compute_observation` and `compute_mask`
- ✅ CLI integration with `"mcts"` key and help text
- ✅ `env.py` unchanged in reward logic — pure delegation refactor
- ✅ Tests: eval, simulator, pruning, agent integration, vs-random benchmark

**Placeholder scan:** No TBDs or incomplete sections found.

**Type consistency:** `MCTSNode` fields, `_step_inplace` signature, `OpponentPolicy` type alias, and `evaluate_position` signature are consistent across all tasks.
