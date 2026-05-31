# Pokémon Splendor — Game Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Pokémon Splendor game engine: data models, JSONL loader, action encoding, game rules, PettingZoo AEC environment, CLI renderer, and entry point.

**Architecture:** Pure dataclasses in `models.py`; pure rule functions in `engine/rules.py`; `PokemonSplendorEnv(AECEnv)` in `engine/env.py` owns all state and calls rules; agents plug in via a single `act(obs, mask) -> int` interface.

**Tech Stack:** Python 3.11+, uv, pettingzoo, gymnasium, numpy, stable-baselines3, rich, pytest.

---

## File Map

- `pyproject.toml`
- `data/pokemon.jsonl`
- `src/pokemon_splendor/__init__.py`
- `src/pokemon_splendor/models.py`
- `src/pokemon_splendor/data/__init__.py`
- `src/pokemon_splendor/data/loader.py`
- `src/pokemon_splendor/engine/__init__.py`
- `src/pokemon_splendor/engine/actions.py`
- `src/pokemon_splendor/engine/rules.py`
- `src/pokemon_splendor/engine/env.py`
- `src/pokemon_splendor/cli/__init__.py`
- `src/pokemon_splendor/cli/renderer.py`
- `src/pokemon_splendor/__main__.py`
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_loader.py`
- `tests/test_rules.py`
- `tests/test_game.py`

---

## Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `data/pokemon.jsonl`
- Create: all `__init__.py` files and empty module stubs

- [ ] **Step 1: Initialise uv project**

```bash
cd /Users/alan/code/splendor
uv init --name pokemon-splendor --python 3.11
rm hello.py  # remove uv default file
```

- [ ] **Step 2: Write `pyproject.toml`**

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
    "torch>=2.2.0",
    "rich>=13.0.0",
]

[project.scripts]
pokemon-splendor = "pokemon_splendor.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]

[dependency-groups]
dev = ["pytest>=8.0.0"]
```

- [ ] **Step 3: Create directory structure**

```bash
mkdir -p src/pokemon_splendor/engine
mkdir -p src/pokemon_splendor/data
mkdir -p src/pokemon_splendor/cli
mkdir -p src/pokemon_splendor/agents
mkdir -p tests
touch src/pokemon_splendor/__init__.py
touch src/pokemon_splendor/engine/__init__.py
touch src/pokemon_splendor/data/__init__.py
touch src/pokemon_splendor/cli/__init__.py
touch src/pokemon_splendor/agents/__init__.py
touch tests/__init__.py
```

- [ ] **Step 4: Create minimal `data/pokemon.jsonl`**

```jsonl
{"name": "charmander", "tier": "common", "cost": {"red": 2}, "bonus": {"red": 1}, "evolve": {"red": 2}, "evolve_into": "charmeleon", "point": 0}
{"name": "charmeleon", "tier": "uncommon", "cost": {"red": 3}, "bonus": {"red": 2}, "evolve": {"red": 3}, "evolve_into": "charizard", "point": 1}
{"name": "charizard", "tier": "rare", "cost": {"red": 4}, "bonus": {"red": 3}, "evolve": {}, "evolve_into": "", "point": 3}
{"name": "squirtle", "tier": "common", "cost": {"blue": 2}, "bonus": {"blue": 1}, "evolve": {"blue": 2}, "evolve_into": "wartortle", "point": 0}
{"name": "wartortle", "tier": "uncommon", "cost": {"blue": 3}, "bonus": {"blue": 2}, "evolve": {}, "evolve_into": "", "point": 1}
{"name": "bulbasaur", "tier": "common", "cost": {"yellow": 2}, "bonus": {"yellow": 1}, "evolve": {}, "evolve_into": "", "point": 0}
{"name": "pikachu", "tier": "common", "cost": {"yellow": 1, "red": 1}, "bonus": {"pink": 1}, "evolve": {}, "evolve_into": "", "point": 0}
{"name": "mewtwo", "tier": "epic", "cost": {"master": 1, "red": 3, "blue": 3}, "bonus": {"red": 3}, "evolve": {}, "evolve_into": "", "point": 8}
{"name": "rayquaza", "tier": "legendary", "cost": {"master": 1, "red": 4, "blue": 4}, "bonus": {"blue": 3}, "evolve": {}, "evolve_into": "", "point": 12}
{"name": "eevee", "tier": "common", "cost": {"pink": 2}, "bonus": {"pink": 1}, "evolve": {}, "evolve_into": "", "point": 0}
{"name": "geodude", "tier": "common", "cost": {"black": 2}, "bonus": {"black": 1}, "evolve": {}, "evolve_into": "", "point": 0}
{"name": "gastly", "tier": "uncommon", "cost": {"black": 2, "pink": 1}, "bonus": {"black": 1}, "evolve": {}, "evolve_into": "", "point": 1}
{"name": "vaporeon", "tier": "rare", "cost": {"blue": 3, "pink": 2}, "bonus": {"blue": 2}, "evolve": {}, "evolve_into": "", "point": 4}
{"name": "flareon", "tier": "rare", "cost": {"red": 3, "yellow": 2}, "bonus": {"red": 2}, "evolve": {}, "evolve_into": "", "point": 4}
```

- [ ] **Step 5: Install dependencies**

```bash
uv sync --dev
```

Expected: dependencies installed with no errors.

- [ ] **Step 6: Commit**

```bash
git init
git add .
git commit -m "chore: initialise project structure and dependencies"
```

---

## Task 2: Data Models

**Files:**
- Create: `src/pokemon_splendor/models.py`

- [ ] **Step 1: Write `models.py`**

```python
from dataclasses import dataclass, field
from enum import Enum


class PokeballType(Enum):
    Red = "red"
    Yellow = "yellow"
    Blue = "blue"
    Pink = "pink"
    Black = "black"
    Master = "master"


@dataclass
class PokeballToken:
    name: PokeballType


@dataclass
class Bonus(PokeballToken):
    pass


class Tier(Enum):
    Common = "common"
    Uncommon = "uncommon"
    Rare = "rare"
    Epic = "epic"
    Legendary = "legendary"


class GamePhase(Enum):
    MAIN = "main"
    DISCARD = "discard"
    EVOLVE = "evolve"


@dataclass
class Pokemon:
    name: str
    tier: Tier
    cost: list[PokeballToken]
    bonus: list[Bonus]
    evolve: list[Bonus]
    evolve_into: str
    point: int
    evolved: bool = False


@dataclass
class Player:
    name: str
    tokens: list[PokeballToken] = field(default_factory=list)
    cards: list[Pokemon] = field(default_factory=list)
    reserved_cards: list[Pokemon] = field(default_factory=list)
    points: int = 0


@dataclass
class Board:
    common_deck: list[Pokemon] = field(default_factory=list)
    uncommon_deck: list[Pokemon] = field(default_factory=list)
    rare_deck: list[Pokemon] = field(default_factory=list)
    epic_deck: list[Pokemon] = field(default_factory=list)
    legendary_deck: list[Pokemon] = field(default_factory=list)
    common_revealed: list[Pokemon | None] = field(default_factory=lambda: [None] * 4)
    uncommon_revealed: list[Pokemon | None] = field(default_factory=lambda: [None] * 4)
    rare_revealed: list[Pokemon | None] = field(default_factory=lambda: [None] * 4)
    epic_revealed: list[Pokemon | None] = field(default_factory=lambda: [None] * 1)
    legendary_revealed: list[Pokemon | None] = field(default_factory=lambda: [None] * 1)


@dataclass
class Game:
    players: list[Player]
    turn: Player
    starting_player: Player
    round: int
    board: Board
    tokens: dict[PokeballType, int]
    phase: GamePhase = GamePhase.MAIN
    evolved_this_turn: bool = False
    win_triggered: bool = False
    winner: Player | None = None
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from pokemon_splendor.models import Game, Pokemon, Board, Player, PokeballType; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/pokemon_splendor/models.py
git commit -m "feat: add data models"
```

---

## Task 3: JSONL Loader

**Files:**
- Create: `src/pokemon_splendor/data/loader.py`
- Create: `tests/test_loader.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_loader.py
import pytest
from pathlib import Path
from pokemon_splendor.data.loader import load_pokemon
from pokemon_splendor.models import Tier, PokeballType


SAMPLE_JSONL = """\
{"name": "charmander", "tier": "common", "cost": {"red": 2}, "bonus": {"red": 1}, "evolve": {"red": 2}, "evolve_into": "charmeleon", "point": 0}
{"name": "mewtwo", "tier": "epic", "cost": {"master": 1, "red": 3}, "bonus": {}, "evolve": {}, "evolve_into": "", "point": 8}
"""


@pytest.fixture
def jsonl_file(tmp_path):
    f = tmp_path / "pokemon.jsonl"
    f.write_text(SAMPLE_JSONL)
    return f


def test_loads_correct_count(jsonl_file):
    pokemon = load_pokemon(jsonl_file)
    assert len(pokemon) == 2


def test_fields_parsed_correctly(jsonl_file):
    pokemon = load_pokemon(jsonl_file)
    charm = next(p for p in pokemon if p.name == "charmander")
    assert charm.tier == Tier.Common
    assert charm.point == 0
    assert charm.evolve_into == "charmeleon"
    assert charm.evolved is False


def test_cost_expanded_to_list(jsonl_file):
    pokemon = load_pokemon(jsonl_file)
    charm = next(p for p in pokemon if p.name == "charmander")
    types_in_cost = [t.name for t in charm.cost]
    assert types_in_cost.count(PokeballType.Red) == 2


def test_bonus_expanded_to_list(jsonl_file):
    pokemon = load_pokemon(jsonl_file)
    charm = next(p for p in pokemon if p.name == "charmander")
    assert len(charm.bonus) == 1
    assert charm.bonus[0].name == PokeballType.Red


def test_missing_optional_fields_default_empty(tmp_path):
    f = tmp_path / "p.jsonl"
    f.write_text('{"name": "ditto", "tier": "common", "cost": {}, "point": 0}\n')
    pokemon = load_pokemon(f)
    assert pokemon[0].bonus == []
    assert pokemon[0].evolve == []
    assert pokemon[0].evolve_into == ""


def test_invalid_tier_raises(tmp_path):
    f = tmp_path / "p.jsonl"
    f.write_text('{"name": "bad", "tier": "godlike", "cost": {}, "point": 0}\n')
    with pytest.raises(ValueError, match="Invalid tier"):
        load_pokemon(f)


def test_missing_required_field_raises(tmp_path):
    f = tmp_path / "p.jsonl"
    f.write_text('{"name": "bad"}\n')
    with pytest.raises(ValueError, match="Missing required field"):
        load_pokemon(f)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
uv run pytest tests/test_loader.py -v
```

Expected: all FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement `loader.py`**

```python
# src/pokemon_splendor/data/loader.py
import json
from pathlib import Path
from pokemon_splendor.models import Pokemon, Tier, PokeballToken, Bonus, PokeballType


def _expand_token_dict(d: dict, cls: type) -> list:
    tokens = []
    for color, count in d.items():
        try:
            ptype = PokeballType(color)
        except ValueError:
            raise ValueError(f"Invalid token type: {color}")
        tokens.extend([cls(ptype)] * count)
    return tokens


def load_pokemon(path: Path) -> list[Pokemon]:
    pokemon = []
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Line {lineno}: invalid JSON: {e}")

            for field in ("name", "tier", "cost", "point"):
                if field not in data:
                    raise ValueError(f"Missing required field '{field}' on line {lineno}")

            try:
                tier = Tier(data["tier"])
            except ValueError:
                raise ValueError(f"Invalid tier '{data['tier']}' on line {lineno}")

            pokemon.append(Pokemon(
                name=data["name"],
                tier=tier,
                cost=_expand_token_dict(data.get("cost", {}), PokeballToken),
                bonus=_expand_token_dict(data.get("bonus", {}), Bonus),
                evolve=_expand_token_dict(data.get("evolve", {}), Bonus),
                evolve_into=data.get("evolve_into", ""),
                point=data["point"],
            ))
    return pokemon
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_loader.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pokemon_splendor/data/loader.py tests/test_loader.py
git commit -m "feat: add JSONL loader with validation"
```

---

## Task 4: Action Encoding

**Files:**
- Create: `src/pokemon_splendor/engine/actions.py`
- Create: `tests/test_actions.py`

- [ ] **Step 1: Write `actions.py`**

```python
# src/pokemon_splendor/engine/actions.py
from itertools import combinations
from pokemon_splendor.models import PokeballType, Tier

NORMAL_TYPES = [
    PokeballType.Red,
    PokeballType.Yellow,
    PokeballType.Blue,
    PokeballType.Pink,
    PokeballType.Black,
]

# Precompute all take-different combos (size 1, 2, 3)
TAKE_DIFF_COMBOS: list[tuple[PokeballType, ...]] = [
    combo
    for size in range(1, 4)
    for combo in combinations(NORMAL_TYPES, size)
]
assert len(TAKE_DIFF_COMBOS) == 25

# Action index ranges
TAKE_DIFF_START = 0          # 0–24  (25 actions)
TAKE_SAME_START = 25         # 25–29 (5 actions)
CATCH_BOARD_START = 30       # 30–43 (14 actions)
CATCH_RESERVED_START = 44    # 44–46 (3 actions)
RESERVE_MASTER_START = 47    # 47–58 (12 actions)
RESERVE_NO_MASTER_START = 59 # 59–70 (12 actions)
DISCARD_START = 71           # 71–76 (6 actions, one per PokeballType)
EVOLVE_START = 77            # 77–106 (30 slots)
EVOLVE_PASS = 107            # pass evolution

TOTAL_ACTIONS = 108
MAX_OWNED_CARDS = 30  # upper bound for evolve action slots

# Board slot layout for CATCH_BOARD and RESERVE actions
# Slots 0–3: common, 4–7: uncommon, 8–11: rare, 12: epic, 13: legendary
BOARD_SLOT_TIERS = (
    [Tier.Common] * 4
    + [Tier.Uncommon] * 4
    + [Tier.Rare] * 4
    + [Tier.Epic]
    + [Tier.Legendary]
)

RESERVABLE_TIERS = {Tier.Common, Tier.Uncommon, Tier.Rare}

# Maps PokeballType to its DISCARD action index
DISCARD_ACTION = {ptype: DISCARD_START + i for i, ptype in enumerate(PokeballType)}
# Maps PokeballType to its TAKE_SAME action index
TAKE_SAME_ACTION = {ptype: TAKE_SAME_START + i for i, ptype in enumerate(NORMAL_TYPES)}
```

- [ ] **Step 2: Write tests**

```python
# tests/test_actions.py
from pokemon_splendor.engine.actions import (
    TAKE_DIFF_COMBOS, TOTAL_ACTIONS, BOARD_SLOT_TIERS,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START,
    CATCH_RESERVED_START, RESERVE_MASTER_START, RESERVE_NO_MASTER_START,
    DISCARD_START, EVOLVE_START, EVOLVE_PASS,
)
from pokemon_splendor.models import PokeballType, Tier


def test_take_diff_combo_count():
    assert len(TAKE_DIFF_COMBOS) == 25


def test_take_diff_no_master():
    for combo in TAKE_DIFF_COMBOS:
        assert PokeballType.Master not in combo


def test_take_diff_all_unique_types_per_combo():
    for combo in TAKE_DIFF_COMBOS:
        assert len(set(combo)) == len(combo)


def test_board_slot_count():
    assert len(BOARD_SLOT_TIERS) == 14


def test_epic_legendary_slots():
    assert BOARD_SLOT_TIERS[12] == Tier.Epic
    assert BOARD_SLOT_TIERS[13] == Tier.Legendary


def test_total_actions():
    assert TOTAL_ACTIONS == 108


def test_action_ranges_non_overlapping():
    ranges = [
        range(TAKE_DIFF_START, TAKE_SAME_START),
        range(TAKE_SAME_START, CATCH_BOARD_START),
        range(CATCH_BOARD_START, CATCH_RESERVED_START),
        range(CATCH_RESERVED_START, RESERVE_MASTER_START),
        range(RESERVE_MASTER_START, RESERVE_NO_MASTER_START),
        range(RESERVE_NO_MASTER_START, DISCARD_START),
        range(DISCARD_START, EVOLVE_START),
        range(EVOLVE_START, EVOLVE_PASS),
    ]
    all_indices = [i for r in ranges for i in r] + [EVOLVE_PASS]
    assert len(all_indices) == len(set(all_indices)) == TOTAL_ACTIONS
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/test_actions.py -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add src/pokemon_splendor/engine/actions.py tests/test_actions.py
git commit -m "feat: add action encoding constants"
```

---

## Task 5: Game Rules

**Files:**
- Create: `src/pokemon_splendor/engine/rules.py`
- Create: `tests/conftest.py`
- Create: `tests/test_rules.py`

- [ ] **Step 1: Write `conftest.py` fixtures**

```python
# tests/conftest.py
import pytest
from pokemon_splendor.models import (
    Pokemon, Player, Board, Game, Tier, PokeballType, PokeballToken, Bonus, GamePhase,
)


def make_token(ptype: PokeballType) -> PokeballToken:
    return PokeballToken(ptype)


def make_bonus(ptype: PokeballType) -> Bonus:
    return Bonus(ptype)


def tokens(*types: PokeballType) -> list[PokeballToken]:
    return [make_token(t) for t in types]


def bonuses(*types: PokeballType) -> list[Bonus]:
    return [make_bonus(t) for t in types]


@pytest.fixture
def charmander():
    return Pokemon(
        name="charmander", tier=Tier.Common,
        cost=tokens(PokeballType.Red, PokeballType.Red),
        bonus=bonuses(PokeballType.Red),
        evolve=bonuses(PokeballType.Red, PokeballType.Red),
        evolve_into="charmeleon", point=0,
    )


@pytest.fixture
def charmeleon():
    return Pokemon(
        name="charmeleon", tier=Tier.Uncommon,
        cost=tokens(PokeballType.Red, PokeballType.Red, PokeballType.Red),
        bonus=bonuses(PokeballType.Red, PokeballType.Red),
        evolve=bonuses(PokeballType.Red, PokeballType.Red, PokeballType.Red),
        evolve_into="charizard", point=1,
    )


@pytest.fixture
def squirtle():
    return Pokemon(
        name="squirtle", tier=Tier.Common,
        cost=tokens(PokeballType.Blue, PokeballType.Blue),
        bonus=bonuses(PokeballType.Blue),
        evolve=[], evolve_into="", point=0,
    )


@pytest.fixture
def mewtwo():
    return Pokemon(
        name="mewtwo", tier=Tier.Epic,
        cost=tokens(PokeballType.Master, PokeballType.Red, PokeballType.Red, PokeballType.Red),
        bonus=[], evolve=[], evolve_into="", point=8,
    )


@pytest.fixture
def two_player_game(charmander, squirtle, charmeleon):
    p1 = Player(name="Alice")
    p2 = Player(name="Bob")
    board = Board(
        common_revealed=[charmander, squirtle, None, None],
        uncommon_revealed=[charmeleon, None, None, None],
    )
    game = Game(
        players=[p1, p2],
        turn=p1,
        starting_player=p1,
        round=1,
        board=board,
        tokens={
            PokeballType.Red: 4,
            PokeballType.Yellow: 4,
            PokeballType.Blue: 4,
            PokeballType.Pink: 4,
            PokeballType.Black: 4,
            PokeballType.Master: 5,
        },
    )
    return game, p1, p2
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_rules.py
import pytest
from copy import deepcopy
from pokemon_splendor.models import PokeballType, GamePhase
from pokemon_splendor.engine.rules import (
    get_player_bonuses,
    calculate_effective_cost,
    apply_take_different_tokens,
    apply_take_same_tokens,
    apply_catch_pokemon,
    apply_reserve,
    apply_discard,
    apply_evolve,
    get_evolvable_cards,
    check_win_condition,
    refill_board_slot,
)
from tests.conftest import tokens, bonuses, make_token


# --- Bonus calculation ---

def test_bonuses_from_non_evolved_cards_only(charmander, squirtle):
    from pokemon_splendor.models import Player
    p = Player(name="P", cards=[charmander, squirtle])
    charmander.evolved = True
    bonuses_map = get_player_bonuses(p)
    # charmander's red bonus excluded; squirtle's blue bonus included
    assert bonuses_map.get(PokeballType.Red, 0) == 0
    assert bonuses_map.get(PokeballType.Blue, 0) == 1


def test_bonuses_summed_across_cards(charmander, squirtle):
    from pokemon_splendor.models import Player
    charmander.evolved = False
    squirtle.evolved = False
    p = Player(name="P", cards=[charmander, squirtle])
    bonuses_map = get_player_bonuses(p)
    assert bonuses_map[PokeballType.Red] == 1
    assert bonuses_map[PokeballType.Blue] == 1


# --- Effective cost ---

def test_effective_cost_reduced_by_bonus(charmander):
    from pokemon_splendor.models import Player
    p = Player(name="P", cards=[charmander])  # has 1 red bonus
    player_bonuses = get_player_bonuses(p)
    cost = calculate_effective_cost(charmander, player_bonuses)
    # charmander costs 2 red; 1 red bonus → effective cost 1 red
    assert cost.get(PokeballType.Red, 0) == 1


def test_effective_cost_never_negative(charmander):
    from pokemon_splendor.models import Player
    # Give player 5 red bonuses but charmander only costs 2 red
    extra = deepcopy(charmander)
    extra.evolved = False
    p = Player(name="P", cards=[charmander, extra, extra])
    player_bonuses = get_player_bonuses(p)
    cost = calculate_effective_cost(charmander, player_bonuses)
    assert cost.get(PokeballType.Red, 0) == 0


# --- Take different tokens ---

def test_take_1_different_token(two_player_game):
    game, p1, _ = two_player_game
    game2 = apply_take_different_tokens(game, p1, [PokeballType.Red])
    assert sum(1 for t in game2.turn.tokens if t.name == PokeballType.Red) == 1
    assert game2.tokens[PokeballType.Red] == 3


def test_take_3_different_tokens(two_player_game):
    game, p1, _ = two_player_game
    game2 = apply_take_different_tokens(game, p1, [PokeballType.Red, PokeballType.Blue, PokeballType.Yellow])
    assert len(p1.tokens) == 3
    assert game2.tokens[PokeballType.Red] == 3


def test_cannot_take_master_as_different_token(two_player_game):
    game, p1, _ = two_player_game
    with pytest.raises(ValueError, match="Master"):
        apply_take_different_tokens(game, p1, [PokeballType.Master])


def test_cannot_take_duplicate_types(two_player_game):
    game, p1, _ = two_player_game
    with pytest.raises(ValueError, match="duplicate"):
        apply_take_different_tokens(game, p1, [PokeballType.Red, PokeballType.Red])


def test_cannot_take_more_than_3(two_player_game):
    game, p1, _ = two_player_game
    with pytest.raises(ValueError):
        apply_take_different_tokens(
            game, p1,
            [PokeballType.Red, PokeballType.Blue, PokeballType.Yellow, PokeballType.Pink]
        )


def test_take_fewer_when_limited_types_available(two_player_game):
    game, p1, _ = two_player_game
    # Zero out all but Red and Blue on board
    for ptype in [PokeballType.Yellow, PokeballType.Pink, PokeballType.Black]:
        game.tokens[ptype] = 0
    # Taking 2 is valid when only 2 types available
    game2 = apply_take_different_tokens(game, p1, [PokeballType.Red, PokeballType.Blue])
    assert len(p1.tokens) == 2


def test_cannot_take_token_type_with_zero_on_board(two_player_game):
    game, p1, _ = two_player_game
    game.tokens[PokeballType.Yellow] = 0
    with pytest.raises(ValueError, match="not available"):
        apply_take_different_tokens(game, p1, [PokeballType.Red, PokeballType.Blue, PokeballType.Yellow])


# --- Take 2 same tokens ---

def test_take_2_same_valid(two_player_game):
    game, p1, _ = two_player_game
    game.tokens[PokeballType.Red] = 4
    game2 = apply_take_same_tokens(game, p1, PokeballType.Red)
    assert sum(1 for t in p1.tokens if t.name == PokeballType.Red) == 2
    assert game2.tokens[PokeballType.Red] == 2


def test_take_2_same_requires_4_on_board(two_player_game):
    game, p1, _ = two_player_game
    game.tokens[PokeballType.Red] = 3
    with pytest.raises(ValueError, match="4"):
        apply_take_same_tokens(game, p1, PokeballType.Red)


def test_cannot_take_2_master(two_player_game):
    game, p1, _ = two_player_game
    with pytest.raises(ValueError, match="Master"):
        apply_take_same_tokens(game, p1, PokeballType.Master)


# --- Catch pokemon ---

def test_catch_pays_correct_tokens(two_player_game, charmander):
    game, p1, _ = two_player_game
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    game2 = apply_catch_pokemon(game, p1, charmander, from_reserved=False, board_slot=0)
    assert charmander in p1.cards
    assert sum(1 for t in p1.tokens if t.name == PokeballType.Red) == 0
    assert game2.tokens[PokeballType.Red] == 6  # 4 + 2 returned


def test_catch_uses_bonus_as_discount(two_player_game, charmander, squirtle):
    game, p1, _ = two_player_game
    # p1 already owns squirtle (blue bonus), catching charmander (costs 2 red)
    # Squirtle bonus doesn't help with red cost — full price still
    p1.cards = [squirtle]
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    game2 = apply_catch_pokemon(game, p1, charmander, from_reserved=False, board_slot=0)
    assert charmander in p1.cards


def test_catch_bonus_reduces_cost(two_player_game, charmeleon):
    game, p1, _ = two_player_game
    # charmeleon costs 3 red; give p1 1 red bonus card + 2 red tokens
    from pokemon_splendor.models import Pokemon
    red_bonus_card = Pokemon(
        name="dummy", tier=Tier.Common,
        cost=[], bonus=bonuses(PokeballType.Red),
        evolve=[], evolve_into="", point=0,
    )
    p1.cards = [red_bonus_card]
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    game.board.uncommon_revealed[0] = charmeleon
    game2 = apply_catch_pokemon(game, p1, charmeleon, from_reserved=False, board_slot=4)
    assert charmeleon in p1.cards


def test_catch_master_as_wild(two_player_game, charmander):
    game, p1, _ = two_player_game
    # charmander costs 2 red; pay 1 red + 1 master
    p1.tokens = tokens(PokeballType.Red, PokeballType.Master)
    game2 = apply_catch_pokemon(game, p1, charmander, from_reserved=False, board_slot=0)
    assert charmander in p1.cards
    assert len(p1.tokens) == 0


def test_catch_epic_requires_master(two_player_game, mewtwo):
    game, p1, _ = two_player_game
    game.board.epic_revealed[0] = mewtwo
    # mewtwo costs master + 3 red; pay without master → fail
    p1.tokens = tokens(
        PokeballType.Red, PokeballType.Red, PokeballType.Red,
        PokeballType.Red,  # extra red instead of master
    )
    with pytest.raises(ValueError, match="Master"):
        apply_catch_pokemon(game, p1, mewtwo, from_reserved=False, board_slot=12)


def test_catch_epic_with_master_succeeds(two_player_game, mewtwo):
    game, p1, _ = two_player_game
    game.board.epic_revealed[0] = mewtwo
    p1.tokens = tokens(
        PokeballType.Master,
        PokeballType.Red, PokeballType.Red, PokeballType.Red,
    )
    game2 = apply_catch_pokemon(game, p1, mewtwo, from_reserved=False, board_slot=12)
    assert mewtwo in p1.cards


def test_catch_from_reserved_removes_card(two_player_game, charmander):
    game, p1, _ = two_player_game
    p1.reserved_cards = [charmander]
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    game2 = apply_catch_pokemon(game, p1, charmander, from_reserved=True, board_slot=None)
    assert charmander not in p1.reserved_cards
    assert charmander in p1.cards


def test_catch_updates_points(two_player_game, charmeleon):
    game, p1, _ = two_player_game
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red, PokeballType.Red)
    game.board.uncommon_revealed[0] = charmeleon
    apply_catch_pokemon(game, p1, charmeleon, from_reserved=False, board_slot=4)
    assert p1.points == 1


# --- Reserve ---

def test_reserve_adds_to_reserved(two_player_game, charmander):
    game, p1, _ = two_player_game
    apply_reserve(game, p1, charmander, board_slot=0, take_master=False)
    assert charmander in p1.reserved_cards


def test_reserve_with_master_gives_token(two_player_game, charmander):
    game, p1, _ = two_player_game
    apply_reserve(game, p1, charmander, board_slot=0, take_master=True)
    assert any(t.name == PokeballType.Master for t in p1.tokens)
    assert game.tokens[PokeballType.Master] == 4


def test_reserve_without_master_no_token(two_player_game, charmander):
    game, p1, _ = two_player_game
    apply_reserve(game, p1, charmander, board_slot=0, take_master=False)
    assert not any(t.name == PokeballType.Master for t in p1.tokens)


def test_reserve_max_3(two_player_game, charmander, squirtle):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    dummy = Pokemon(name="d", tier=Tier.Common, cost=[], bonus=[], evolve=[], evolve_into="", point=0)
    p1.reserved_cards = [charmander, squirtle, dummy]
    with pytest.raises(ValueError, match="3"):
        apply_reserve(game, p1, charmander, board_slot=0, take_master=False)


def test_cannot_reserve_epic(two_player_game, mewtwo):
    game, p1, _ = two_player_game
    game.board.epic_revealed[0] = mewtwo
    with pytest.raises(ValueError, match="Epic"):
        apply_reserve(game, p1, mewtwo, board_slot=12, take_master=True)


def test_cannot_reserve_when_no_master_and_take_master(two_player_game, charmander):
    game, p1, _ = two_player_game
    game.tokens[PokeballType.Master] = 0
    with pytest.raises(ValueError, match="Master"):
        apply_reserve(game, p1, charmander, board_slot=0, take_master=True)


# --- Discard ---

def test_discard_removes_one_token(two_player_game):
    game, p1, _ = two_player_game
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red, PokeballType.Blue)
    apply_discard(game, p1, PokeballType.Red)
    assert sum(1 for t in p1.tokens if t.name == PokeballType.Red) == 1
    assert game.tokens[PokeballType.Red] == 5


def test_discard_returns_token_to_board(two_player_game):
    game, p1, _ = two_player_game
    p1.tokens = tokens(PokeballType.Blue)
    apply_discard(game, p1, PokeballType.Blue)
    assert game.tokens[PokeballType.Blue] == 5


def test_cannot_discard_token_not_held(two_player_game):
    game, p1, _ = two_player_game
    p1.tokens = tokens(PokeballType.Red)
    with pytest.raises(ValueError, match="not held"):
        apply_discard(game, p1, PokeballType.Blue)


# --- Board refill ---

def test_board_refill_after_catch(two_player_game, charmander):
    from pokemon_splendor.models import Pokemon
    extra = Pokemon(name="extra", tier=Tier.Common, cost=[], bonus=[], evolve=[], evolve_into="", point=0)
    game, p1, _ = two_player_game
    game.board.common_deck = [extra]
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    apply_catch_pokemon(game, p1, charmander, from_reserved=False, board_slot=0)
    assert game.board.common_revealed[0] == extra


def test_board_slot_empty_when_deck_exhausted(two_player_game, charmander):
    game, p1, _ = two_player_game
    game.board.common_deck = []
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    apply_catch_pokemon(game, p1, charmander, from_reserved=False, board_slot=0)
    assert game.board.common_revealed[0] is None


# --- Evolution ---

def test_get_evolvable_cards(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    # p1 owns charmander (evolve requires 2 red bonuses)
    # give p1 a card with 2 red bonuses
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    game.board.uncommon_revealed[0] = charmeleon
    evolvable = get_evolvable_cards(game, p1)
    assert any(card.name == "charmander" for card, _ in evolvable)


def test_evolvable_uses_only_non_evolved_bonuses(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    # red_card is evolved — its bonus should NOT count
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    red_card.evolved = True
    p1.cards = [charmander, red_card]
    game.board.uncommon_revealed[0] = charmeleon
    evolvable = get_evolvable_cards(game, p1)
    assert evolvable == []


def test_evolve_marks_source_as_evolved(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    game.board.uncommon_revealed[0] = charmeleon
    apply_evolve(game, p1, card_index=0)  # evolve charmander (index 0 in p1.cards)
    assert charmander.evolved is True


def test_evolve_adds_evolved_form_to_collection(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    game.board.uncommon_revealed[0] = charmeleon
    apply_evolve(game, p1, card_index=0)
    assert charmeleon in p1.cards


def test_evolve_is_free(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    p1.tokens = []
    game.board.uncommon_revealed[0] = charmeleon
    apply_evolve(game, p1, card_index=0)
    assert len(p1.tokens) == 0  # no tokens spent


def test_evolve_excludes_source_from_points(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    game.board.uncommon_revealed[0] = charmeleon
    apply_evolve(game, p1, card_index=0)
    assert p1.points == charmeleon.point  # only charmeleon's points count


def test_evolve_from_reserved(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    p1.reserved_cards = [charmeleon]
    game.board.uncommon_revealed[0] = None
    apply_evolve(game, p1, card_index=0)
    assert charmeleon in p1.cards
    assert charmeleon not in p1.reserved_cards


def test_evolve_fails_when_target_not_available(two_player_game, charmander):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    # charmeleon not on board or reserved
    with pytest.raises(ValueError, match="not available"):
        apply_evolve(game, p1, card_index=0)


# --- Win condition ---

def test_win_not_triggered_below_18(two_player_game):
    game, p1, _ = two_player_game
    p1.points = 17
    assert check_win_condition(game) is None


def test_win_triggered_at_18(two_player_game):
    game, p1, _ = two_player_game
    p1.points = 18
    assert check_win_condition(game) is not None


def test_win_tiebreak_by_card_count(two_player_game):
    game, p1, p2 = two_player_game
    from pokemon_splendor.models import Pokemon
    dummy = Pokemon(name="d", tier=Tier.Common, cost=[], bonus=[], evolve=[], evolve_into="", point=0)
    p1.points = 18
    p2.points = 18
    p1.cards = [dummy]
    p2.cards = [dummy, dummy]
    winner = check_win_condition(game)
    assert winner == p2  # more cards wins
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
uv run pytest tests/test_rules.py -v 2>&1 | head -20
```

Expected: all FAIL with `ImportError`.

- [ ] **Step 4: Implement `rules.py`**

```python
# src/pokemon_splendor/engine/rules.py
from collections import Counter
from copy import deepcopy
from pokemon_splendor.models import (
    Game, Player, Pokemon, Board, PokeballType, Tier, PokeballToken, Bonus,
)


def get_player_bonuses(player: Player) -> Counter:
    bonuses: Counter = Counter()
    for card in player.cards:
        if not card.evolved:
            for b in card.bonus:
                bonuses[b.name] += 1
    return bonuses


def calculate_effective_cost(pokemon: Pokemon, player_bonuses: Counter) -> Counter:
    cost: Counter = Counter()
    for token in pokemon.cost:
        cost[token.name] += 1
    for ptype, count in player_bonuses.items():
        if ptype in cost:
            cost[ptype] = max(0, cost[ptype] - count)
    return cost


def _player_token_counter(player: Player) -> Counter:
    c: Counter = Counter()
    for t in player.tokens:
        c[t.name] += 1
    return c


def _recalculate_points(player: Player) -> None:
    player.points = sum(c.point for c in player.cards if not c.evolved)


def apply_take_different_tokens(game: Game, player: Player, token_types: list[PokeballType]) -> Game:
    if len(token_types) > 3:
        raise ValueError("Cannot take more than 3 tokens")
    if len(set(token_types)) != len(token_types):
        raise ValueError("Cannot take duplicate types")
    if PokeballType.Master in token_types:
        raise ValueError("Master token cannot be taken as a different token")
    for ptype in token_types:
        if game.tokens.get(ptype, 0) == 0:
            raise ValueError(f"{ptype} not available on board")
    for ptype in token_types:
        game.tokens[ptype] -= 1
        player.tokens.append(PokeballToken(ptype))
    return game


def apply_take_same_tokens(game: Game, player: Player, token_type: PokeballType) -> Game:
    if token_type == PokeballType.Master:
        raise ValueError("Master token cannot be taken as same-type pair")
    if game.tokens.get(token_type, 0) < 4:
        raise ValueError(f"Need at least 4 {token_type} on board to take 2")
    game.tokens[token_type] -= 2
    player.tokens.extend([PokeballToken(token_type), PokeballToken(token_type)])
    return game


def _get_board_slot_list(board: Board, tier: Tier) -> list:
    return {
        Tier.Common: board.common_revealed,
        Tier.Uncommon: board.uncommon_revealed,
        Tier.Rare: board.rare_revealed,
        Tier.Epic: board.epic_revealed,
        Tier.Legendary: board.legendary_revealed,
    }[tier]


def _get_deck(board: Board, tier: Tier) -> list:
    return {
        Tier.Common: board.common_deck,
        Tier.Uncommon: board.uncommon_deck,
        Tier.Rare: board.rare_deck,
        Tier.Epic: board.epic_deck,
        Tier.Legendary: board.legendary_deck,
    }[tier]


def refill_board_slot(board: Board, tier: Tier, slot_index: int) -> None:
    deck = _get_deck(board, tier)
    slot_list = _get_board_slot_list(board, tier)
    slot_list[slot_index] = deck.pop(0) if deck else None


def apply_catch_pokemon(
    game: Game,
    player: Player,
    pokemon: Pokemon,
    from_reserved: bool,
    board_slot: int | None,
) -> Game:
    player_bonuses = get_player_bonuses(player)
    effective_cost = calculate_effective_cost(pokemon, player_bonuses)
    player_tokens = _player_token_counter(player)

    # Validate Master token requirement for Epic/Legendary
    master_required = effective_cost.get(PokeballType.Master, 0)
    if pokemon.tier in (Tier.Epic, Tier.Legendary) and master_required == 0:
        master_required = 1  # always need at least 1 master
        effective_cost[PokeballType.Master] = master_required

    master_available = player_tokens.get(PokeballType.Master, 0)
    if master_available < master_required:
        raise ValueError(f"Master token required to catch {pokemon.tier.value} Pokémon")

    # Calculate shortfall covered by Master wilds
    shortfall = 0
    for ptype, needed in effective_cost.items():
        if ptype == PokeballType.Master:
            continue
        shortfall += max(0, needed - player_tokens.get(ptype, 0))

    masters_used_as_wild = shortfall
    masters_used_required = master_required
    if master_available < masters_used_required + masters_used_as_wild:
        raise ValueError("Not enough tokens to catch this Pokémon")

    # Deduct tokens from player and return to board
    paid: Counter = Counter()
    for ptype, needed in effective_cost.items():
        if ptype == PokeballType.Master:
            paid[PokeballType.Master] += needed
        else:
            available = player_tokens.get(ptype, 0)
            direct = min(available, needed)
            paid[ptype] += direct
            wild = needed - direct
            paid[PokeballType.Master] += wild

    new_tokens = []
    paid_remaining = Counter(paid)
    for t in player.tokens:
        if paid_remaining.get(t.name, 0) > 0:
            paid_remaining[t.name] -= 1
            game.tokens[t.name] = game.tokens.get(t.name, 0) + 1
        else:
            new_tokens.append(t)
    player.tokens = new_tokens

    # Remove from board or reserved
    if from_reserved:
        player.reserved_cards.remove(pokemon)
    else:
        tier_list = _get_board_slot_list(game.board, pokemon.tier)
        local_slot = board_slot - {
            Tier.Common: 0, Tier.Uncommon: 4, Tier.Rare: 8, Tier.Epic: 12, Tier.Legendary: 13,
        }[pokemon.tier]
        tier_list[local_slot] = None
        refill_board_slot(game.board, pokemon.tier, local_slot)

    player.cards.append(pokemon)
    _recalculate_points(player)
    return game


def apply_reserve(
    game: Game,
    player: Player,
    pokemon: Pokemon,
    board_slot: int,
    take_master: bool,
) -> Game:
    if pokemon.tier in (Tier.Epic, Tier.Legendary):
        raise ValueError(f"{pokemon.tier.value.capitalize()} Pokémon cannot be reserved")
    if len(player.reserved_cards) >= 3:
        raise ValueError("Cannot reserve more than 3 Pokémon")
    if take_master and game.tokens.get(PokeballType.Master, 0) == 0:
        raise ValueError("No Master tokens available to take")

    tier_list = _get_board_slot_list(game.board, pokemon.tier)
    local_slot = board_slot - {
        Tier.Common: 0, Tier.Uncommon: 4, Tier.Rare: 8,
    }[pokemon.tier]
    tier_list[local_slot] = None
    refill_board_slot(game.board, pokemon.tier, local_slot)

    player.reserved_cards.append(pokemon)
    if take_master:
        game.tokens[PokeballType.Master] -= 1
        player.tokens.append(PokeballToken(PokeballType.Master))
    return game


def apply_discard(game: Game, player: Player, token_type: PokeballType) -> Game:
    for i, t in enumerate(player.tokens):
        if t.name == token_type:
            player.tokens.pop(i)
            game.tokens[token_type] = game.tokens.get(token_type, 0) + 1
            return game
    raise ValueError(f"{token_type} not held by player")


def get_evolvable_cards(game: Game, player: Player) -> list[tuple[Pokemon, Pokemon]]:
    player_bonuses = get_player_bonuses(player)
    result = []
    for card in player.cards:
        if card.evolved or not card.evolve_into:
            continue
        needed: Counter = Counter()
        for b in card.evolve:
            needed[b.name] += 1
        if any(player_bonuses.get(ptype, 0) < count for ptype, count in needed.items()):
            continue
        # Find evolved form on board or in reserved
        target = _find_pokemon(game, player, card.evolve_into)
        if target:
            result.append((card, target))
    return result


def _find_pokemon(game: Game, player: Player, name: str) -> Pokemon | None:
    all_revealed = (
        game.board.common_revealed
        + game.board.uncommon_revealed
        + game.board.rare_revealed
        + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    for p in all_revealed:
        if p and p.name == name:
            return p
    for p in player.reserved_cards:
        if p.name == name:
            return p
    return None


def apply_evolve(game: Game, player: Player, card_index: int) -> Game:
    card = player.cards[card_index]
    evolvable = get_evolvable_cards(game, player)
    match = next(((c, t) for c, t in evolvable if c is card), None)
    if not match:
        raise ValueError(f"{card.name} cannot be evolved or target not available")
    source, target = match

    # Remove target from board or reserved
    all_tier_lists = [
        game.board.common_revealed,
        game.board.uncommon_revealed,
        game.board.rare_revealed,
        game.board.epic_revealed,
        game.board.legendary_revealed,
    ]
    removed = False
    for tier, tier_list in zip(
        [Tier.Common, Tier.Uncommon, Tier.Rare, Tier.Epic, Tier.Legendary], all_tier_lists
    ):
        for i, p in enumerate(tier_list):
            if p is target:
                tier_list[i] = None
                refill_board_slot(game.board, tier, i)
                removed = True
                break
        if removed:
            break
    if not removed:
        if target in player.reserved_cards:
            player.reserved_cards.remove(target)
        else:
            raise ValueError(f"{target.name} not available on board or reserved")

    source.evolved = True
    player.cards.append(target)
    _recalculate_points(player)
    return game


def check_win_condition(game: Game) -> Player | None:
    triggered = [p for p in game.players if p.points >= 18]
    if not triggered:
        return None
    # Return player with highest points; tiebreak: most cards
    return max(game.players, key=lambda p: (p.points, len(p.cards)))
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_rules.py -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pokemon_splendor/engine/rules.py tests/conftest.py tests/test_rules.py
git commit -m "feat: add game rules with full test coverage"
```

---

## Task 6: PettingZoo Environment

**Files:**
- Create: `src/pokemon_splendor/engine/env.py`
- Create: `tests/test_game.py`

- [ ] **Step 1: Write failing integration tests**

```python
# tests/test_game.py
import numpy as np
import pytest
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.engine.actions import TOTAL_ACTIONS
from pathlib import Path

JSONL = Path("data/pokemon.jsonl")


@pytest.fixture
def env():
    e = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    e.reset()
    return e


def test_env_resets_without_error():
    env = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    env.reset()


def test_action_space_size(env):
    for agent in env.agents:
        assert env.action_space(agent).n == TOTAL_ACTIONS


def test_observation_is_numpy_array(env):
    agent = env.agent_selection
    obs, _, _, _, _ = env.last()
    assert isinstance(obs, np.ndarray)


def test_action_mask_is_boolean_array(env):
    agent = env.agent_selection
    mask = env.action_mask(agent)
    assert mask.dtype == bool
    assert len(mask) == TOTAL_ACTIONS


def test_action_mask_has_at_least_one_valid_action(env):
    agent = env.agent_selection
    mask = env.action_mask(agent)
    assert mask.any()


def test_random_game_terminates():
    import random
    env = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    env.reset()
    for _ in range(10000):
        if not env.agents:
            break
        agent = env.agent_selection
        mask = env.action_mask(agent)
        valid = np.where(mask)[0]
        action = random.choice(valid)
        env.step(action)
    assert not env.agents, "Game did not terminate within 10000 steps"


def test_winner_declared_at_end():
    import random
    env = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    env.reset()
    for _ in range(10000):
        if not env.agents:
            break
        agent = env.agent_selection
        mask = env.action_mask(agent)
        valid = np.where(mask)[0]
        env.step(random.choice(valid))
    rewards = env.rewards
    assert any(r == 1.0 for r in rewards.values())
    assert any(r == -1.0 for r in rewards.values())
```

- [ ] **Step 2: Implement `env.py`**

```python
# src/pokemon_splendor/engine/env.py
import random
from pathlib import Path
from collections import Counter
import numpy as np
import gymnasium
from pettingzoo import AECEnv
from pettingzoo.utils import agent_selector

from pokemon_splendor.models import (
    Game, Player, Board, Pokemon, PokeballType, Tier, GamePhase,
)
from pokemon_splendor.data.loader import load_pokemon
from pokemon_splendor.engine.actions import (
    TOTAL_ACTIONS, TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START,
    CATCH_RESERVED_START, RESERVE_MASTER_START, RESERVE_NO_MASTER_START,
    DISCARD_START, EVOLVE_START, EVOLVE_PASS,
    BOARD_SLOT_TIERS, RESERVABLE_TIERS, DISCARD_ACTION, TAKE_SAME_ACTION,
    MAX_OWNED_CARDS,
)
from pokemon_splendor.engine.rules import (
    apply_take_different_tokens, apply_take_same_tokens,
    apply_catch_pokemon, apply_reserve, apply_discard, apply_evolve,
    get_evolvable_cards, check_win_condition, refill_board_slot,
)

INITIAL_TOKENS = {2: 4, 3: 5, 4: 7}
TIER_SLOTS = {
    Tier.Common: (0, 4),
    Tier.Uncommon: (4, 8),
    Tier.Rare: (8, 12),
    Tier.Epic: (12, 13),
    Tier.Legendary: (13, 14),
}


class PokemonSplendorEnv(AECEnv):
    metadata = {"name": "pokemon_splendor_v0"}

    def __init__(self, jsonl_path: Path, num_players: int = 2, render_mode: str | None = None):
        assert 2 <= num_players <= 4
        self.jsonl_path = jsonl_path
        self.num_players = num_players
        self.render_mode = render_mode
        self._all_pokemon = load_pokemon(jsonl_path)

        self.possible_agents = [f"player_{i}" for i in range(num_players)]
        self.agents = list(self.possible_agents)

        obs_size = self._obs_size()
        self.observation_spaces = {
            a: gymnasium.spaces.Box(0, 1, shape=(obs_size,), dtype=np.float32)
            for a in self.possible_agents
        }
        self.action_spaces = {
            a: gymnasium.spaces.Discrete(TOTAL_ACTIONS)
            for a in self.possible_agents
        }
        self.game: Game | None = None

    def _obs_size(self) -> int:
        return 6 + 14 * 20 + self.num_players * 14 + self.num_players + 3

    def reset(self, seed=None, options=None):
        if seed is not None:
            random.seed(seed)

        by_tier: dict[Tier, list[Pokemon]] = {t: [] for t in Tier}
        import copy
        for p in self._all_pokemon:
            by_tier[p.tier].append(copy.deepcopy(p))
        for lst in by_tier.values():
            random.shuffle(lst)

        def fill(lst, n):
            revealed = lst[:n] + [None] * max(0, n - len(lst))
            deck = lst[n:]
            return revealed[:n], deck

        cr, cd = fill(by_tier[Tier.Common], 4)
        ur, ud = fill(by_tier[Tier.Uncommon], 4)
        rr, rd = fill(by_tier[Tier.Rare], 4)
        er, ed = fill(by_tier[Tier.Epic], 1)
        lr, ld = fill(by_tier[Tier.Legendary], 1)

        board = Board(
            common_revealed=cr, common_deck=cd,
            uncommon_revealed=ur, uncommon_deck=ud,
            rare_revealed=rr, rare_deck=rd,
            epic_revealed=er, epic_deck=ed,
            legendary_revealed=lr, legendary_deck=ld,
        )

        normal_count = INITIAL_TOKENS[self.num_players]
        tokens = {
            PokeballType.Red: normal_count,
            PokeballType.Yellow: normal_count,
            PokeballType.Blue: normal_count,
            PokeballType.Pink: normal_count,
            PokeballType.Black: normal_count,
            PokeballType.Master: 5,
        }

        players = [Player(name=a) for a in self.possible_agents]
        start = random.choice(players)

        self.game = Game(
            players=players,
            turn=start,
            starting_player=start,
            round=1,
            board=board,
            tokens=tokens,
        )

        self.agents = list(self.possible_agents)
        self._agent_selector = agent_selector(self.agents)
        self.agent_selection = self._agent_selector.reset()
        # Sync selector to starting player
        while self.agent_selection != start.name:
            self.agent_selection = self._agent_selector.next()

        self.rewards = {a: 0.0 for a in self.agents}
        self.terminations = {a: False for a in self.agents}
        self.truncations = {a: False for a in self.agents}
        self.infos = {a: {} for a in self.agents}
        self._cumulative_rewards = {a: 0.0 for a in self.agents}

    def observe(self, agent: str) -> np.ndarray:
        obs = np.zeros(self._obs_size(), dtype=np.float32)
        offset = 0
        # Board tokens
        for i, ptype in enumerate(PokeballType):
            obs[offset + i] = self.game.tokens.get(ptype, 0) / 10.0
        offset += 6
        # Revealed cards
        all_slots = (
            self.game.board.common_revealed
            + self.game.board.uncommon_revealed
            + self.game.board.rare_revealed
            + self.game.board.epic_revealed
            + self.game.board.legendary_revealed
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
        # Players
        player_map = {p.name: p for p in self.game.players}
        for a in self.possible_agents:
            p = player_map[a]
            tc = Counter(t.name for t in p.tokens)
            for i, pt in enumerate(PokeballType):
                obs[offset + i] = tc.get(pt, 0) / 10.0
            offset += 6
            tier_counts = Counter(c.tier for c in p.cards if not c.evolved)
            for t in Tier:
                obs[offset] = tier_counts.get(t, 0) / 5.0
                offset += 1
            obs[offset] = p.points / 18.0
            obs[offset+1] = len(p.reserved_cards) / 3.0
            offset += 2
        # Current player
        for i, a in enumerate(self.possible_agents):
            obs[offset + i] = 1.0 if a == self.game.turn.name else 0.0
        offset += self.num_players
        # Phase
        for i, ph in enumerate(GamePhase):
            obs[offset + i] = 1.0 if self.game.phase == ph else 0.0
        return obs

    def action_mask(self, agent: str) -> np.ndarray:
        mask = np.zeros(TOTAL_ACTIONS, dtype=bool)
        player = next(p for p in self.game.players if p.name == agent)
        game = self.game

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

        # Main phase
        available_types = {pt for pt in NORMAL_TYPES if game.tokens.get(pt, 0) > 0}
        for i, combo in enumerate(TAKE_DIFF_COMBOS):
            if all(pt in available_types for pt in combo):
                can_take = len(combo) <= len(available_types)
                if can_take:
                    mask[TAKE_DIFF_START + i] = True

        for pt in NORMAL_TYPES:
            if game.tokens.get(pt, 0) >= 4:
                mask[TAKE_SAME_ACTION[pt]] = True

        all_slots = (
            game.board.common_revealed
            + game.board.uncommon_revealed
            + game.board.rare_revealed
            + game.board.epic_revealed
            + game.board.legendary_revealed
        )
        player_bonuses = None
        from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost
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
            reservable_slots = [
                i for i, p in enumerate(all_slots[:12]) if p is not None
            ]
            for slot_idx in reservable_slots:
                if game.tokens.get(PokeballType.Master, 0) > 0:
                    mask[RESERVE_MASTER_START + slot_idx] = True
                mask[RESERVE_NO_MASTER_START + slot_idx] = True

        return mask

    def _enter_evolve_phase(self, agent: str, player: Player) -> None:
        self.game.phase = GamePhase.EVOLVE
        if not self.action_mask(agent)[EVOLVE_START:EVOLVE_PASS].any():
            self._end_turn(player)

    def step(self, action: int):
        agent = self.agent_selection
        player = next(p for p in self.game.players if p.name == agent)

        self._apply_action(player, action)

        if self.game.phase == GamePhase.EVOLVE:
            # Evolve action (or pass) just taken — end turn
            self._end_turn(player)
            return

        if self.game.phase == GamePhase.DISCARD:
            if len(player.tokens) <= 10:
                self._enter_evolve_phase(agent, player)
            # else stay in DISCARD for next discard action
            return

        # Main phase action just taken
        if len(player.tokens) > 10:
            self.game.phase = GamePhase.DISCARD
        else:
            self._enter_evolve_phase(agent, player)

    def _apply_action(self, player: Player, action: int):
        game = self.game

        if game.phase == GamePhase.DISCARD:
            for ptype, idx in DISCARD_ACTION.items():
                if action == idx:
                    apply_discard(game, player, ptype)
                    return  # phase transition handled by step()
            raise ValueError(f"Invalid discard action {action}")

        if game.phase == GamePhase.EVOLVE:
            if action == EVOLVE_PASS:
                return
            card_idx = action - EVOLVE_START
            apply_evolve(game, player, card_idx)
            game.evolved_this_turn = True
            return

        # Main phase
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
            apply_catch_pokemon(game, player, pokemon, from_reserved=False, board_slot=action - CATCH_BOARD_START)
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

    def _end_turn(self, player: Player):
        self.game.phase = GamePhase.MAIN
        self.game.evolved_this_turn = False

        winner = check_win_condition(self.game)
        if winner:
            if not self.game.win_triggered:
                self.game.win_triggered = True

            # Check if round is complete (back to starting player)
            if player == self.game.players[-1] or (
                self.game.win_triggered
                and self.game.turn == self.game.players[-1]
            ):
                for p in self.game.players:
                    agent = p.name
                    self.rewards[agent] = 1.0 if p is winner else -1.0
                    self.terminations[agent] = True
                self.agents = []
                return

        # Advance turn
        idx = self.game.players.index(player)
        next_player = self.game.players[(idx + 1) % len(self.game.players)]
        self.game.turn = next_player
        self.agent_selection = self._agent_selector.next()

    def last(self, observe=True):
        agent = self.agent_selection
        obs = self.observe(agent) if observe else None
        return (
            obs,
            self.rewards.get(agent, 0),
            self.terminations.get(agent, False),
            self.truncations.get(agent, False),
            self.infos.get(agent, {}),
        )

    def render(self):
        if self.render_mode == "human":
            from pokemon_splendor.cli.renderer import render
            render(self.game)
```

- [ ] **Step 3: Run integration tests**

```bash
uv run pytest tests/test_game.py -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add src/pokemon_splendor/engine/env.py tests/test_game.py
git commit -m "feat: add PettingZoo AEC environment"
```

---

## Task 7: CLI Renderer

**Files:**
- Create: `src/pokemon_splendor/cli/renderer.py`

- [ ] **Step 1: Implement renderer**

```python
# src/pokemon_splendor/cli/renderer.py
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from pokemon_splendor.models import Game, PokeballType, GamePhase

console = Console()

TYPE_COLORS = {
    PokeballType.Red: "red",
    PokeballType.Yellow: "yellow",
    PokeballType.Blue: "blue",
    PokeballType.Pink: "magenta",
    PokeballType.Black: "white",
    PokeballType.Master: "gold1",
}


def _token_str(tokens: dict[PokeballType, int]) -> str:
    return "  ".join(
        f"[{TYPE_COLORS[pt]}]{pt.value}:{count}[/]"
        for pt, count in tokens.items()
        if count > 0
    )


def render(game: Game) -> None:
    console.rule(f"[bold]Round {game.round} — {game.turn.name}'s turn ({game.phase.value})[/]")

    # Board tokens
    from collections import Counter
    console.print(Panel(_token_str(game.tokens), title="Board Tokens"))

    # Revealed cards per tier
    all_revealed = {
        "Common": game.board.common_revealed,
        "Uncommon": game.board.uncommon_revealed,
        "Rare": game.board.rare_revealed,
        "Epic": game.board.epic_revealed,
        "Legendary": game.board.legendary_revealed,
    }
    for tier_name, slots in all_revealed.items():
        table = Table(title=tier_name, box=box.SIMPLE)
        table.add_column("Slot")
        table.add_column("Name")
        table.add_column("Cost")
        table.add_column("Bonus")
        table.add_column("Pts")
        for i, p in enumerate(slots):
            if p:
                cost_str = " ".join(f"{t.name.value}" for t in p.cost)
                bonus_str = " ".join(f"{b.name.value}" for b in p.bonus)
                table.add_row(str(i), p.name, cost_str, bonus_str, str(p.point))
            else:
                table.add_row(str(i), "—", "", "", "")
        console.print(table)

    # Players
    for p in game.players:
        tc = Counter(t.name for t in p.tokens)
        token_str = "  ".join(f"{pt.value}:{tc[pt]}" for pt in PokeballType if tc[pt] > 0)
        cards_str = ", ".join(
            f"{c.name}{'*' if c.evolved else ''}" for c in p.cards
        )
        reserved_str = ", ".join(c.name for c in p.reserved_cards)
        marker = "► " if p is game.turn else "  "
        console.print(
            Panel(
                f"Tokens: {token_str}\nCards: {cards_str}\nReserved: {reserved_str}\nPoints: {p.points}",
                title=f"{marker}{p.name}",
            )
        )


def render_valid_actions(actions: list[tuple[int, str]]) -> None:
    for idx, (action_id, description) in enumerate(actions):
        console.print(f"  [{idx}] {description}")
```

- [ ] **Step 2: Smoke test**

```bash
uv run python -c "
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pathlib import Path
env = PokemonSplendorEnv(Path('data/pokemon.jsonl'), num_players=2, render_mode='human')
env.reset()
env.render()
print('Renderer OK')
"
```

Expected: board state printed to terminal, `Renderer OK`.

- [ ] **Step 3: Commit**

```bash
git add src/pokemon_splendor/cli/renderer.py
git commit -m "feat: add rich CLI renderer"
```

---

## Task 8: Entry Point

**Files:**
- Create: `src/pokemon_splendor/__main__.py`

- [ ] **Step 1: Implement entry point**

```python
# src/pokemon_splendor/__main__.py
import argparse
import random
import numpy as np
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv


def main():
    parser = argparse.ArgumentParser(prog="pokemon-splendor")
    parser.add_argument("--players", default="random,random",
                        help="Comma-separated agent types: random, human")
    parser.add_argument("--mode", choices=["play", "train", "benchmark"], default="play")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--data", default="data/pokemon.jsonl")
    args = parser.parse_args()

    agent_types = [a.strip() for a in args.players.split(",")]
    num_players = len(agent_types)
    render_mode = "human" if (args.render or args.mode == "play") else None
    jsonl = Path(args.data)

    if args.mode == "benchmark":
        _run_benchmark(jsonl, agent_types, args.games, render_mode)
    else:
        _run_game(jsonl, agent_types, render_mode)


def _make_agent(agent_type: str):
    if agent_type == "random":
        return lambda obs, mask: int(np.random.choice(np.where(mask)[0]))
    if agent_type == "human":
        from pokemon_splendor.agents.human import HumanAgent
        return HumanAgent()
    raise ValueError(f"Unknown agent type: {agent_type}")


def _run_game(jsonl: Path, agent_types: list[str], render_mode: str | None):
    agents_map = {}
    env = PokemonSplendorEnv(jsonl, num_players=len(agent_types), render_mode=render_mode)
    env.reset()
    agent_list = env.possible_agents
    for name, atype in zip(agent_list, agent_types):
        agents_map[name] = _make_agent(atype)

    for _ in range(100000):
        if not env.agents:
            break
        agent_name = env.agent_selection
        obs, reward, term, trunc, _ = env.last()
        if term or trunc:
            env.step(None)
            continue
        mask = env.action_mask(agent_name)
        action = agents_map[agent_name](obs, mask) if callable(agents_map[agent_name]) else agents_map[agent_name].act(obs, mask)
        if render_mode == "human":
            env.render()
        env.step(action)

    from rich.console import Console
    c = Console()
    winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
    c.print(f"\n[bold green]Winner: {winner.name} with {winner.points} points![/]")


def _run_benchmark(jsonl: Path, agent_types: list[str], num_games: int, render_mode):
    wins = {i: 0 for i in range(len(agent_types))}
    for _ in range(num_games):
        env = PokemonSplendorEnv(jsonl, num_players=len(agent_types), render_mode=render_mode)
        env.reset()
        agent_list = env.possible_agents
        agents_map = {name: _make_agent(t) for name, t in zip(agent_list, agent_types)}
        for _ in range(100000):
            if not env.agents:
                break
            name = env.agent_selection
            obs, _, term, trunc, _ = env.last()
            if term or trunc:
                env.step(None)
                continue
            mask = env.action_mask(name)
            action = agents_map[name](obs, mask) if callable(agents_map[name]) else agents_map[name].act(obs, mask)
            env.step(action)
        winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
        idx = env.possible_agents.index(winner.name)
        wins[idx] += 1

    print("\nBenchmark Results:")
    for i, atype in enumerate(agent_types):
        print(f"  {atype}: {wins[i]}/{num_games} wins ({100*wins[i]/num_games:.1f}%)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run smoke test**

```bash
uv run pokemon-splendor --players random,random --mode benchmark --games 5
```

Expected: benchmark output printed with win percentages.

- [ ] **Step 3: Run all tests**

```bash
uv run pytest -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add src/pokemon_splendor/__main__.py
git commit -m "feat: add CLI entry point with play/benchmark modes"
```
