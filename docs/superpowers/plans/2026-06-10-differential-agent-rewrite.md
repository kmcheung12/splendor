# DifferentialAgent Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `DifferentialAgent` as a deterministic heuristic agent that scores every legal action on one scale (`self_value + λ × harm`) with threat-weighted sabotage, beating `DenialAgent` >50% head-to-head.

**Architecture:** Module-level pure functions in `src/pokemon_splendor/agents/differential.py` (demand, engine quality, threat, action values, harm), each independently unit-testable with hand-built `Player`/`Game` dataclasses (no env needed). `DifferentialAgent(RuleBasedAgent)` enumerates legal actions from the mask, scores each, plays argmax. Class name and `__main__.py` registry entry stay unchanged.

**Tech Stack:** Python, numpy (mask only), pytest. Reuses `engine.rules` helpers (`get_player_bonuses`, `calculate_effective_cost`, `get_evolvable_cards`) and `engine.actions` constants.

**Spec:** `docs/superpowers/specs/2026-06-10-differential-agent-rewrite-design.md`

**Key domain facts** (verified against `engine/rules.py`):
- Bonuses come from unevolved caught cards (`get_player_bonuses`, rules.py:7).
- Evolution requires *bonuses*, not tokens, and the evolve target must be on board or in own reserve (`get_evolvable_cards`, `apply_evolve`).
- Evolved source cards stop scoring (`_recalculate_points`, rules.py:50) → evolution gain = target.point − source.point.
- Game ends when anyone reaches 18; highest points wins, card count tiebreak (`check_win_condition`, rules.py:282).
- Max 3 reserved cards (`apply_reserve`, rules.py:182). Action space: see `engine/actions.py` (TOTAL_ACTIONS = 108).

---

### Task 1: Test fixtures + core economics helpers

**Files:**
- Create: `tests/test_differential.py`
- Rewrite: `src/pokemon_splendor/agents/differential.py` (helpers section; keep the old `DifferentialAgent` class temporarily — it is replaced in Task 6)

- [ ] **Step 1: Write failing tests with hand-built fixtures**

Create `tests/test_differential.py`:

```python
# tests/test_differential.py
import numpy as np
import pytest
from collections import Counter
from pokemon_splendor.models import (
    Game, Player, Pokemon, Board, PokeballType, PokeballToken, Bonus, Tier,
)

R, Y, B, P, K = (PokeballType.Red, PokeballType.Yellow, PokeballType.Blue,
                 PokeballType.Pink, PokeballType.Black)


def make_card(name="X", tier=Tier.Common, cost=None, bonus=None,
              evolve=None, evolve_into="", point=0):
    return Pokemon(
        name=name, tier=tier,
        cost=[PokeballToken(c) for c in (cost or [])],
        bonus=[Bonus(c) for c in (bonus or [])],
        evolve=[Bonus(c) for c in (evolve or [])],
        evolve_into=evolve_into, point=point,
    )


def make_player(name="me", tokens=None, cards=None, reserved=None, points=0):
    return Player(
        name=name,
        tokens=[PokeballToken(c) for c in (tokens or [])],
        cards=list(cards or []),
        reserved_cards=list(reserved or []),
        points=points,
    )


def make_board(common=None, uncommon=None, rare=None, epic=None, legendary=None):
    def pad(lst, n):
        lst = list(lst or [])
        return lst + [None] * (n - len(lst))
    return Board(
        common_revealed=pad(common, 4), uncommon_revealed=pad(uncommon, 4),
        rare_revealed=pad(rare, 4), epic_revealed=pad(epic, 1),
        legendary_revealed=pad(legendary, 1),
    )


def make_game(players, board=None, tokens=None):
    bank = {pt: 5 for pt in PokeballType}
    if tokens:
        bank.update(tokens)
    return Game(players=players, turn=players[0], starting_player=players[0],
                round=1, board=board or make_board(), tokens=bank)


# --- Task 1: core economics ---

def test_token_shortfall_counts_missing_tokens_after_bonuses():
    from pokemon_splendor.agents.differential import token_shortfall
    # cost 3 yellow + 1 red; player has 1 yellow bonus and 1 yellow token
    card = make_card(cost=[Y, Y, Y, R])
    bonus_card = make_card(name="b", bonus=[Y])
    player = make_player(tokens=[Y], cards=[bonus_card])
    short = token_shortfall(player, card)
    assert short[Y] == 1  # 3 - 1 bonus - 1 token
    assert short[R] == 1
    assert sum(short.values()) == 2


def test_rounds_to_catch_floor_is_one():
    from pokemon_splendor.agents.differential import rounds_to_catch
    card = make_card(cost=[Y])
    player = make_player(tokens=[Y])
    assert rounds_to_catch(player, card) == 1.0


def test_ppr_zero_point_card_is_zero():
    from pokemon_splendor.agents.differential import ppr
    card = make_card(cost=[Y], point=0)
    assert ppr(make_player(), card) == 0.0


def test_ppr_affordable_card_equals_points():
    from pokemon_splendor.agents.differential import ppr
    card = make_card(cost=[Y], point=4)
    player = make_player(tokens=[Y])
    assert ppr(player, card) == 4.0


def test_find_card_point_searches_revealed_decks_and_reserves():
    from pokemon_splendor.agents.differential import find_card_point
    on_board = make_card(name="Charmeleon", point=5)
    in_deck = make_card(name="Wartortle", point=4)
    reserved = make_card(name="Ivysaur", point=3)
    opp = make_player(name="opp", reserved=[reserved])
    board = make_board(uncommon=[on_board])
    board.rare_deck = [in_deck]
    game = make_game([make_player(), opp], board)
    assert find_card_point(game, "Charmeleon") == 5
    assert find_card_point(game, "Wartortle") == 4
    assert find_card_point(game, "Ivysaur") == 3
    assert find_card_point(game, "Missingno") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/alan/code/splendor && python -m pytest tests/test_differential.py -v`
Expected: FAIL with `ImportError: cannot import name 'token_shortfall'`

- [ ] **Step 3: Implement helpers**

In `src/pokemon_splendor/agents/differential.py`, replace the imports and module docstring area (everything above `class DifferentialAgent`) with:

```python
# src/pokemon_splendor/agents/differential.py
from collections import Counter
import numpy as np
from pokemon_splendor.agents.base import RuleBasedAgent
from pokemon_splendor.models import Game, Player, Pokemon, PokeballType
from pokemon_splendor.engine.rules import (
    get_player_bonuses, calculate_effective_cost, get_evolvable_cards,
)
from pokemon_splendor.engine.actions import (
    NORMAL_TYPES, TAKE_DIFF_COMBOS, TAKE_DIFF_START, TAKE_SAME_ACTION,
    CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START,
    EVOLVE_START, EVOLVE_PASS,
)

# Tunable weights (see spec: tunable weights table)
EXP = 1.5              # bonus concentration exponent
ALPHA = 1.0            # projected-points share in threat
BETA = 0.5             # engine quality share in threat
LAMBDA_BASE = 0.2      # baseline sabotage weight
LAMBDA_SCALE = 1.0     # threat-scaled sabotage weight
DELTA = 0.6            # reserve deferral discount
ENDGAME_DELTA = 0.05   # reserve discount once endgame
E_EVO_DENIAL = 1.0     # evolution-denial harm multiplier
MASTER_BONUS = 0.15    # reserve-with-Master bump
SLOT_PENALTY = (0.0, 0.2, 2.0)  # indexed by len(reserved_cards), capped at 2
TOKEN_FACTOR = 0.8     # token progress vs buying the target outright
URGENCY = 1.5          # take completes affordability of target
SCARCE_SUPPLY = 2      # bank count at/below which token denial bites
TOKEN_HARM = 0.3       # harm per denied scarce token
WIN_POINTS = 18
MAX_HORIZON = 15.0


def _all_revealed(game: Game) -> list[Pokemon | None]:
    return (
        game.board.common_revealed + game.board.uncommon_revealed +
        game.board.rare_revealed + game.board.epic_revealed +
        game.board.legendary_revealed
    )


def token_shortfall(player: Player, card: Pokemon) -> Counter:
    bonuses = get_player_bonuses(player)
    ec = calculate_effective_cost(card, bonuses)
    tokens = Counter(t.name for t in player.tokens)
    return Counter({
        pt: cnt - tokens.get(pt, 0)
        for pt, cnt in ec.items() if cnt - tokens.get(pt, 0) > 0
    })


def rounds_to_catch(player: Player, card: Pokemon) -> float:
    shortfall = sum(token_shortfall(player, card).values())
    return max(1.0, (shortfall + 2) / 3)


def ppr(player: Player, card: Pokemon) -> float:
    if card.point == 0:
        return 0.0
    return card.point / rounds_to_catch(player, card)


def find_card_point(game: Game, name: str) -> int | None:
    for c in _all_revealed(game):
        if c is not None and c.name == name:
            return c.point
    for deck in (game.board.common_deck, game.board.uncommon_deck,
                 game.board.rare_deck, game.board.epic_deck,
                 game.board.legendary_deck):
        for c in deck:
            if c.name == name:
                return c.point
    for p in game.players:
        for c in p.reserved_cards:
            if c.name == name:
                return c.point
    return None
```

Keep the existing `DifferentialAgent` class below (it still imports `Player, Pokemon` etc. that remain available; delete the old module-level `_BLOCK_THRESHOLD` only if the old class no longer references it — it does, so keep both until Task 6).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_differential.py -v`
Expected: 5 PASS. Also run `python -m pytest tests/test_agents.py -v` to confirm nothing broke.

- [ ] **Step 5: Commit**

```bash
git add tests/test_differential.py src/pokemon_splendor/agents/differential.py
git commit -m "feat(differential): core economics helpers (shortfall, ppr, card lookup)"
```

---

### Task 2: Color demand + engine quality

**Files:**
- Modify: `src/pokemon_splendor/agents/differential.py`
- Test: `tests/test_differential.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_differential.py`:

```python
# --- Task 2: demand & engine quality ---

def test_board_demand_weighted_by_points():
    from pokemon_splendor.agents.differential import color_demand
    big = make_card(name="big", cost=[Y, Y, Y, Y], point=5)
    small = make_card(name="small", cost=[B, B, B], point=1)
    game = make_game([make_player()], make_board(common=[big, small]))
    d = color_demand(game, game.players[0])
    assert d[Y] > d[B]
    assert abs(sum(d.values()) - 1.0) < 1e-9


def test_zero_point_cards_create_no_board_demand():
    from pokemon_splendor.agents.differential import color_demand
    filler = make_card(name="filler", cost=[K, K], point=0)
    scorer = make_card(name="scorer", cost=[R], point=2)
    game = make_game([make_player()], make_board(common=[filler, scorer]))
    d = color_demand(game, game.players[0])
    assert d[K] == 0.0
    assert d[R] > 0


def test_evolve_demand_uses_point_differential():
    from pokemon_splendor.agents.differential import color_demand
    # Charmander (3pt) held, evolves into Charmeleon (5pt) needing 2 yellow bonuses.
    charmeleon = make_card(name="Charmeleon", tier=Tier.Uncommon, point=5)
    charmander = make_card(name="Charmander", point=3,
                           evolve=[Y, Y], evolve_into="Charmeleon")
    scorer = make_card(name="scorer", cost=[R, R], point=2)
    me = make_player(cards=[charmander])
    game = make_game([me], make_board(common=[scorer], uncommon=[charmeleon]))
    d_with = color_demand(game, me)
    game_no = make_game([make_player()], make_board(common=[scorer], uncommon=[charmeleon]))
    d_without = color_demand(game_no, game_no.players[0])
    # Holding Charmander raises yellow demand (2 missing × w_evo=(5-3)/2=1 each)
    assert d_with[Y] > d_without[Y]


def test_evolve_demand_skips_completed_and_pointless_evolutions():
    from pokemon_splendor.agents.differential import color_demand
    # Already have the 2 yellow bonuses -> no missing -> no demand
    target = make_card(name="T", tier=Tier.Uncommon, point=5)
    src = make_card(name="S", point=3, evolve=[Y, Y], evolve_into="T")
    yb1 = make_card(name="yb1", bonus=[Y])
    yb2 = make_card(name="yb2", bonus=[Y])
    scorer = make_card(name="scorer", cost=[R], point=2)
    me = make_player(cards=[src, yb1, yb2])
    game = make_game([me], make_board(common=[scorer], uncommon=[target]))
    d = color_demand(game, me)
    assert d[Y] == 0.0


def test_engine_quality_rewards_concentration():
    from pokemon_splendor.agents.differential import engine_quality_from
    demand = {c: 0.2 for c in (R, Y, B, P, K)}
    concentrated = Counter({Y: 4})
    spread = Counter({Y: 1, R: 1, B: 1, P: 1})
    assert engine_quality_from(concentrated, demand) > engine_quality_from(spread, demand)


def test_engine_quality_rewards_board_alignment():
    from pokemon_splendor.agents.differential import engine_quality
    yellow_card = make_card(name="yc", cost=[Y, Y, Y, Y], point=4)
    board = make_board(common=[yellow_card])
    yellow_engine = make_player(name="ye", cards=[
        make_card(name=f"y{i}", bonus=[Y]) for i in range(3)])
    blue_engine = make_player(name="be", cards=[
        make_card(name=f"b{i}", bonus=[B]) for i in range(3)])
    game = make_game([yellow_engine, blue_engine], board)
    assert engine_quality(game, yellow_engine) > engine_quality(game, blue_engine)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_differential.py -v -k "demand or engine"`
Expected: FAIL with `ImportError: cannot import name 'color_demand'`

- [ ] **Step 3: Implement**

Append after `find_card_point` in `differential.py`:

```python
def _missing_evolve(player_bonuses: Counter, card: Pokemon) -> Counter:
    needed = Counter(b.name for b in card.evolve)
    return Counter({
        c: cnt - player_bonuses.get(c, 0)
        for c, cnt in needed.items() if cnt - player_bonuses.get(c, 0) > 0
    })


def color_demand(game: Game, player: Player) -> dict[PokeballType, float]:
    bonuses = get_player_bonuses(player)
    demand: Counter = Counter()
    for card in _all_revealed(game):
        if card is None or card.point == 0:
            continue
        ec = calculate_effective_cost(card, bonuses)
        for c, cnt in ec.items():
            demand[c] += card.point * cnt
    for card in player.cards:
        if card.evolved or not card.evolve_into:
            continue
        missing = _missing_evolve(bonuses, card)
        total_missing = sum(missing.values())
        if total_missing == 0:
            continue
        target_point = find_card_point(game, card.evolve_into)
        if target_point is None:
            continue
        w_evo = max(0.0, target_point - card.point) / total_missing
        for c, m in missing.items():
            demand[c] += w_evo * m
    total = sum(demand.values())
    if total <= 0:
        return {c: 0.0 for c in NORMAL_TYPES}
    return {c: demand.get(c, 0.0) / total for c in NORMAL_TYPES}


def engine_quality_from(bonuses: Counter, demand: dict) -> float:
    return sum(
        (bonuses.get(c, 0) ** EXP) * demand.get(c, 0.0) for c in NORMAL_TYPES
    )


def engine_quality(game: Game, player: Player) -> float:
    return engine_quality_from(get_player_bonuses(player), color_demand(game, player))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_differential.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_differential.py src/pokemon_splendor/agents/differential.py
git commit -m "feat(differential): color demand and concentration-aware engine quality"
```

---

### Task 3: Threat model, horizon, endgame, sabotage weight

**Files:**
- Modify: `src/pokemon_splendor/agents/differential.py`
- Test: `tests/test_differential.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_differential.py`:

```python
# --- Task 3: threat / horizon / endgame ---

def _scoring_board():
    return make_board(common=[
        make_card(name="c1", cost=[Y, Y], point=3),
        make_card(name="c2", cost=[R, R], point=2),
    ])


def test_threat_higher_for_player_closer_to_winning():
    from pokemon_splendor.agents.differential import threats
    me = make_player(name="me")
    leader = make_player(name="leader", points=14, tokens=[Y, Y])
    laggard = make_player(name="laggard", points=2)
    game = make_game([me, leader, laggard], _scoring_board())
    t = threats(game, me)
    assert t["leader"] > t["laggard"]
    assert "me" not in t


def test_threat_includes_engine_quality():
    from pokemon_splendor.agents.differential import threats
    me = make_player(name="me")
    engined = make_player(name="engined", cards=[
        make_card(name=f"y{i}", bonus=[Y]) for i in range(4)])
    bare = make_player(name="bare")
    board = make_board(common=[make_card(name="yc", cost=[Y, Y, Y], point=3)])
    game = make_game([me, engined, bare], board)
    t = threats(game, me)
    assert t["engined"] > t["bare"]


def test_endgame_when_player_at_18():
    from pokemon_splendor.agents.differential import is_endgame
    game = make_game([make_player(points=18), make_player(name="o")], _scoring_board())
    assert is_endgame(game)


def test_not_endgame_early():
    from pokemon_splendor.agents.differential import is_endgame
    game = make_game([make_player(), make_player(name="o")], _scoring_board())
    assert not is_endgame(game)


def test_sabotage_weight_grows_with_threat():
    from pokemon_splendor.agents.differential import sabotage_weight, LAMBDA_BASE
    assert sabotage_weight({}) == LAMBDA_BASE
    assert sabotage_weight({"o": 1.0}) > sabotage_weight({"o": 0.3})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_differential.py -v -k "threat or endgame or sabotage"`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement**

Append to `differential.py`:

```python
def scoring_rate(game: Game, player: Player) -> float:
    cards = [c for c in _all_revealed(game) if c is not None and c.point > 0]
    cards += [c for c in player.reserved_cards if c.point > 0]
    rates = sorted((ppr(player, c) for c in cards), reverse=True)
    return sum(rates[:2])


def estimate_horizon(game: Game) -> float:
    best = MAX_HORIZON
    for p in game.players:
        remaining = WIN_POINTS - p.points
        if remaining <= 0:
            return 0.0
        rate = scoring_rate(game, p)
        if rate > 0:
            best = min(best, remaining / rate)
    return max(1.0, best)


def is_endgame(game: Game) -> bool:
    return estimate_horizon(game) <= 1.0


def threats(game: Game, player: Player) -> dict[str, float]:
    horizon = estimate_horizon(game)
    proj = {p.name: p.points + horizon * scoring_rate(game, p) for p in game.players}
    max_proj = max(proj.values())
    eq = {p.name: engine_quality(game, p) for p in game.players}
    max_eq = max(eq.values())
    return {
        p.name:
            ALPHA * (proj[p.name] / max_proj if max_proj > 0 else 0.0)
            + BETA * (eq[p.name] / max_eq if max_eq > 0 else 0.0)
        for p in game.players if p.name != player.name
    }


def sabotage_weight(threat_map: dict[str, float]) -> float:
    if not threat_map:
        return LAMBDA_BASE
    return LAMBDA_BASE + LAMBDA_SCALE * max(threat_map.values())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_differential.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_differential.py src/pokemon_splendor/agents/differential.py
git commit -m "feat(differential): threat model with projected final scores and endgame detection"
```

---

### Task 4: Capture value, evolution unlock, capture harm

**Files:**
- Modify: `src/pokemon_splendor/agents/differential.py`
- Test: `tests/test_differential.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_differential.py`:

```python
# --- Task 4: capture value & harm ---

def test_capture_value_zero_point_bonus_card_positive_via_engine_delta():
    from pokemon_splendor.agents.differential import capture_value
    bonus_card = make_card(name="bc", cost=[Y], bonus=[R], point=0)
    scorer = make_card(name="sc", cost=[R, R, R, R], point=5)
    me = make_player(tokens=[Y])
    game = make_game([me], make_board(common=[bonus_card, scorer]))
    assert capture_value(game, me, bonus_card, endgame=False) > 0


def test_capture_value_endgame_ignores_engine():
    from pokemon_splendor.agents.differential import capture_value
    bonus_card = make_card(name="bc", cost=[Y], bonus=[R], point=0)
    scorer = make_card(name="sc", cost=[R, R, R, R], point=5)
    me = make_player(tokens=[Y])
    game = make_game([me], make_board(common=[bonus_card, scorer]))
    assert capture_value(game, me, bonus_card, endgame=True) == 0.0


def test_capture_value_includes_own_evolution_target():
    from pokemon_splendor.agents.differential import capture_value
    # We hold Charmander (3pt, needs 2 yellow bonuses we already have);
    # capturing Charmeleon (5pt) banks a +2 differential evolution.
    charmeleon = make_card(name="Charmeleon", tier=Tier.Uncommon, cost=[R], point=5)
    other = make_card(name="other", tier=Tier.Uncommon, cost=[R], point=5)
    charmander = make_card(name="Charmander", point=3, evolve=[Y, Y],
                           evolve_into="Charmeleon")
    yb = [make_card(name=f"y{i}", bonus=[Y]) for i in range(2)]
    me = make_player(tokens=[R], cards=[charmander] + yb)
    game = make_game([me], make_board(uncommon=[charmeleon, other]))
    v_target = capture_value(game, me, charmeleon, endgame=False)
    v_other = capture_value(game, me, other, endgame=False)
    assert v_target > v_other


def test_harm_capture_scales_with_opponent_threat_and_ppr():
    from pokemon_splendor.agents.differential import harm_capture
    card = make_card(name="hot", cost=[Y, Y], point=5)
    me = make_player(name="me")
    opp = make_player(name="opp", tokens=[Y, Y])  # can afford it now
    game = make_game([me, opp], make_board(common=[card]))
    h = harm_capture(game, me, card, {"opp": 1.0})
    h_low = harm_capture(game, me, card, {"opp": 0.1})
    assert h > h_low > 0


def test_harm_capture_evolution_target_denial():
    from pokemon_splendor.agents.differential import harm_capture
    # Opponent holds Charmander with bonuses nearly complete; Charmeleon on board.
    charmeleon = make_card(name="Charmeleon", tier=Tier.Uncommon, cost=[R, R, R, R, R], point=5)
    charmander = make_card(name="Charmander", point=3, evolve=[Y, Y],
                           evolve_into="Charmeleon")
    yb = [make_card(name=f"y{i}", bonus=[Y]) for i in range(2)]
    me = make_player(name="me")
    opp = make_player(name="opp", cards=[charmander] + yb)
    game = make_game([me, opp], make_board(uncommon=[charmeleon]))
    h = harm_capture(game, me, charmeleon, {"opp": 1.0})
    # Denial worth at least E × threat × point differential (2), beating plain ppr harm
    assert h >= 2.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_differential.py -v -k "capture"`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement**

Append to `differential.py`:

```python
def evo_unlock(game: Game, player: Player, card: Pokemon) -> float:
    """Value of card being the evolve target of a card we hold.
    Bonus-color progress toward evolutions is already credited via
    engine_delta (demand includes evolve demand), so only the
    target-capture case is scored here."""
    bonuses = get_player_bonuses(player)
    value = 0.0
    for held in player.cards:
        if held.evolved or held.evolve_into != card.name:
            continue
        diff = max(0, card.point - held.point)
        missing = sum(_missing_evolve(bonuses, held).values())
        value += diff / (1 + missing)
    return value


def capture_value(game: Game, player: Player, card: Pokemon, endgame: bool) -> float:
    v = ppr(player, card)
    if not endgame:
        demand = color_demand(game, player)
        bonuses = get_player_bonuses(player)
        new_bonuses = bonuses.copy()
        for b in card.bonus:
            new_bonuses[b.name] += 1
        v += engine_quality_from(new_bonuses, demand) - engine_quality_from(bonuses, demand)
        v += evo_unlock(game, player, card)
    return v


def harm_capture(game: Game, player: Player, card: Pokemon,
                 threat_map: dict[str, float]) -> float:
    h = 0.0
    for opp in game.players:
        t = threat_map.get(opp.name)
        if t is None:
            continue
        h = max(h, t * ppr(opp, card))
        opp_bonuses = get_player_bonuses(opp)
        for held in opp.cards:
            if held.evolved or held.evolve_into != card.name:
                continue
            diff = max(0, card.point - held.point)
            if sum(_missing_evolve(opp_bonuses, held).values()) <= 1:
                h = max(h, E_EVO_DENIAL * t * diff)
    return h
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_differential.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_differential.py src/pokemon_splendor/agents/differential.py
git commit -m "feat(differential): capture value with engine delta, evolution unlock and denial harm"
```

---

### Task 5: Token-take value and token denial harm

**Files:**
- Modify: `src/pokemon_splendor/agents/differential.py`
- Test: `tests/test_differential.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_differential.py`:

```python
# --- Task 5: token helpers ---

def test_predicted_buy_picks_best_ppr_card():
    from pokemon_splendor.agents.differential import predicted_buy
    cheap = make_card(name="cheap", cost=[Y], point=2)
    expensive = make_card(name="exp", cost=[B] * 7, point=3)
    opp = make_player(name="opp", tokens=[Y])
    game = make_game([make_player(), opp], make_board(common=[cheap, expensive]))
    assert predicted_buy(game, opp).name == "cheap"


def test_harm_tokens_only_when_scarce_and_needed():
    from pokemon_splendor.agents.differential import harm_tokens
    target = make_card(name="t", cost=[Y, Y], point=4)
    me = make_player(name="me")
    opp = make_player(name="opp")
    # yellow scarce (2 left), red plentiful
    game = make_game([me, opp], make_board(common=[target]),
                     tokens={PokeballType.Yellow: 2, PokeballType.Red: 5})
    tm = {"opp": 1.0}
    assert harm_tokens(game, me, Counter({Y: 1}), tm) > 0
    assert harm_tokens(game, me, Counter({R: 1}), tm) == 0.0


def test_harm_tokens_zero_when_supply_plentiful():
    from pokemon_splendor.agents.differential import harm_tokens
    target = make_card(name="t", cost=[Y, Y], point=4)
    me = make_player(name="me")
    opp = make_player(name="opp")
    game = make_game([me, opp], make_board(common=[target]),
                     tokens={PokeballType.Yellow: 5})
    assert harm_tokens(game, me, Counter({Y: 1}), {"opp": 1.0}) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_differential.py -v -k token`
Expected: FAIL with ImportError (`predicted_buy`)

- [ ] **Step 3: Implement**

Append to `differential.py`:

```python
def predicted_buy(game: Game, opp: Player) -> Pokemon | None:
    cards = [c for c in _all_revealed(game) if c is not None and c.point > 0]
    cards += [c for c in opp.reserved_cards if c.point > 0]
    if not cards:
        return None
    return max(cards, key=lambda c: ppr(opp, c))


def harm_tokens(game: Game, player: Player, taken: Counter,
                threat_map: dict[str, float]) -> float:
    h = 0.0
    for opp in game.players:
        t = threat_map.get(opp.name)
        if t is None:
            continue
        target = predicted_buy(game, opp)
        if target is None:
            continue
        need = token_shortfall(opp, target)
        for c, cnt in taken.items():
            if need.get(c, 0) > 0 and game.tokens.get(c, 0) <= SCARCE_SUPPLY:
                h += TOKEN_HARM * t * min(cnt, need[c])
    return h
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_differential.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_differential.py src/pokemon_splendor/agents/differential.py
git commit -m "feat(differential): token denial harm with scarcity gating"
```

---

### Task 6: Rewrite DifferentialAgent (argmax policy + evolve override)

**Files:**
- Modify: `src/pokemon_splendor/agents/differential.py` (replace the old class entirely; delete `_BLOCK_THRESHOLD` and the old methods)
- Test: `tests/test_differential.py`

- [ ] **Step 1: Write failing behavioral tests**

Append to `tests/test_differential.py`. `DifferentialAgent` only reads `self._env.game`, so a fake env suffices:

```python
# --- Task 6: agent policy ---

from pokemon_splendor.engine.actions import (
    TOTAL_ACTIONS, TAKE_DIFF_START, TAKE_DIFF_COMBOS, TAKE_SAME_ACTION,
    CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START, EVOLVE_START, EVOLVE_PASS,
)


class FakeEnv:
    def __init__(self, game):
        self.game = game


def make_agent(game, name="me"):
    from pokemon_splendor.agents.differential import DifferentialAgent
    return DifferentialAgent(FakeEnv(game), name)


def empty_mask():
    return np.zeros(TOTAL_ACTIONS, dtype=bool)


def test_buys_affordable_point_card_over_blocking():
    # We can buy a solid 4pt card; opponent also wants a card. Buying must win.
    mine = make_card(name="mine", cost=[Y], point=4)
    theirs = make_card(name="theirs", cost=[R, R], point=3)
    me = make_player(name="me", tokens=[Y])
    opp = make_player(name="opp", tokens=[R, R])
    game = make_game([me, opp], make_board(common=[mine, theirs]))
    mask = empty_mask()
    mask[CATCH_BOARD_START + 0] = True          # buy mine (slot 0)
    mask[RESERVE_NO_MASTER_START + 1] = True    # block theirs (slot 1)
    mask[TAKE_DIFF_START] = True
    agent = make_agent(game)
    assert agent.act(None, mask) == CATCH_BOARD_START + 0


def test_block_reserves_when_opponent_about_to_score_big():
    # We can't buy anything; high-threat opponent can afford a 5pt card now.
    hot = make_card(name="hot", tier=Tier.Rare, cost=[R, R], point=5)
    me = make_player(name="me")
    opp = make_player(name="opp", tokens=[R, R], points=14)
    game = make_game([me, opp], make_board(rare=[hot]))
    mask = empty_mask()
    mask[RESERVE_NO_MASTER_START + 8] = True    # rare slot 0 = reservable index 8
    for i in range(len(TAKE_DIFF_COMBOS)):
        mask[TAKE_DIFF_START + i] = True
    agent = make_agent(game)
    assert agent.act(None, mask) == RESERVE_NO_MASTER_START + 8


def test_takes_tokens_toward_target_when_nothing_to_buy_or_block():
    target = make_card(name="t", cost=[Y, Y, B], point=4)
    me = make_player(name="me")
    opp = make_player(name="opp")
    game = make_game([me, opp], make_board(common=[target]))
    mask = empty_mask()
    for i in range(len(TAKE_DIFF_COMBOS)):
        mask[TAKE_DIFF_START + i] = True
    agent = make_agent(game)
    action = agent.act(None, mask)
    combo = TAKE_DIFF_COMBOS[action - TAKE_DIFF_START]
    # Must take yellow and blue (the needed colors)
    assert Y in combo and B in combo


def test_evolve_picks_largest_point_differential():
    from pokemon_splendor.models import GamePhase
    # Two evolutions available: +1 diff and +4 diff. Pick +4.
    small_t = make_card(name="SmallT", tier=Tier.Uncommon, point=3)
    big_t = make_card(name="BigT", tier=Tier.Uncommon, point=6)
    small_s = make_card(name="SmallS", point=2, evolve=[Y], evolve_into="SmallT")
    big_s = make_card(name="BigS", point=2, evolve=[Y], evolve_into="BigT")
    yb = make_card(name="yb", bonus=[Y])
    me = make_player(name="me", cards=[small_s, big_s, yb])
    opp = make_player(name="opp")
    game = make_game([me, opp], make_board(uncommon=[small_t, big_t]))
    game.phase = GamePhase.EVOLVE
    mask = empty_mask()
    mask[EVOLVE_START + 0] = True   # SmallS
    mask[EVOLVE_START + 1] = True   # BigS
    mask[EVOLVE_PASS] = True
    agent = make_agent(game)
    assert agent.act(None, mask) == EVOLVE_START + 1


def test_fallback_first_legal_action():
    me = make_player(name="me")
    opp = make_player(name="opp")
    game = make_game([me, opp], make_board())
    mask = empty_mask()
    mask[TAKE_DIFF_START + 3] = True
    agent = make_agent(game)
    assert agent.act(None, mask) == TAKE_DIFF_START + 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_differential.py -v -k "buys or block or takes_tokens or evolve_picks or fallback"`
Expected: FAIL (old class behaves differently / lacks evolve override)

- [ ] **Step 3: Replace the class**

Delete `_BLOCK_THRESHOLD` and the entire old `DifferentialAgent` class. Replace with:

```python
class DifferentialAgent(RuleBasedAgent):
    """Deterministic agent scoring every legal action as
    self_value + lambda * harm, where lambda scales with the most
    threatening opponent. Sabotage (block-reserve, token denial,
    evolution-target denial) wins the argmax only when its weighted
    harm exceeds the best self-progress alternative."""

    def _main_action(self, mask: np.ndarray) -> int:
        game, player = self._game, self._player
        endgame = is_endgame(game)
        threat_map = threats(game, player)
        lam = sabotage_weight(threat_map)
        delta = ENDGAME_DELTA if endgame else DELTA

        all_slots = _all_revealed(game)
        reservable = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed
        )

        best_action, best_score = None, float("-inf")

        def consider(action: int, score: float) -> None:
            nonlocal best_action, best_score
            if score > best_score:
                best_score = score
                best_action = action

        # Card count breaks point ties at game end, so nudge captures in endgame
        card_nudge = 0.01 if endgame else 0.0

        # --- Captures (board + own reserve) ---
        for i, card in enumerate(all_slots):
            a = CATCH_BOARD_START + i
            if card is None or not mask[a]:
                continue
            consider(a, capture_value(game, player, card, endgame) + card_nudge
                     + lam * harm_capture(game, player, card, threat_map))
        for i, card in enumerate(player.reserved_cards):
            a = CATCH_RESERVED_START + i
            if not mask[a]:
                continue
            consider(a, capture_value(game, player, card, endgame) + card_nudge
                     + lam * harm_capture(game, player, card, threat_map))

        # --- Reserves ---
        penalty = SLOT_PENALTY[min(len(player.reserved_cards), 2)]
        for i, card in enumerate(reservable):
            if card is None:
                continue
            am = RESERVE_MASTER_START + i
            an = RESERVE_NO_MASTER_START + i
            if not (mask[am] or mask[an]):
                continue
            base = (delta * capture_value(game, player, card, endgame)
                    - penalty
                    + lam * harm_capture(game, player, card, threat_map))
            if mask[am]:
                consider(am, base + MASTER_BONUS)
            if mask[an]:
                consider(an, base)

        # --- Token takes ---
        target = self._token_target(endgame)
        need, total_short, target_value = Counter(), 0, 0.0
        if target is not None:
            need = token_shortfall(player, target)
            total_short = sum(need.values())
            target_value = capture_value(game, player, target, endgame)

        def token_score(taken: Counter) -> float:
            sv = 0.0
            if total_short > 0:
                progress = sum(min(need.get(c, 0), n) for c, n in taken.items())
                sv = target_value * TOKEN_FACTOR * progress / total_short
                if progress >= total_short:
                    sv *= URGENCY
            return sv + lam * harm_tokens(game, player, taken, threat_map)

        for i, combo in enumerate(TAKE_DIFF_COMBOS):
            a = TAKE_DIFF_START + i
            if mask[a]:
                consider(a, token_score(Counter(combo)))
        for pt, a in TAKE_SAME_ACTION.items():
            if mask[a]:
                consider(a, token_score(Counter({pt: 2})))

        if best_action is not None:
            return best_action
        return int(np.where(mask)[0][0])

    def _token_target(self, endgame: bool) -> Pokemon | None:
        game, player = self._game, self._player
        candidates = [c for c in _all_revealed(game) if c is not None]
        candidates += list(player.reserved_cards)
        unaffordable = [c for c in candidates if sum(token_shortfall(player, c).values()) > 0]
        if not unaffordable:
            return None
        return max(unaffordable, key=lambda c: capture_value(game, player, c, endgame))

    def _handle_evolve(self, mask: np.ndarray) -> int:
        game, player = self._game, self._player
        best_a, best_diff = None, 0
        for source, target in get_evolvable_cards(game, player):
            idx = next(i for i, c in enumerate(player.cards) if c is source)
            a = EVOLVE_START + idx
            if not mask[a]:
                continue
            diff = target.point - source.point
            if diff > best_diff:
                best_diff = diff
                best_a = a
        if best_a is not None:
            return best_a
        if mask[EVOLVE_PASS]:
            return EVOLVE_PASS
        return int(np.where(mask)[0][0])
```

- [ ] **Step 4: Run the full test suite**

Run: `python -m pytest tests/test_differential.py tests/test_agents.py -v`
Expected: all PASS. If a behavioral test fails, debug by printing per-action scores (temporary), but do NOT special-case the policy — adjust weights only if a weight is clearly mis-scaled, and note the change for the spec's tunables table.

- [ ] **Step 5: Smoke-test in real games**

Run: `python -m pokemon_splendor --mode benchmark --players differential,random --games 20`
Expected: completes without exceptions; differential wins the large majority vs random.

- [ ] **Step 6: Commit**

```bash
git add tests/test_differential.py src/pokemon_splendor/agents/differential.py
git commit -m "feat(differential): rewrite as unified threat-weighted argmax agent"
```

---

### Task 7: Benchmark gate vs DenialAgent (+ weight tuning if needed)

**Files:**
- Modify (only if tuning needed): `src/pokemon_splendor/agents/differential.py` (weight constants)

- [ ] **Step 1: Run the primary benchmark**

Run: `python -m pokemon_splendor --mode benchmark --players differential,denial --games 200`

Note the win counts printed at the end. Success criterion: differential > 50% (i.e., >100 wins of 200; ignore exact seat assignment — the benchmark alternates/aggregates per its existing implementation in `__main__.py:_run_benchmark`).

- [ ] **Step 2: If below 50%, tune weights**

One change at a time, re-running 200 games after each. Order of suspects:

1. `LAMBDA_SCALE` (1.0): if differential wastes turns sabotaging, halve it; if it never sabotages a denial-heavy opponent, raise to 1.5.
2. `TOKEN_FACTOR` (0.8) / `URGENCY` (1.5): if it hoards tokens instead of buying, lower TOKEN_FACTOR to 0.6.
3. `BETA` (0.5): if it overrates engines and ignores point leaders, lower to 0.3.
4. `DELTA` (0.6): if it over-reserves, lower to 0.4.
5. `SLOT_PENALTY[1]` (0.2): raise to 0.5 if it fills reserve slots early.

Keep the final values as the module constants; update the tunables table in the spec doc if they changed.

- [ ] **Step 3: Secondary sanity benchmarks**

```bash
python -m pokemon_splendor --mode benchmark --players differential,bonus_engine --games 100
python -m pokemon_splendor --mode benchmark --players differential,high_point --games 100
python -m pokemon_splendor --mode benchmark --players differential,denial,bonus_engine,high_point --games 100
```

Expected: ≥50% vs each 2p opponent; highest win count in the 4p mix. These are informational, not gates — record results in the final summary.

- [ ] **Step 4: Run the entire test suite once more**

Run: `python -m pytest tests/ -v --ignore=tests/server --ignore=tests/article_export`
Expected: all PASS

- [ ] **Step 5: Commit final weights and results**

```bash
git add src/pokemon_splendor/agents/differential.py docs/superpowers/specs/2026-06-10-differential-agent-rewrite-design.md
git commit -m "feat(differential): tune weights to beat DenialAgent >50% over 200 games"
```

Include the measured win rates in the commit body.
