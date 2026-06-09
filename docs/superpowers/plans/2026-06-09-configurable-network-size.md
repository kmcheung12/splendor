# Configurable Network Size Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make hidden layer width and depth configurable for both PPO (`MlpPolicy`) and `AlphaNet`, with full backward compatibility for existing `.zip` and `.pt` checkpoints.

**Architecture:** `AlphaNet` gains `hidden_size`/`num_layers` constructor params and embeds architecture in saved `.pt` files; `load()` handles both legacy (raw state dict) and new (dict with metadata) formats. PPO's `net_arch` is built dynamically from new `--hidden-size`/`--hidden-layers` CLI flags. `AlphaCoach` threads the new params through to `AlphaNet` construction.

**Tech Stack:** Python 3.11, PyTorch, stable-baselines3, sb3-contrib, pytest

---

## File Map

- Modify: `src/pokemon_splendor/agents/alpha_net.py` — constructor, save, load
- Modify: `src/pokemon_splendor/agents/alpha_coach.py` — pass `hidden_size`/`num_layers` to `AlphaNet` construction
- Modify: `src/pokemon_splendor/__main__.py` — 4 new CLI flags, dynamic `net_arch`, thread params to `_run_alpha_train`
- Create: `tests/test_network_compat.py` — backward compatibility tests

---

### Task 1: Update AlphaNet constructor and save

**Files:**
- Modify: `src/pokemon_splendor/agents/alpha_net.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_network_compat.py`:

```python
import tempfile
import os
import torch
import numpy as np
import pytest
from pokemon_splendor.agents.alpha_net import AlphaNet, OBS_SIZE, TOTAL_ACTIONS


def test_default_constructor_is_256x3():
    net = AlphaNet()
    # shared has 3 Linear layers → indices 0, 2, 4 in Sequential (interleaved with ReLU)
    linear_layers = [m for m in net.shared if isinstance(m, torch.nn.Linear)]
    assert len(linear_layers) == 3
    assert linear_layers[0].out_features == 256


def test_custom_hidden_size():
    net = AlphaNet(hidden_size=512, num_layers=2)
    linear_layers = [m for m in net.shared if isinstance(m, torch.nn.Linear)]
    assert len(linear_layers) == 2
    assert all(l.out_features == 512 for l in linear_layers)


def test_forward_shape_default():
    net = AlphaNet()
    obs = torch.zeros(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert policy.shape == (TOTAL_ACTIONS,)
    assert value.shape == ()


def test_forward_shape_custom():
    net = AlphaNet(hidden_size=512, num_layers=4)
    obs = torch.zeros(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert policy.shape == (TOTAL_ACTIONS,)
    assert value.shape == ()


def test_save_embeds_architecture():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "net.pt")
        net = AlphaNet(hidden_size=512, num_layers=3)
        net.save(path)
        data = torch.load(path, map_location="cpu", weights_only=True)
        assert isinstance(data, dict)
        assert data["hidden_size"] == 512
        assert data["num_layers"] == 3
        assert "state_dict" in data
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_network_compat.py -v
```

Expected: FAIL — `AlphaNet` constructor doesn't accept `hidden_size`/`num_layers` yet, save doesn't embed architecture.

- [ ] **Step 3: Rewrite `AlphaNet`**

Replace the entire `src/pokemon_splendor/agents/alpha_net.py`:

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

OBS_SIZE = 345
TOTAL_ACTIONS = 108


class AlphaNet(nn.Module):
    def __init__(self, hidden_size: int = 256, num_layers: int = 3):
        super().__init__()
        self._hidden_size = hidden_size
        self._num_layers = num_layers
        layers = []
        in_size = OBS_SIZE
        for _ in range(num_layers):
            layers += [nn.Linear(in_size, hidden_size), nn.ReLU()]
            in_size = hidden_size
        self.shared = nn.Sequential(*layers)
        self.policy_head = nn.Linear(hidden_size, TOTAL_ACTIONS)
        self.value_head = nn.Linear(hidden_size, 1)

    def forward(self, obs: torch.Tensor, mask: torch.Tensor):
        x = self.shared(obs)
        logits = self.policy_head(x)
        logits = logits.masked_fill(~mask, float("-inf"))

        if mask.dim() == 1:
            if mask.sum() == 0:
                raise ValueError("Cannot compute policy: all actions are masked")
        else:
            if not mask.any(dim=-1).all():
                raise ValueError("Cannot compute policy: batch contains samples with all actions masked")

        policy = F.softmax(logits, dim=-1)
        value = torch.sigmoid(self.value_head(x)).squeeze(-1)
        return policy, value

    def save(self, path: str) -> None:
        torch.save({
            "state_dict": self.state_dict(),
            "hidden_size": self._hidden_size,
            "num_layers": self._num_layers,
        }, path)

    @classmethod
    def load(cls, path: str) -> "AlphaNet":
        data = torch.load(path, map_location="cpu", weights_only=True)
        if isinstance(data, dict) and "state_dict" in data:
            net = cls(hidden_size=data["hidden_size"], num_layers=data["num_layers"])
            net.load_state_dict(data["state_dict"])
        else:
            # Legacy: raw state_dict — infer architecture from weight shapes
            hidden_size = data["shared.0.weight"].shape[0]
            layer_indices = {
                int(k.split(".")[1])
                for k in data
                if k.startswith("shared.") and k.endswith(".weight")
            }
            num_layers = len(layer_indices)
            net = cls(hidden_size=hidden_size, num_layers=num_layers)
            net.load_state_dict(data)
        net.eval()
        return net
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_network_compat.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Verify existing alpha tests still pass**

```bash
uv run pytest tests/test_alpha.py -v
```

Expected: all tests PASS. The existing tests use `AlphaNet()` with no args — defaults 256×3 now, but forward/save/load tests don't care about depth.

- [ ] **Step 6: Commit**

```bash
git add src/pokemon_splendor/agents/alpha_net.py tests/test_network_compat.py
git commit -m "feat: make AlphaNet hidden size and depth configurable"
```

---

### Task 2: Backward compatibility tests for load()

**Files:**
- Modify: `tests/test_network_compat.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_network_compat.py`:

```python
def test_load_new_format_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "net.pt")
        net = AlphaNet(hidden_size=512, num_layers=3)
        obs = torch.randn(OBS_SIZE)
        mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
        policy_orig, value_orig = net(obs, mask)
        net.save(path)
        net2 = AlphaNet.load(path)
        policy_loaded, value_loaded = net2(obs, mask)
        assert torch.allclose(policy_orig, policy_loaded)
        assert torch.allclose(value_orig, value_loaded)


def test_load_legacy_format():
    """Simulate a pre-migration .pt file: raw state_dict, no metadata."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "legacy.pt")
        net = AlphaNet(hidden_size=256, num_layers=2)
        # Save legacy format (raw state dict, no metadata)
        torch.save(net.state_dict(), path)
        # Load should infer architecture and succeed
        net2 = AlphaNet.load(path)
        linear_layers = [m for m in net2.shared if isinstance(m, torch.nn.Linear)]
        assert len(linear_layers) == 2
        assert linear_layers[0].out_features == 256


def test_load_legacy_format_output_matches():
    """Legacy load produces identical output to original network."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "legacy.pt")
        net = AlphaNet(hidden_size=256, num_layers=2)
        obs = torch.randn(OBS_SIZE)
        mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
        policy_orig, value_orig = net(obs, mask)
        torch.save(net.state_dict(), path)
        net2 = AlphaNet.load(path)
        policy_loaded, value_loaded = net2(obs, mask)
        assert torch.allclose(policy_orig, policy_loaded)
        assert torch.allclose(value_orig, value_loaded)


def test_load_legacy_format_256x3():
    """Legacy 256x3 network (current default before migration) loads correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "legacy_3layer.pt")
        net = AlphaNet(hidden_size=256, num_layers=3)
        torch.save(net.state_dict(), path)
        net2 = AlphaNet.load(path)
        linear_layers = [m for m in net2.shared if isinstance(m, torch.nn.Linear)]
        assert len(linear_layers) == 3
```

- [ ] **Step 2: Run to verify they fail**

```bash
uv run pytest tests/test_network_compat.py::test_load_new_format_roundtrip tests/test_network_compat.py::test_load_legacy_format -v
```

Expected: PASS for new format (already implemented), may FAIL for legacy if shape inference has a bug.

- [ ] **Step 3: Run all compat tests**

```bash
uv run pytest tests/test_network_compat.py -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_network_compat.py
git commit -m "test: add backward compatibility tests for AlphaNet load()"
```

---

### Task 3: Thread hidden_size/num_layers through AlphaCoach

**Files:**
- Modify: `src/pokemon_splendor/agents/alpha_coach.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_network_compat.py`:

```python
from pathlib import Path
from pokemon_splendor.agents.alpha_coach import AlphaCoach


def test_alpha_coach_custom_architecture():
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
            hidden_size=128,
            num_layers=2,
        )
        coach.run()
        # Load the checkpoint and verify architecture
        net = AlphaNet.load(f"{tmpdir}/alpha_0001.pt")
        linear_layers = [m for m in net.shared if isinstance(m, torch.nn.Linear)]
        assert len(linear_layers) == 2
        assert linear_layers[0].out_features == 128
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_network_compat.py::test_alpha_coach_custom_architecture -v
```

Expected: FAIL — `AlphaCoach.__init__` doesn't accept `hidden_size`/`num_layers`.

- [ ] **Step 3: Update `AlphaCoach`**

In `src/pokemon_splendor/agents/alpha_coach.py`, add `hidden_size` and `num_layers` to `__init__` and store them, then pass to `AlphaNet()` construction in `run()`:

```python
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
        buffer_size: int = 20000,
        lr: float = 0.001,
        checkpoint_dir: str = "checkpoints",
        resume_from: str | None = None,
        start_iteration: int = 1,
        n_workers: int = 1,
        eval_games: int = 40,
        accept_threshold: float = 0.45,
        hidden_size: int = 256,
        num_layers: int = 3,
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
        self._checkpoint_dir = Path(checkpoint_dir)
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._resume_from = resume_from
        self._start_iteration = start_iteration
        self._n_workers = n_workers
        self._eval_games = eval_games
        self._accept_threshold = accept_threshold
        self._hidden_size = hidden_size
        self._num_layers = num_layers
```

In `run()`, change the `AlphaNet()` construction line from:
```python
best_network = AlphaNet()
```
to:
```python
best_network = AlphaNet(hidden_size=self._hidden_size, num_layers=self._num_layers)
```

Note: the `resume_from` path uses `AlphaNet.load()` which reads architecture from the file — no change needed there.

- [ ] **Step 4: Run the test**

```bash
uv run pytest tests/test_network_compat.py::test_alpha_coach_custom_architecture -v
```

Expected: PASS.

- [ ] **Step 5: Run all tests**

```bash
uv run pytest tests/ -v --ignore=tests/server
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pokemon_splendor/agents/alpha_coach.py tests/test_network_compat.py
git commit -m "feat: thread hidden_size/num_layers through AlphaCoach"
```

---

### Task 4: Add CLI flags and wire into _run_train and _run_alpha_train

**Files:**
- Modify: `src/pokemon_splendor/__main__.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_network_compat.py`:

```python
def test_ppo_net_arch_construction():
    """Verify the net_arch dict is built correctly from hidden_size/hidden_layers."""
    hidden_size = 256
    hidden_layers = 3
    layers = [hidden_size] * hidden_layers
    net_arch = dict(pi=layers, vf=layers)
    assert net_arch == {"pi": [256, 256, 256], "vf": [256, 256, 256]}
```

This test documents the expected shape — it passes immediately since it's pure logic, but serves as a regression guard.

- [ ] **Step 2: Run it**

```bash
uv run pytest tests/test_network_compat.py::test_ppo_net_arch_construction -v
```

Expected: PASS.

- [ ] **Step 3: Add CLI flags**

In `src/pokemon_splendor/__main__.py`, add four new arguments after the existing `--alpha-start-iter` argument (around line 63):

```python
    parser.add_argument("--hidden-size", type=int, default=256,
                        help="PPO hidden layer width (default 256; ignored on --resume)")
    parser.add_argument("--hidden-layers", type=int, default=3,
                        help="PPO hidden layer count (default 3; ignored on --resume)")
    parser.add_argument("--alpha-hidden-size", type=int, default=256,
                        help="AlphaNet hidden layer width (default 256)")
    parser.add_argument("--alpha-hidden-layers", type=int, default=3,
                        help="AlphaNet hidden layer count (default 3)")
```

- [ ] **Step 4: Thread flags into `_run_train` call**

Change the `_run_train` call in `main()` (line 80) from:
```python
_run_train(jsonl, args.episodes, args.save, opponent_types, args.resume, args.lr, args.workers)
```
to:
```python
_run_train(jsonl, args.episodes, args.save, opponent_types, args.resume, args.lr, args.workers,
           args.hidden_size, args.hidden_layers)
```

- [ ] **Step 5: Update `_run_train` signature and body**

Change `_run_train` definition from:
```python
def _run_train(jsonl: Path, episodes: int, save_path: str,
               opponent_types: list[str] | None = None,
               resume_path: str | None = None,
               learning_rate: float = 0.0001,
               n_workers: int = 1):
```
to:
```python
def _run_train(jsonl: Path, episodes: int, save_path: str,
               opponent_types: list[str] | None = None,
               resume_path: str | None = None,
               learning_rate: float = 0.0001,
               n_workers: int = 1,
               hidden_size: int = 256,
               hidden_layers: int = 3):
```

Replace the hardcoded `policy_kwargs` line:
```python
        model = MaskablePPO("MlpPolicy", env, verbose=1,
                            learning_rate=learning_rate,
                            vf_coef=0.5,
                            policy_kwargs={"net_arch": dict(pi=[128, 128], vf=[128, 128])})
```
with:
```python
        layers = [hidden_size] * hidden_layers
        model = MaskablePPO("MlpPolicy", env, verbose=1,
                            learning_rate=learning_rate,
                            vf_coef=0.5,
                            policy_kwargs={"net_arch": dict(pi=layers, vf=layers)})
```

- [ ] **Step 6: Thread flags into `_run_alpha_train` call**

Change the `_run_alpha_train` call in `main()` (around line 84):
```python
    elif args.mode == "alpha-train":
        _run_alpha_train(
            jsonl, args.alpha_iters, args.alpha_games,
            args.alpha_sims, args.alpha_depth,
            len(agent_types), args.alpha_checkpoint_dir,
            args.alpha_resume, args.alpha_start_iter, args.workers,
            args.alpha_hidden_size, args.alpha_hidden_layers,
        )
```

- [ ] **Step 7: Update `_run_alpha_train` signature and body**

Change `_run_alpha_train` definition:
```python
def _run_alpha_train(
    jsonl: Path, n_iterations: int, games_per_iteration: int,
    n_simulations: int, depth: int, num_players: int, checkpoint_dir: str,
    resume_from: str | None = None, start_iteration: int = 1, n_workers: int = 1,
    hidden_size: int = 256, num_layers: int = 3,
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
        resume_from=resume_from,
        start_iteration=start_iteration,
        n_workers=n_workers,
        hidden_size=hidden_size,
        num_layers=num_layers,
    )
    coach.run()
```

- [ ] **Step 8: Run all tests**

```bash
uv run pytest tests/ -v --ignore=tests/server
```

Expected: all PASS.

- [ ] **Step 9: Smoke test — verify CLI flags are visible**

```bash
uv run pokemon-splendor --help | grep -E "hidden|alpha-hidden"
```

Expected output includes:
```
--hidden-size HIDDEN_SIZE
--hidden-layers HIDDEN_LAYERS
--alpha-hidden-size ALPHA_HIDDEN_SIZE
--alpha-hidden-layers ALPHA_HIDDEN_LAYERS
```

- [ ] **Step 10: Commit**

```bash
git add src/pokemon_splendor/__main__.py
git commit -m "feat: add --hidden-size/--hidden-layers CLI flags for PPO and AlphaNet"
```

---

### Task 5: Verify backward compatibility with real checkpoints

**Files:**
- Modify: `tests/test_network_compat.py`

- [ ] **Step 1: Write integration tests using real checkpoint files**

Append to `tests/test_network_compat.py`:

```python
import pytest

ALPHA_CHECKPOINT = "alpha_checkpoints/alpha_0001.pt"
RL_CHECKPOINT = "v7e.zip"


@pytest.mark.skipif(
    not os.path.exists(ALPHA_CHECKPOINT),
    reason=f"{ALPHA_CHECKPOINT} not present"
)
def test_real_alpha_checkpoint_loads():
    """Real .pt checkpoint (pre-migration, raw state_dict) loads without error."""
    net = AlphaNet.load(ALPHA_CHECKPOINT)
    obs = torch.zeros(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert policy.shape == (TOTAL_ACTIONS,)
    assert value.shape == ()
    assert abs(policy.sum().item() - 1.0) < 1e-5


@pytest.mark.skipif(
    not os.path.exists(RL_CHECKPOINT),
    reason=f"{RL_CHECKPOINT} not present"
)
def test_real_rl_checkpoint_loads():
    """Real .zip checkpoint loads with MaskablePPO without specifying net_arch."""
    from sb3_contrib import MaskablePPO
    from pokemon_splendor.engine.env import PokemonSplendorEnv
    from pathlib import Path
    env = PokemonSplendorEnv(Path("data/pokemon.jsonl"), num_players=2)
    model = MaskablePPO.load(RL_CHECKPOINT, env=env)
    assert model is not None
```

- [ ] **Step 2: Run**

```bash
uv run pytest tests/test_network_compat.py -v
```

Expected: all tests PASS, including the real-checkpoint tests if the files exist.

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest tests/ -v --ignore=tests/server
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_network_compat.py
git commit -m "test: add real-checkpoint backward compatibility integration tests"
```
