# AlphaZero-Style Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an AlphaZero-style self-improving agent that uses a neural network (policy + value heads) inside MCTS, trained via self-play.

**Architecture:** A PyTorch network (`AlphaNet`) with shared layers and two heads (policy over 108 actions, scalar value) replaces the heuristic evaluator and uniform UCB in a new `AlphaMCTSAgent`. A `AlphaCoach` runs the self-play loop: generate games, collect `(obs, visit_counts, outcome)` records, train the network, checkpoint. Everything is additive — no existing files are modified except `__main__.py` (new mode + agent type appended).

**Tech Stack:** Python, PyTorch (`torch`, `torch.nn`, `torch.optim`), existing `compute_observation`/`compute_mask` from `engine/observation.py`, existing `_step_inplace` from `engine/simulator.py`, existing `_clone` pattern from `agents/mcts.py`.

---

## File Structure

| File | Role |
|------|------|
| `src/pokemon_splendor/agents/alpha_net.py` | `AlphaNet` PyTorch module — shared layers + policy head + value head |
| `src/pokemon_splendor/agents/alpha_mcts.py` | `AlphaMCTSNode` dataclass + `AlphaMCTSAgent` — MCTS using network for eval and UCB prior |
| `src/pokemon_splendor/agents/alpha_coach.py` | `compute_outcomes`, `SelfPlayRecord`, `run_self_play_game`, `train_step`, `AlphaCoach` |
| `src/pokemon_splendor/__main__.py` | Add `alpha-train` mode + `alpha:<path>` agent type (append only) |
| `tests/test_alpha.py` | All tests for the above |

---

### Task 1: AlphaNet — neural network with two heads

**Files:**
- Create: `src/pokemon_splendor/agents/alpha_net.py`
- Test: `tests/test_alpha.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_alpha.py
import torch
import numpy as np
import pytest
from pokemon_splendor.agents.alpha_net import AlphaNet

OBS_SIZE = 345
TOTAL_ACTIONS = 108


def test_alpha_net_policy_shape():
    net = AlphaNet()
    obs = torch.zeros(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert policy.shape == (TOTAL_ACTIONS,)


def test_alpha_net_value_shape():
    net = AlphaNet()
    obs = torch.zeros(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert value.shape == ()


def test_alpha_net_policy_sums_to_one():
    net = AlphaNet()
    obs = torch.randn(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, _ = net(obs, mask)
    assert abs(policy.sum().item() - 1.0) < 1e-5


def test_alpha_net_policy_respects_mask():
    net = AlphaNet()
    obs = torch.randn(OBS_SIZE)
    mask = torch.zeros(TOTAL_ACTIONS, dtype=torch.bool)
    mask[0] = True
    mask[1] = True
    policy, _ = net(obs, mask)
    assert policy[2:].sum().item() < 1e-6
    assert abs(policy[:2].sum().item() - 1.0) < 1e-5


def test_alpha_net_value_in_range():
    net = AlphaNet()
    obs = torch.randn(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    _, value = net(obs, mask)
    assert 0.0 <= value.item() <= 1.0


def test_alpha_net_batch_forward():
    net = AlphaNet()
    obs = torch.randn(4, OBS_SIZE)
    mask = torch.ones(4, TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert policy.shape == (4, TOTAL_ACTIONS)
    assert value.shape == (4,)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_alpha.py -v
```
Expected: `ModuleNotFoundError: No module named 'pokemon_splendor.agents.alpha_net'`

- [ ] **Step 3: Implement AlphaNet**

```python
# src/pokemon_splendor/agents/alpha_net.py
import torch
import torch.nn as nn
import torch.nn.functional as F

OBS_SIZE = 345
TOTAL_ACTIONS = 108


class AlphaNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(OBS_SIZE, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
        )
        self.policy_head = nn.Linear(256, TOTAL_ACTIONS)
        self.value_head = nn.Linear(256, 1)

    def forward(self, obs: torch.Tensor, mask: torch.Tensor):
        x = self.shared(obs)
        logits = self.policy_head(x)
        logits = logits.masked_fill(~mask, float("-inf"))
        policy = F.softmax(logits, dim=-1)
        value = torch.sigmoid(self.value_head(x)).squeeze(-1)
        return policy, value

    def save(self, path: str) -> None:
        torch.save(self.state_dict(), path)

    @classmethod
    def load(cls, path: str) -> "AlphaNet":
        net = cls()
        net.load_state_dict(torch.load(path, map_location="cpu"))
        net.eval()
        return net
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_alpha.py -v
```
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/pokemon_splendor/agents/alpha_net.py tests/test_alpha.py
git commit -m "feat: add AlphaNet with policy and value heads"
```

---

### Task 2: compute_outcomes — multi-player outcome calculation

**Files:**
- Create: `src/pokemon_splendor/agents/alpha_coach.py` (stub, grows in later tasks)
- Test: `tests/test_alpha.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_alpha.py`:

```python
from pokemon_splendor.agents.alpha_coach import compute_outcomes
from pokemon_splendor.models import Game, Player, Pokemon, Board, PokeballType, Tier, PokeballToken, GamePhase


def _make_player(name: str, points: int, n_cards: int) -> Player:
    cards = []
    for i in range(n_cards):
        p = Pokemon(
            name=f"card_{i}", tier=Tier.Common, cost=[], bonus=[], evolve=[],
            evolve_into=None, point=0,
        )
        cards.append(p)
    player = Player(name=name)
    player.points = points
    player.cards = cards
    return player


def test_compute_outcomes_winner_gets_one():
    p1 = _make_player("player_0", 20, 10)
    p2 = _make_player("player_1", 15, 8)
    game = _make_minimal_game([p1, p2], winner=p1)
    outcomes = compute_outcomes(game)
    assert outcomes["player_0"] == 1.0


def test_compute_outcomes_normalised_by_winner_score():
    p1 = _make_player("player_0", 20, 10)
    p2 = _make_player("player_1", 10, 10)
    game = _make_minimal_game([p1, p2], winner=p1)
    outcomes = compute_outcomes(game)
    assert abs(outcomes["player_1"] - 0.5) < 1e-6


def test_compute_outcomes_card_delta():
    p1 = _make_player("player_0", 20, 10)
    p2 = _make_player("player_1", 20, 12)
    game = _make_minimal_game([p1, p2], winner=p1)
    outcomes = compute_outcomes(game)
    # p2: 20/20 + (12-10)*0.001 = 1.002 → clamped to 1.0
    assert outcomes["player_1"] == 1.0


def test_compute_outcomes_clamped_to_zero():
    p1 = _make_player("player_0", 20, 10)
    p2 = _make_player("player_1", 0, 0)
    game = _make_minimal_game([p1, p2], winner=p1)
    outcomes = compute_outcomes(game)
    assert outcomes["player_1"] == 0.0


def _make_minimal_game(players, winner):
    from pokemon_splendor.data.loader import load_pokedex
    from pathlib import Path
    from pokemon_splendor.engine.env import PokemonSplendorEnv
    env = PokemonSplendorEnv(Path("data/pokemon.jsonl"), num_players=len(players))
    env.reset()
    game = env.game
    game.players = players
    game.winner = winner
    game.turn = players[0]
    return game
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_alpha.py::test_compute_outcomes_winner_gets_one -v
```
Expected: `ImportError: cannot import name 'compute_outcomes'`

- [ ] **Step 3: Implement compute_outcomes**

```python
# src/pokemon_splendor/agents/alpha_coach.py
from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
import random
import torch
import torch.nn.functional as F
from pokemon_splendor.models import Game


def compute_outcomes(game: Game) -> dict[str, float]:
    winner = game.winner
    winner_score = winner.points
    winner_cards = len([c for c in winner.cards if not c.evolved])
    outcomes = {}
    for player in game.players:
        active_cards = len([c for c in player.cards if not c.evolved])
        card_delta = (active_cards - winner_cards) * 0.001
        outcome = player.points / winner_score + card_delta
        outcomes[player.name] = max(0.0, min(1.0, outcome))
    return outcomes
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_alpha.py -k "compute_outcomes" -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/pokemon_splendor/agents/alpha_coach.py tests/test_alpha.py
git commit -m "feat: add compute_outcomes for alpha self-play"
```

---

### Task 3: AlphaMCTSAgent — MCTS using network for eval and UCB prior

**Files:**
- Create: `src/pokemon_splendor/agents/alpha_mcts.py`
- Test: `tests/test_alpha.py` (append)

Context: `MCTSAgent` in `agents/mcts.py` is the reference implementation. `AlphaMCTSAgent` reuses the same tree structure but:
1. `AlphaMCTSNode` adds a `prior: float` field (policy probability from parent's network call)
2. UCB formula: `total_value/visits + C * prior * sqrt(parent.visits) / (1 + visits)`
3. `_expand` calls the network policy head to set priors on all children at expansion time
4. `_evaluate` calls the network value head instead of `evaluate_position`
5. `act` returns both the chosen action and the visit count distribution (needed for training)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_alpha.py`:

```python
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.agents.alpha_mcts import AlphaMCTSAgent
from pokemon_splendor.agents.alpha_net import AlphaNet


def _make_env_and_agent(n_sims=10):
    env = PokemonSplendorEnv(Path("data/pokemon.jsonl"), num_players=2)
    env.reset()
    name = env.agent_selection
    net = AlphaNet()
    agent = AlphaMCTSAgent(env, name, network=net, n_simulations=n_sims, depth=2)
    return env, agent, name


def test_alpha_mcts_returns_valid_action():
    env, agent, name = _make_env_and_agent()
    obs, _, _, _, _ = env.last()
    mask = env.action_mask(name)
    action, visit_counts = agent.act(obs, mask)
    assert mask[action], "chosen action must be valid"


def test_alpha_mcts_visit_counts_shape():
    env, agent, name = _make_env_and_agent()
    obs, _, _, _, _ = env.last()
    mask = env.action_mask(name)
    action, visit_counts = agent.act(obs, mask)
    assert len(visit_counts) == 108
    assert abs(sum(visit_counts) - 1.0) < 1e-5


def test_alpha_mcts_visit_counts_only_valid():
    env, agent, name = _make_env_and_agent()
    obs, _, _, _, _ = env.last()
    mask = env.action_mask(name)
    action, visit_counts = agent.act(obs, mask)
    for i, prob in enumerate(visit_counts):
        if not mask[i]:
            assert prob == 0.0, f"invalid action {i} has non-zero visit count"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_alpha.py -k "alpha_mcts" -v
```
Expected: `ImportError: cannot import name 'AlphaMCTSAgent'`

- [ ] **Step 3: Implement AlphaMCTSAgent**

```python
# src/pokemon_splendor/agents/alpha_mcts.py
import math
import pickle
import torch
import numpy as np
from dataclasses import dataclass, field
from pokemon_splendor.models import Game, Player, GamePhase, PokeballType
from pokemon_splendor.engine.simulator import _step_inplace
from pokemon_splendor.engine.observation import compute_mask, compute_observation
from pokemon_splendor.engine.rules import get_player_bonuses
from pokemon_splendor.engine.actions import (
    TOTAL_ACTIONS, TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START,
    RESERVE_MASTER_START, EVOLVE_START, EVOLVE_PASS, DISCARD_ACTION,
)
from pokemon_splendor.agents.base import RuleBasedAgent
from pokemon_splendor.agents.alpha_net import AlphaNet

_C = math.sqrt(2)


def _clone(game: Game) -> Game:
    return pickle.loads(pickle.dumps(game, protocol=5))


@dataclass
class AlphaMCTSNode:
    game: Game
    parent: "AlphaMCTSNode | None"
    action: int | None
    prior: float = 0.0
    depth: int = 0
    visits: int = 0
    total_value: float = 0.0
    children: dict[int, "AlphaMCTSNode"] = field(default_factory=dict)
    untried_actions: list[int] = field(default_factory=list)


class AlphaMCTSAgent(RuleBasedAgent):
    def __init__(self, env, player_name: str, network: AlphaNet,
                 n_simulations: int = 100, depth: int = 4):
        super().__init__(env, player_name)
        self._network = network
        self._n_simulations = n_simulations
        self._depth = depth

    def act(self, obs: np.ndarray, mask: np.ndarray) -> tuple[int, list[float]]:
        game = _clone(self._game)

        if game.phase == GamePhase.DISCARD:
            action = self._best_discard_action(game, mask)
            visit_counts = [0.0] * TOTAL_ACTIONS
            visit_counts[action] = 1.0
            return action, visit_counts

        valid_actions = list(np.where(mask)[0])
        if not valid_actions:
            action = int(np.where(mask)[0][0])
            visit_counts = [0.0] * TOTAL_ACTIONS
            visit_counts[action] = 1.0
            return action, visit_counts

        root = AlphaMCTSNode(
            game=game, parent=None, action=None, depth=0,
            untried_actions=list(valid_actions),
        )
        for _ in range(self._n_simulations):
            self._simulate(root)

        if not root.children:
            action = valid_actions[0]
            visit_counts = [0.0] * TOTAL_ACTIONS
            visit_counts[action] = 1.0
            return action, visit_counts

        total_visits = sum(c.visits for c in root.children.values())
        visit_counts = [0.0] * TOTAL_ACTIONS
        for a, child in root.children.items():
            visit_counts[a] = child.visits / total_visits if total_visits > 0 else 0.0

        action = max(root.children.values(), key=lambda c: c.visits).action
        return action, visit_counts

    def _simulate(self, root: AlphaMCTSNode) -> None:
        node = self._select(root)
        if node.untried_actions and not self._is_terminal(node):
            node = self._expand(node)
        value = self._evaluate(node)
        self._backpropagate(node, value)

    def _select(self, node: AlphaMCTSNode) -> AlphaMCTSNode:
        while not node.untried_actions and node.children and not self._is_terminal(node):
            node = max(node.children.values(), key=lambda c: self._ucb(c, node))
        return node

    def _ucb(self, node: AlphaMCTSNode, parent: AlphaMCTSNode) -> float:
        if node.visits == 0:
            return float("inf")
        exploit = node.total_value / node.visits
        explore = _C * node.prior * math.sqrt(parent.visits) / (1 + node.visits)
        return exploit + explore

    def _expand(self, node: AlphaMCTSNode) -> AlphaMCTSNode:
        action = node.untried_actions.pop()
        game = _clone(node.game)
        is_terminal = _step_inplace(game, action, self._player_name)

        while (not is_terminal
               and game.turn.name == self._player_name
               and game.phase == GamePhase.DISCARD):
            player = next(p for p in game.players if p.name == self._player_name)
            discard_mask = compute_mask(game, self._player_name)
            d_action = self._best_discard_action(game, discard_mask)
            is_terminal = _step_inplace(game, d_action, self._player_name)

        while not is_terminal and game.turn.name != self._player_name:
            opp_name = game.turn.name
            opp_obs = torch.tensor(compute_observation(game, opp_name), dtype=torch.float32)
            opp_mask_np = compute_mask(game, opp_name)
            opp_mask = torch.tensor(opp_mask_np, dtype=torch.bool)
            with torch.no_grad():
                opp_policy, _ = self._network(opp_obs, opp_mask)
            opp_action = int(torch.multinomial(opp_policy, 1).item())
            is_terminal = _step_inplace(game, opp_action, opp_name)

        our_player = next(p for p in game.players if p.name == self._player_name)
        if not is_terminal and node.depth + 1 < self._depth:
            child_mask_np = compute_mask(game, self._player_name)
            untried = list(np.where(child_mask_np)[0])
            child_obs = torch.tensor(compute_observation(game, self._player_name), dtype=torch.float32)
            child_mask = torch.tensor(child_mask_np, dtype=torch.bool)
            with torch.no_grad():
                priors, _ = self._network(child_obs, child_mask)
            priors_np = priors.numpy()
        else:
            untried = []
            priors_np = None

        child = AlphaMCTSNode(
            game=game, parent=node, action=action,
            prior=priors_np[action] if priors_np is not None else 1.0,
            depth=node.depth + 1, untried_actions=untried,
        )
        node.children[action] = child
        return child

    def _evaluate(self, node: AlphaMCTSNode) -> float:
        if self._is_terminal(node):
            if node.game.winner is None:
                return 0.5
            return 1.0 if node.game.winner.name == self._player_name else 0.0
        obs = torch.tensor(
            compute_observation(node.game, self._player_name), dtype=torch.float32
        )
        mask = torch.tensor(compute_mask(node.game, self._player_name), dtype=torch.bool)
        with torch.no_grad():
            _, value = self._network(obs, mask)
        return value.item()

    def _backpropagate(self, node: AlphaMCTSNode, value: float) -> None:
        while node is not None:
            node.visits += 1
            node.total_value += value
            node = node.parent

    def _is_terminal(self, node: AlphaMCTSNode) -> bool:
        return node.game.winner is not None

    def _best_discard_action(self, game: Game, mask: np.ndarray) -> int:
        from collections import Counter
        from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost
        player = next(p for p in game.players if p.name == self._player_name)
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_alpha.py -k "alpha_mcts" -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/pokemon_splendor/agents/alpha_mcts.py tests/test_alpha.py
git commit -m "feat: add AlphaMCTSAgent with network-guided UCB and value eval"
```

---

### Task 4: Self-play game runner — collect training records

**Files:**
- Modify: `src/pokemon_splendor/agents/alpha_coach.py` (append)
- Test: `tests/test_alpha.py` (append)

A self-play game runs all players using `AlphaMCTSAgent` with the same network. Each move records `(obs, visit_counts)`. At game end, outcomes are computed and attached, producing a list of `SelfPlayRecord`.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_alpha.py`:

```python
from pokemon_splendor.agents.alpha_coach import run_self_play_game, SelfPlayRecord


def test_self_play_game_returns_records():
    net = AlphaNet()
    records = run_self_play_game(Path("data/pokemon.jsonl"), net, num_players=2, n_simulations=5, depth=1)
    assert len(records) > 0


def test_self_play_record_fields():
    net = AlphaNet()
    records = run_self_play_game(Path("data/pokemon.jsonl"), net, num_players=2, n_simulations=5, depth=1)
    r = records[0]
    assert r.obs.shape == (345,)
    assert len(r.visit_counts) == 108
    assert abs(sum(r.visit_counts) - 1.0) < 1e-5
    assert 0.0 <= r.outcome <= 1.0


def test_self_play_game_terminates():
    net = AlphaNet()
    records = run_self_play_game(Path("data/pokemon.jsonl"), net, num_players=2, n_simulations=5, depth=1)
    assert len(records) >= 10
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_alpha.py -k "self_play" -v
```
Expected: `ImportError: cannot import name 'run_self_play_game'`

- [ ] **Step 3: Implement SelfPlayRecord and run_self_play_game**

Append to `src/pokemon_splendor/agents/alpha_coach.py`:

```python
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.agents.alpha_mcts import AlphaMCTSAgent
from pokemon_splendor.agents.alpha_net import AlphaNet

MAX_STEPS = 100000


@dataclass
class SelfPlayRecord:
    obs: np.ndarray
    visit_counts: list[float]
    outcome: float


def run_self_play_game(
    jsonl_path: Path,
    network: AlphaNet,
    num_players: int = 2,
    n_simulations: int = 100,
    depth: int = 4,
) -> list[SelfPlayRecord]:
    env = PokemonSplendorEnv(jsonl_path, num_players=num_players)
    env.reset()

    agents = {
        name: AlphaMCTSAgent(env, name, network=network,
                             n_simulations=n_simulations, depth=depth)
        for name in env.possible_agents
    }

    move_records: list[tuple[str, np.ndarray, list[float]]] = []

    for _ in range(MAX_STEPS):
        if not env.agents:
            break
        name = env.agent_selection
        obs, _, term, trunc, _ = env.last()
        if term or trunc:
            break
        mask = env.action_mask(name)
        action, visit_counts = agents[name].act(obs, mask)
        move_records.append((name, obs.copy(), visit_counts))
        env.step(action)

    outcomes = compute_outcomes(env.game)
    return [
        SelfPlayRecord(obs=obs, visit_counts=vc, outcome=outcomes[name])
        for name, obs, vc in move_records
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_alpha.py -k "self_play" -v
```
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/pokemon_splendor/agents/alpha_coach.py tests/test_alpha.py
git commit -m "feat: add self-play game runner producing SelfPlayRecord list"
```

---

### Task 5: Training step — train network on replay buffer batch

**Files:**
- Modify: `src/pokemon_splendor/agents/alpha_coach.py` (append)
- Test: `tests/test_alpha.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_alpha.py`:

```python
from pokemon_splendor.agents.alpha_coach import train_step


def test_train_step_returns_losses():
    net = AlphaNet()
    optimizer = torch.optim.Adam(net.parameters(), lr=0.001)
    batch = [
        SelfPlayRecord(
            obs=np.random.rand(345).astype(np.float32),
            visit_counts=[1.0 / 108] * 108,
            outcome=0.5,
        )
        for _ in range(8)
    ]
    policy_loss, value_loss = train_step(net, optimizer, batch)
    assert policy_loss >= 0.0
    assert value_loss >= 0.0


def test_train_step_updates_weights():
    net = AlphaNet()
    optimizer = torch.optim.Adam(net.parameters(), lr=0.01)
    batch = [
        SelfPlayRecord(
            obs=np.random.rand(345).astype(np.float32),
            visit_counts=[1.0 / 108] * 108,
            outcome=1.0,
        )
        for _ in range(8)
    ]
    before = net.value_head.weight.data.clone()
    train_step(net, optimizer, batch)
    after = net.value_head.weight.data
    assert not torch.allclose(before, after)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_alpha.py -k "train_step" -v
```
Expected: `ImportError: cannot import name 'train_step'`

- [ ] **Step 3: Implement train_step**

Append to `src/pokemon_splendor/agents/alpha_coach.py`:

```python
import torch.optim


def train_step(
    network: AlphaNet,
    optimizer: torch.optim.Optimizer,
    batch: list[SelfPlayRecord],
) -> tuple[float, float]:
    network.train()
    obs_batch = torch.tensor(
        np.stack([r.obs for r in batch]), dtype=torch.float32
    )
    visit_batch = torch.tensor(
        np.array([r.visit_counts for r in batch]), dtype=torch.float32
    )
    outcome_batch = torch.tensor(
        [r.outcome for r in batch], dtype=torch.float32
    )
    mask_batch = (visit_batch > 0).bool()
    mask_batch |= mask_batch  # any action with nonzero visits is valid

    policy, value = network(obs_batch, torch.ones_like(mask_batch))

    policy_loss = -(visit_batch * torch.log(policy.clamp(min=1e-8))).sum(dim=-1).mean()
    value_loss = F.mse_loss(value, outcome_batch)
    loss = policy_loss + value_loss

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    network.eval()
    return policy_loss.item(), value_loss.item()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_alpha.py -k "train_step" -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/pokemon_splendor/agents/alpha_coach.py tests/test_alpha.py
git commit -m "feat: add train_step with policy cross-entropy and value MSE losses"
```

---

### Task 6: AlphaCoach — full self-play training loop

**Files:**
- Modify: `src/pokemon_splendor/agents/alpha_coach.py` (append)
- Test: `tests/test_alpha.py` (append)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_alpha.py`:

```python
import tempfile, os
from pokemon_splendor.agents.alpha_coach import AlphaCoach


def test_alpha_coach_runs_one_iteration():
    with tempfile.TemporaryDirectory() as tmpdir:
        coach = AlphaCoach(
            jsonl_path=Path("data/pokemon.jsonl"),
            num_players=2,
            n_iterations=1,
            games_per_iteration=2,
            n_simulations=5,
            depth=1,
            batch_size=4,
            buffer_size=100,
            checkpoint_dir=tmpdir,
        )
        coach.run()
        files = os.listdir(tmpdir)
        assert any(f.endswith(".pt") for f in files)


def test_alpha_coach_saves_checkpoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        coach = AlphaCoach(
            jsonl_path=Path("data/pokemon.jsonl"),
            num_players=2,
            n_iterations=2,
            games_per_iteration=2,
            n_simulations=5,
            depth=1,
            batch_size=4,
            buffer_size=100,
            checkpoint_dir=tmpdir,
        )
        coach.run()
        files = os.listdir(tmpdir)
        pt_files = [f for f in files if f.endswith(".pt")]
        assert len(pt_files) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_alpha.py -k "alpha_coach" -v
```
Expected: `ImportError: cannot import name 'AlphaCoach'`

- [ ] **Step 3: Implement AlphaCoach**

Append to `src/pokemon_splendor/agents/alpha_coach.py`:

```python
import os


class AlphaCoach:
    def __init__(
        self,
        jsonl_path: Path,
        num_players: int = 2,
        n_iterations: int = 100,
        games_per_iteration: int = 20,
        n_simulations: int = 100,
        depth: int = 4,
        batch_size: int = 256,
        buffer_size: int = 2000,
        lr: float = 0.001,
        checkpoint_dir: str = "checkpoints",
    ):
        self._jsonl_path = jsonl_path
        self._num_players = num_players
        self._n_iterations = n_iterations
        self._games_per_iteration = games_per_iteration
        self._n_simulations = n_simulations
        self._depth = depth
        self._batch_size = batch_size
        self._buffer_size = buffer_size
        self._lr = lr
        self._checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)

    def run(self) -> None:
        network = AlphaNet()
        network.eval()
        optimizer = torch.optim.Adam(network.parameters(), lr=self._lr)
        replay_buffer: deque[SelfPlayRecord] = deque(maxlen=self._buffer_size)

        for iteration in range(1, self._n_iterations + 1):
            print(f"\n[Iteration {iteration}/{self._n_iterations}]")

            # Self-play
            for game_num in range(1, self._games_per_iteration + 1):
                records = run_self_play_game(
                    self._jsonl_path, network,
                    num_players=self._num_players,
                    n_simulations=self._n_simulations,
                    depth=self._depth,
                )
                replay_buffer.extend(records)
                print(f"  game {game_num}/{self._games_per_iteration} — {len(records)} records", flush=True)

            # Train
            if len(replay_buffer) >= self._batch_size:
                batch = random.sample(list(replay_buffer), self._batch_size)
                policy_loss, value_loss = train_step(network, optimizer, batch)
                print(f"  policy_loss={policy_loss:.4f}  value_loss={value_loss:.4f}")

            # Checkpoint
            path = os.path.join(self._checkpoint_dir, f"alpha_{iteration:04d}.pt")
            network.save(path)
            print(f"  saved {path}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_alpha.py -k "alpha_coach" -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/pokemon_splendor/agents/alpha_coach.py tests/test_alpha.py
git commit -m "feat: add AlphaCoach self-play training loop with replay buffer"
```

---

### Task 7: Wire into CLI — alpha-train mode and alpha agent type

**Files:**
- Modify: `src/pokemon_splendor/__main__.py` (append only — new mode + agent type)
- Test: manual smoke test only

- [ ] **Step 1: Add `alpha-train` to mode choices and argument**

In `__main__.py`, find:
```python
parser.add_argument("--mode", choices=["play", "train", "benchmark", "data"], default="play")
```
Change to:
```python
parser.add_argument("--mode", choices=["play", "train", "benchmark", "data", "alpha-train"], default="play")
```

- [ ] **Step 2: Add alpha-train CLI flags**

After the existing `--mcts-opponent` argument, append:
```python
parser.add_argument("--alpha-iters", type=int, default=100,
                    help="Alpha training: number of self-play iterations")
parser.add_argument("--alpha-games", type=int, default=20,
                    help="Alpha training: self-play games per iteration")
parser.add_argument("--alpha-sims", type=int, default=100,
                    help="Alpha training: MCTS simulations per move")
parser.add_argument("--alpha-depth", type=int, default=4,
                    help="Alpha training: MCTS cutoff depth")
parser.add_argument("--alpha-checkpoint-dir", default="alpha_checkpoints",
                    help="Alpha training: directory for .pt checkpoint files")
```

- [ ] **Step 3: Add alpha-train dispatch in main()**

After `elif args.mode == "benchmark":`, append:
```python
elif args.mode == "alpha-train":
    _run_alpha_train(
        jsonl, args.alpha_iters, args.alpha_games,
        args.alpha_sims, args.alpha_depth,
        len(agent_types), args.alpha_checkpoint_dir,
    )
```

- [ ] **Step 4: Implement _run_alpha_train()**

Append to `__main__.py`:
```python
def _run_alpha_train(
    jsonl: Path, n_iterations: int, games_per_iteration: int,
    n_simulations: int, depth: int, num_players: int, checkpoint_dir: str,
):
    from pokemon_splendor.agents.alpha_coach import AlphaCoach
    coach = AlphaCoach(
        jsonl_path=jsonl,
        num_players=num_players,
        n_iterations=n_iterations,
        games_per_iteration=games_per_iteration,
        n_simulations=n_simulations,
        depth=depth,
        checkpoint_dir=checkpoint_dir,
    )
    coach.run()
```

- [ ] **Step 5: Add `alpha:<path>` agent type in _make_agent()**

After the `"mcts"` block in `_make_agent`, append:
```python
if agent_type.startswith("alpha:"):
    model_path = agent_type.split(":", 1)[1]
    from pokemon_splendor.agents.alpha_net import AlphaNet
    from pokemon_splendor.agents.alpha_mcts import AlphaMCTSAgent
    net = AlphaNet.load(model_path)
    return AlphaMCTSAgent(env, player_name, network=net,
                          n_simulations=mcts_sims, depth=mcts_depth)
```

- [ ] **Step 6: Smoke test**

```bash
uv run pokemon-splendor --mode alpha-train \
  --alpha-iters 2 --alpha-games 2 --alpha-sims 10 --alpha-depth 1 \
  --alpha-checkpoint-dir /tmp/alpha_smoke
ls /tmp/alpha_smoke
```
Expected: `alpha_0001.pt  alpha_0002.pt`

- [ ] **Step 7: Commit**

```bash
git add src/pokemon_splendor/__main__.py
git commit -m "feat: wire alpha-train mode and alpha:<path> agent into CLI"
```

---

### Task 8: Run all tests

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest tests/ -v
```
Expected: all existing tests pass, all new alpha tests pass

- [ ] **Step 2: Commit if any fixes needed**

```bash
git add -p
git commit -m "fix: address any issues found in full test run"
```
