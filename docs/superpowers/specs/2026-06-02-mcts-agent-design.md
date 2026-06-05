# MCTS Agent Design

**Goal:** Implement a Monte Carlo Tree Search agent with early cutoff and action pruning that beats early-capture in head-to-head play.

**Architecture:** Full UCB tree built over the MCTS agent's own decisions only. Between our nodes, opponents act via a pluggable policy (default: early-capture). At cutoff depth, a shortfall-based evaluation function estimates position value. Action pruning reduces the branching factor from ~40–50 to ~10–20 per node.

**Tech Stack:** Python, `copy.deepcopy`, existing `rules.py` functions, `sb3_contrib.MaskablePPO` (optional RL opponent policy).

---

## New Files

### `engine/eval.py`
Shortfall-based position evaluation function used by MCTS at cutoff depth.

```python
BASE_ALPHA = 1.0
WIN_SCORE = 18.0

def evaluate_position(game: Game, player: Player) -> float:
    """
    Returns estimated position value in ~[0, 1].
    player.points / WIN_SCORE + alpha * max(card.point / (rounds_to_catch + 1))
    where rounds_to_catch = ceil(shortfall / 3).
    """
```

`env.py` keeps its own `_phi` and constants unchanged — `eval.py` is independent.

### `engine/simulator.py`
Minimal game runner for MCTS tree expansion. Applies one action to a deep-copied game state, handles phase transitions, turn switching, and win detection — without env reward/observation machinery.

```python
def game_step(game: Game, action: int, player_name: str) -> tuple[Game, bool]:
    """
    Returns (new_game, is_terminal).
    Applies action, advances through DISCARD/EVOLVE phases automatically,
    switches to next player's turn. Handles 2–4 players cycling correctly.
    """
```

### `engine/observation.py`
Pure refactor — extracts `compute_observation` and `compute_mask` from `PokemonSplendorEnv` with no logic changes. `env.py` calls these internally after the refactor.

```python
def compute_observation(game: Game, player_name: str) -> np.ndarray: ...
def compute_mask(game: Game, player_name: str) -> np.ndarray: ...
```

### `agents/mcts.py`
Main MCTS agent and supporting utilities.

```python
@dataclass
class MCTSNode:
    game: Game
    parent: MCTSNode | None
    action: int | None
    visits: int = 0
    total_value: float = 0.0
    children: dict[int, MCTSNode] = field(default_factory=dict)
    untried_actions: list[int] = field(default_factory=list)

class MCTSAgent(RuleBasedAgent):
    def __init__(self, env, player_name, n_simulations=200, depth=4,
                 opponent_policy=None): ...
    def act(self, obs, mask) -> int: ...

def make_early_capture_policy() -> Callable[[Game, str], int]: ...
def make_rl_policy(model_path: str) -> Callable[[Game, str], int]: ...
```

### `tests/test_mcts.py`
Tests for pruning logic, eval function, simulator, and agent integration.

---

## Modified Files

### `engine/env.py`
- Calls `compute_observation` and `compute_mask` from `engine/observation.py`
- All reward shaping logic (`_phi`, `BASE_ALPHA`, `WIN_SCORE`, `GAMMA_SHAPING`) unchanged

### `__main__.py`
- Adds `"mcts"` to `_make_agent` and `AGENT_TYPES` help string

---

## MCTS Algorithm

**UCB selection:**
```
UCB(node) = total_value / visits + √2 × sqrt(ln(parent.visits) / visits)
```
Unvisited nodes (visits=0) have UCB=∞ and are always tried first.

**One simulation (select → expand → evaluate → backpropagate):**
1. **Select** — walk the tree choosing the highest-UCB child until reaching a node with untried actions or a terminal state
2. **Expand** — pick one untried action, apply it via `game_step`; then advance opponent turns via `opponent_policy` until it is the MCTS agent's turn again; create child node
3. **Evaluate** — terminal state: 1.0 (win) or 0.0 (loss); depth ≥ cutoff: `evaluate_position(game, player)`; otherwise continue selecting
4. **Backpropagate** — walk up to root, incrementing `visits` and adding result to `total_value`

**Move selection:** after N simulations, return the root child with the most visits.

---

## Action Pruning

Applied at each node expansion to compute `untried_actions`.

### Token-taking
- **Keep:** all valid TAKE_SAME combos (take 2 of same type)
- **Keep:** only 3-token TAKE_DIFF combos — drop all 1-token and 2-token subsets
- **Result:** ≤15 actions (vs 30 unpruned)

### Catch
- Keep all valid catch actions (board + reserved)
- No pruning

### Reserve
Hard filters — remove any slot where:
- A catching that card puts the player at ≥18 points (winning catch available)
- Player already holds 2+ reserved cards
- Card is Common tier, 0 points, and has no bonus
- RESERVE_NO_MASTER is valid for a slot where RESERVE_MASTER is also valid (master token strictly better when board has master tokens)

Remaining candidates scored:
```
reserve_score = card.point
              + rounds_until_best_opponent_catches(card)
              - rounds_to_catch(me, card)
```
Keep top-5 by score.

### Evolve
- Fully expanded in the tree — no pruning
- Options: each valid evolve action + EVOLVE_PASS
- Branching factor is small in practice (≤3 evolvable cards + pass)

### Discard
- Collapsed to a single forced action — not branched in the tree
- Discard the token type that increases total shortfall across all board cards the least

---

## Eval Function: `evaluate_position`

```python
def evaluate_position(game: Game, player: Player) -> float:
    bonuses = get_player_bonuses(player)
    ptokens = Counter(t.name for t in player.tokens)
    all_slots = (game.board.common_revealed + game.board.uncommon_revealed
                 + game.board.rare_revealed + game.board.epic_revealed
                 + game.board.legendary_revealed)
    max_val = 0.0
    for card in all_slots:
        if card is None:
            continue
        ec = calculate_effective_cost(card, bonuses)
        master_req = max(ec.get(PokeballType.Master, 0),
                         1 if card.tier in (Tier.Epic, Tier.Legendary) else 0)
        if ptokens.get(PokeballType.Master, 0) < master_req:
            continue
        shortfall = sum(max(0, ec.get(pt, 0) - ptokens.get(pt, 0))
                        for pt in PokeballType if pt != PokeballType.Master)
        rounds = (shortfall + 2) // 3
        max_val = max(max_val, card.point / (rounds + 1))
    alpha = BASE_ALPHA / max(1, len(game.players) - 1)
    return (player.points + alpha * max_val) / WIN_SCORE
```

---

## Opponent Policy Interface

```python
OpponentPolicy = Callable[[Game, str], int]
```

**`make_early_capture_policy()`** — standalone early-capture logic, no env dependency.

**`make_rl_policy(model_path)`** — loads a MaskablePPO model; uses `compute_observation` and `compute_mask` from `engine/observation.py` to produce the action.

Default in `MCTSAgent.__init__`: `opponent_policy=make_early_capture_policy()`.

Swapping to a trained model:
```python
MCTSAgent(env, player_name, opponent_policy=make_rl_policy("v7b.zip"))
```

---

## CLI Integration

```
uv run pokemon-splendor --players mcts,early-capture --mode benchmark --games 100
```

`MCTSAgent` is wired into `_make_agent` under the key `"mcts"`. No new CLI flags needed — `n_simulations` and `depth` use defaults for now.

---

## Testing (`tests/test_mcts.py`)

- `test_evaluate_position_no_board` — empty board returns points/WIN_SCORE
- `test_evaluate_position_shortfall` — card 2 turns away scores card.point/3
- `test_evaluate_position_affordable_now` — card with no shortfall scores card.point/1
- `test_prune_tokens_no_short_combos` — 1- and 2-token TAKE_DIFF combos excluded
- `test_prune_reserve_winning_catch_available` — reserve dropped when winning catch exists
- `test_prune_reserve_master_preferred` — RESERVE_NO_MASTER dropped when RESERVE_MASTER valid
- `test_prune_reserve_top5` — at most 5 reserve actions in pruned set
- `test_game_step_advances_turn` — simulator switches to next player after action
- `test_game_step_terminal` — simulator detects win condition
- `test_mcts_agent_returns_valid_action` — agent act() returns a valid masked action
- `test_mcts_beats_random` — MCTS wins >60% vs random over 50 games
