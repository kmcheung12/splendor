# Training Explainer Plan 1: Data Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python pipeline that converts `training_log.txt`, `.zip` PPO models, and recorded game replays into typed JSON + ONNX files under `frontend/article/data/`, ready for the Svelte article to consume.

**Architecture:** Three independent CLI scripts under `scripts/`: a log parser that emits `summary.json` and `curves.json`, a replay recorder that plays a game with an RL agent and captures per-turn observations/actions/policy outputs, and an ONNX exporter that converts a `MaskablePPO` checkpoint to a standalone `network.onnx` with intermediate hidden-layer outputs exposed. Each script has a single responsibility and is testable in isolation.

**Tech Stack:** Python 3.11+, pydantic for JSON typing, torch + sb3-contrib for model loading, onnx + onnxruntime for export, pytest for tests.

---

### Task 1: Project skeleton

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/article_export/__init__.py`
- Create: `tests/article_export/__init__.py`
- Create: `frontend/article/data/.gitkeep`

- [ ] **Step 1: Create the package directories**

```bash
mkdir -p scripts/article_export tests/article_export frontend/article/data
touch scripts/__init__.py scripts/article_export/__init__.py tests/article_export/__init__.py frontend/article/data/.gitkeep
```

- [ ] **Step 2: Commit**

```bash
git add scripts/ tests/article_export/ frontend/article/data/.gitkeep
git commit -m "feat(article): scaffold article export package directories"
```

---

### Task 2: Pydantic models for JSON output

**Files:**
- Create: `scripts/article_export/models.py`
- Test: `tests/article_export/test_models.py`

- [ ] **Step 1: Write failing test for `BatchResult`**

```python
# tests/article_export/test_models.py
from scripts.article_export.models import BatchResult, BenchmarkResult, TrainingMetrics


def test_batch_result_roundtrip():
    batch = BatchResult(
        id="v1",
        stage=1,
        opponents=["random"],
        episodes=200000,
        lr=1e-4,
        result=TrainingMetrics(
            total_timesteps=200000,
            explained_variance=-0.12,
            entropy_loss=-1.8,
            value_loss=0.04,
            clip_fraction=0.3,
        ),
        benchmarks=[
            BenchmarkResult(
                opponents=["v1", "random", "early-capture", "denial"],
                win_rates=[0.0, 0.0, 0.42, 0.58],
                games=200,
            )
        ],
        narrative="Pure random opponent.",
    )
    js = batch.model_dump_json()
    parsed = BatchResult.model_validate_json(js)
    assert parsed == batch


def test_benchmark_result_validates_win_rate_sum():
    bench = BenchmarkResult(
        opponents=["a", "b"], win_rates=[0.6, 0.4], games=100
    )
    assert bench.opponents == ["a", "b"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/article_export/test_models.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement models**

```python
# scripts/article_export/models.py
from pydantic import BaseModel


class TrainingMetrics(BaseModel):
    total_timesteps: int
    explained_variance: float
    entropy_loss: float
    value_loss: float
    clip_fraction: float


class BenchmarkResult(BaseModel):
    opponents: list[str]
    win_rates: list[float]
    games: int


class BatchResult(BaseModel):
    id: str
    stage: int
    opponents: list[str]
    episodes: int
    lr: float
    result: TrainingMetrics
    benchmarks: list[BenchmarkResult]
    narrative: str


class RunSummary(BaseModel):
    title: str
    batches: list[BatchResult]


class RunIndexEntry(BaseModel):
    id: str
    title: str
    default: bool = False


class RunIndex(BaseModel):
    runs: list[RunIndexEntry]


class CurvesPerBatch(BaseModel):
    id: str
    total_timesteps: int
    explained_variance: float
    entropy_loss: float
    value_loss: float


class Curves(BaseModel):
    batches: list[CurvesPerBatch]


class NetworkSpec(BaseModel):
    hidden_size: int
    num_layers: int
    input_size: int
    output_size: int


class TurnRecord(BaseModel):
    turn: int
    player: str
    observation: list[float]
    action: int
    action_desc: str
    value: float
    policy_top_k: list[dict]


class Replay(BaseModel):
    id: str
    agent_batch: str
    opponents: list[str]
    turns: list[TurnRecord]
    winner: str
    rounds: int
```

- [ ] **Step 4: Run test to verify pass**

Run: `uv run pytest tests/article_export/test_models.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/article_export/models.py tests/article_export/test_models.py
git commit -m "feat(article): typed pydantic models for export JSON shapes"
```

---

### Task 3: Training log parser

**Files:**
- Create: `scripts/article_export/log_parser.py`
- Create: `tests/article_export/test_log_parser.py`
- Create: `tests/article_export/fixtures/training_log_sample.txt`

- [ ] **Step 1: Create test fixture**

```text
# tests/article_export/fixtures/training_log_sample.txt

=== 2026-06-09 21:25:42 ===
Command: uv run pokemon-splendor --mode train --opponents random --episodes 200000 --save models/v1-256x3.zip --workers 4
Stage: 1 — random opponent, 200k steps
Result:
  total_timesteps:   200704
  explained_variance: -0.122
  entropy_loss:      -1.81
  value_loss:        0.0431
  clip_fraction:     0.301

Benchmark: uv run pokemon-splendor --mode benchmark --games 200 --players models/v1-256x3.zip,random,early-capture,denial --workers 4
Result:
  models/v1-256x3.zip: 0.0%  random: 0.0%  early-capture: 41.5%  denial: 58.5%

Assessment: Pure random opponent. The agent has not yet learned to buy anything.
```

- [ ] **Step 2: Write failing test**

```python
# tests/article_export/test_log_parser.py
from pathlib import Path
from scripts.article_export.log_parser import parse_training_log

FIXTURE = Path(__file__).parent / "fixtures" / "training_log_sample.txt"


def test_parse_single_batch():
    batches = parse_training_log(FIXTURE)
    assert len(batches) == 1
    b = batches[0]
    assert b.id == "v1"
    assert b.stage == 1
    assert b.opponents == ["random"]
    assert b.episodes == 200000
    assert b.result.total_timesteps == 200704
    assert b.result.explained_variance == -0.122
    assert b.result.entropy_loss == -1.81
    assert b.result.value_loss == 0.0431
    assert b.result.clip_fraction == 0.301
    assert len(b.benchmarks) == 1
    bench = b.benchmarks[0]
    assert bench.opponents == ["v1-256x3.zip", "random", "early-capture", "denial"]
    assert bench.win_rates == [0.0, 0.0, 0.415, 0.585]
    assert bench.games == 200
    assert "agent has not yet learned" in b.narrative
```

- [ ] **Step 3: Run test to verify fail**

Run: `uv run pytest tests/article_export/test_log_parser.py -v`
Expected: FAIL (module not found)

- [ ] **Step 4: Implement parser**

```python
# scripts/article_export/log_parser.py
import re
from pathlib import Path
from scripts.article_export.models import (
    BatchResult, BenchmarkResult, TrainingMetrics
)

_BATCH_RE = re.compile(r"^=== (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ===$", re.M)
_OPP_RE = re.compile(r"--opponents (\S+)")
_EPISODES_RE = re.compile(r"--episodes (\d+)")
_SAVE_RE = re.compile(r"--save (\S+)")
_STAGE_RE = re.compile(r"Stage: (\d+)")
_METRIC_RE = re.compile(r"(\w+):\s*([\-\d\.]+)")
_PLAYERS_RE = re.compile(r"--players (\S+)")
_WIN_RATE_RE = re.compile(r"([\w\-/\.]+):\s*([\d\.]+)%")


def _block_iter(text: str):
    matches = list(_BATCH_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        yield text[start:end]


def _batch_id_from_save(save_path: str) -> str:
    name = Path(save_path).stem
    return name.split("-")[0]


def parse_training_log(path: Path) -> list[BatchResult]:
    text = path.read_text()
    out: list[BatchResult] = []
    for block in _block_iter(text):
        cmd_line = next(
            (ln for ln in block.splitlines() if ln.startswith("Command:")), None
        )
        if not cmd_line:
            continue
        save_match = _SAVE_RE.search(cmd_line)
        if not save_match:
            continue
        batch_id = _batch_id_from_save(save_match.group(1))
        stage_match = _STAGE_RE.search(block)
        stage = int(stage_match.group(1)) if stage_match else 0
        opp_match = _OPP_RE.search(cmd_line)
        opponents = opp_match.group(1).split(",") if opp_match else []
        eps_match = _EPISODES_RE.search(cmd_line)
        episodes = int(eps_match.group(1)) if eps_match else 0
        lr_match = re.search(r"--lr (\S+)", cmd_line)
        lr = float(lr_match.group(1)) if lr_match else 1e-4

        result_section = _section(block, "Result:")
        metrics = _parse_metrics(result_section)
        benchmarks = _parse_benchmarks(block)
        narrative = _parse_assessment(block)

        out.append(BatchResult(
            id=batch_id,
            stage=stage,
            opponents=opponents,
            episodes=episodes,
            lr=lr,
            result=metrics,
            benchmarks=benchmarks,
            narrative=narrative,
        ))
    return out


def _section(block: str, header: str) -> str:
    lines = block.splitlines()
    out: list[str] = []
    in_section = False
    for ln in lines:
        if ln.strip() == header.strip():
            in_section = True
            continue
        if in_section:
            if ln.startswith(("Benchmark", "Assessment", "Command", "Stage")):
                break
            out.append(ln)
    return "\n".join(out)


def _parse_metrics(section: str) -> TrainingMetrics:
    found = {k: float(v) for k, v in _METRIC_RE.findall(section)}
    return TrainingMetrics(
        total_timesteps=int(found.get("total_timesteps", 0)),
        explained_variance=found.get("explained_variance", 0.0),
        entropy_loss=found.get("entropy_loss", 0.0),
        value_loss=found.get("value_loss", 0.0),
        clip_fraction=found.get("clip_fraction", 0.0),
    )


def _parse_benchmarks(block: str) -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []
    lines = block.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("Benchmark:"):
            players_match = _PLAYERS_RE.search(ln)
            games_match = re.search(r"--games (\d+)", ln)
            if not (players_match and games_match):
                continue
            opp_strs = players_match.group(1).split(",")
            opponents = [Path(s).name for s in opp_strs]
            games = int(games_match.group(1))
            result_line = next(
                (lines[j] for j in range(i + 1, min(i + 5, len(lines)))
                 if "%" in lines[j]),
                "",
            )
            win_rates: list[float] = []
            for _name, pct in _WIN_RATE_RE.findall(result_line):
                win_rates.append(float(pct) / 100.0)
            if len(win_rates) == len(opponents):
                results.append(BenchmarkResult(
                    opponents=opponents,
                    win_rates=win_rates,
                    games=games,
                ))
    return results


def _parse_assessment(block: str) -> str:
    for ln in block.splitlines():
        if ln.startswith("Assessment:"):
            return ln[len("Assessment:"):].strip()
    return ""
```

- [ ] **Step 5: Run test to verify pass**

Run: `uv run pytest tests/article_export/test_log_parser.py -v`
Expected: 1 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/article_export/log_parser.py tests/article_export/test_log_parser.py tests/article_export/fixtures/
git commit -m "feat(article): parser for training_log.txt → BatchResult list"
```

---

### Task 4: Multi-batch fixture + end-to-end log parsing

**Files:**
- Modify: `tests/article_export/fixtures/training_log_sample.txt` (append 2nd batch)
- Modify: `tests/article_export/test_log_parser.py`

- [ ] **Step 1: Append second batch to fixture**

```text
# Append to tests/article_export/fixtures/training_log_sample.txt

=== 2026-06-09 22:17:25 ===
Command: uv run pokemon-splendor --mode train --opponents denial,high-point --resume models/v2d-256x3.zip --episodes 500000 --lr 0.0001 --save models/v3-256x3.zip --workers 4
Stage: 3 — denial+high-point, 500k steps
Result:
  total_timesteps: 507904  explained_variance: 0.0412  entropy_loss: -1.0  value_loss: 0.0272

Benchmark: uv run pokemon-splendor --mode benchmark --games 200 --players models/v3-256x3.zip,random,early-capture,denial --workers 4
  v3-256x3: 12.5%  random: 0%  early-capture: 36.5%  denial: 51%

Benchmark: uv run pokemon-splendor --mode benchmark --games 200 --players models/v3-256x3.zip,high-point --workers 4
  v3-256x3: 56%  high-point: 44%
Assessment: Crossed 55% threshold vs high-point. Advancing to stage 4.
```

- [ ] **Step 2: Add multi-batch test**

```python
# Append to tests/article_export/test_log_parser.py
def test_parse_multiple_batches():
    batches = parse_training_log(FIXTURE)
    assert [b.id for b in batches] == ["v1", "v3"]
    assert batches[1].stage == 3
    assert batches[1].opponents == ["denial", "high-point"]
    assert batches[1].lr == 0.0001
    assert len(batches[1].benchmarks) == 2
    assert batches[1].benchmarks[1].opponents == ["v3-256x3.zip", "high-point"]
    assert batches[1].benchmarks[1].win_rates == [0.56, 0.44]
```

- [ ] **Step 3: Run test to verify pass**

Run: `uv run pytest tests/article_export/test_log_parser.py -v`
Expected: 2 passed

- [ ] **Step 4: Commit**

```bash
git add tests/article_export/
git commit -m "test(article): parser handles multi-batch training log"
```

---

### Task 5: Summary and curves JSON writer

**Files:**
- Create: `scripts/article_export/writer.py`
- Create: `tests/article_export/test_writer.py`

- [ ] **Step 1: Write failing test**

```python
# tests/article_export/test_writer.py
import json
import tempfile
from pathlib import Path
from scripts.article_export.models import (
    BatchResult, BenchmarkResult, TrainingMetrics
)
from scripts.article_export.writer import write_run_outputs


def _make_batch(id_: str, ev: float) -> BatchResult:
    return BatchResult(
        id=id_, stage=1, opponents=["random"],
        episodes=200000, lr=1e-4,
        result=TrainingMetrics(
            total_timesteps=200000, explained_variance=ev,
            entropy_loss=-1.5, value_loss=0.05, clip_fraction=0.3,
        ),
        benchmarks=[BenchmarkResult(
            opponents=["self", "random"],
            win_rates=[0.6, 0.4], games=200,
        )],
        narrative="example",
    )


def test_write_run_outputs():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        batches = [_make_batch("v1", -0.1), _make_batch("v2", 0.2)]
        write_run_outputs(
            out, run_id="r", title="My run",
            batches=batches, set_default=True,
        )
        summary = json.loads((out / "summary.json").read_text())
        assert summary["title"] == "My run"
        assert [b["id"] for b in summary["batches"]] == ["v1", "v2"]
        curves = json.loads((out / "curves.json").read_text())
        assert curves["batches"][1]["explained_variance"] == 0.2
```

- [ ] **Step 2: Run test to verify fail**

Run: `uv run pytest tests/article_export/test_writer.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement writer**

```python
# scripts/article_export/writer.py
from pathlib import Path
from scripts.article_export.models import (
    BatchResult, Curves, CurvesPerBatch, RunSummary,
)


def write_run_outputs(
    out_dir: Path,
    run_id: str,
    title: str,
    batches: list[BatchResult],
    set_default: bool,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = RunSummary(title=title, batches=batches)
    (out_dir / "summary.json").write_text(summary.model_dump_json(indent=2))

    curves = Curves(batches=[
        CurvesPerBatch(
            id=b.id,
            total_timesteps=b.result.total_timesteps,
            explained_variance=b.result.explained_variance,
            entropy_loss=b.result.entropy_loss,
            value_loss=b.result.value_loss,
        )
        for b in batches
    ])
    (out_dir / "curves.json").write_text(curves.model_dump_json(indent=2))
```

- [ ] **Step 4: Run test to verify pass**

Run: `uv run pytest tests/article_export/test_writer.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/article_export/writer.py tests/article_export/test_writer.py
git commit -m "feat(article): write summary.json and curves.json"
```

---

### Task 6: Index JSON writer

**Files:**
- Modify: `scripts/article_export/writer.py`
- Modify: `tests/article_export/test_writer.py`

- [ ] **Step 1: Add test**

```python
# Append to tests/article_export/test_writer.py
from scripts.article_export.writer import write_run_index


def test_write_run_index_merges_existing():
    with tempfile.TemporaryDirectory() as tmp:
        runs_dir = Path(tmp)
        write_run_index(runs_dir, run_id="r1", title="One", set_default=True)
        write_run_index(runs_dir, run_id="r2", title="Two", set_default=False)
        index = json.loads((runs_dir / "index.json").read_text())
        ids = [r["id"] for r in index["runs"]]
        assert ids == ["r1", "r2"]
        assert index["runs"][0]["default"] is True
        assert index["runs"][1]["default"] is False


def test_write_run_index_set_default_unsets_others():
    with tempfile.TemporaryDirectory() as tmp:
        runs_dir = Path(tmp)
        write_run_index(runs_dir, run_id="r1", title="One", set_default=True)
        write_run_index(runs_dir, run_id="r2", title="Two", set_default=True)
        index = json.loads((runs_dir / "index.json").read_text())
        assert index["runs"][0]["default"] is False
        assert index["runs"][1]["default"] is True
```

- [ ] **Step 2: Run test to verify fail**

Run: `uv run pytest tests/article_export/test_writer.py -v`
Expected: FAIL (write_run_index not found)

- [ ] **Step 3: Implement index writer**

```python
# Append to scripts/article_export/writer.py
import json
from scripts.article_export.models import RunIndex, RunIndexEntry


def write_run_index(
    runs_dir: Path, run_id: str, title: str, set_default: bool
) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    index_path = runs_dir / "index.json"
    if index_path.exists():
        index = RunIndex.model_validate_json(index_path.read_text())
    else:
        index = RunIndex(runs=[])
    entries = [e for e in index.runs if e.id != run_id]
    if set_default:
        for e in entries:
            e.default = False
    entries.append(RunIndexEntry(id=run_id, title=title, default=set_default))
    index = RunIndex(runs=entries)
    index_path.write_text(index.model_dump_json(indent=2))
```

- [ ] **Step 4: Run test to verify pass**

Run: `uv run pytest tests/article_export/test_writer.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/article_export/writer.py tests/article_export/test_writer.py
git commit -m "feat(article): idempotent run index writer"
```

---

### Task 7: Network spec extractor

**Files:**
- Create: `scripts/article_export/network_spec.py`
- Create: `tests/article_export/test_network_spec.py`

- [ ] **Step 1: Write failing test**

```python
# tests/article_export/test_network_spec.py
import os
import pytest
import tempfile
from pathlib import Path
from scripts.article_export.network_spec import extract_network_spec


@pytest.mark.skipif(
    not os.path.exists("models/v6-256x3.zip"),
    reason="needs real PPO checkpoint",
)
def test_extract_network_spec_from_real_model():
    spec = extract_network_spec(Path("models/v6-256x3.zip"))
    assert spec.hidden_size == 256
    assert spec.num_layers == 3
    assert spec.output_size == 50
    assert spec.input_size > 0


def test_extract_network_spec_writes_json():
    import json
    from scripts.article_export.network_spec import write_network_spec
    if not os.path.exists("models/v6-256x3.zip"):
        pytest.skip("needs real PPO checkpoint")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "network.json"
        write_network_spec(Path("models/v6-256x3.zip"), out)
        data = json.loads(out.read_text())
        assert data["hidden_size"] == 256
        assert data["num_layers"] == 3
```

- [ ] **Step 2: Run test to verify fail**

Run: `uv run pytest tests/article_export/test_network_spec.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement extractor**

```python
# scripts/article_export/network_spec.py
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.agents.rl import SingleAgentEnv
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from scripts.article_export.models import NetworkSpec


def _mask_fn(env):
    return env.action_masks()


def _load_model(model_path: Path) -> MaskablePPO:
    env = ActionMasker(
        SingleAgentEnv(Path("data/pokemon.jsonl"), num_players=2),
        _mask_fn,
    )
    return MaskablePPO.load(model_path, env=env)


def extract_network_spec(model_path: Path) -> NetworkSpec:
    model = _load_model(model_path)
    policy = model.policy
    mlp = policy.mlp_extractor.policy_net
    linears = [m for m in mlp.modules() if m.__class__.__name__ == "Linear"]
    hidden_size = linears[0].out_features
    num_layers = len(linears)
    input_size = linears[0].in_features
    output_size = policy.action_net.out_features
    return NetworkSpec(
        hidden_size=hidden_size,
        num_layers=num_layers,
        input_size=input_size,
        output_size=output_size,
    )


def write_network_spec(model_path: Path, out_path: Path) -> None:
    spec = extract_network_spec(model_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(spec.model_dump_json(indent=2))
```

- [ ] **Step 4: Run test to verify pass**

Run: `uv run pytest tests/article_export/test_network_spec.py -v`
Expected: 2 passed (or skipped if checkpoint missing)

- [ ] **Step 5: Commit**

```bash
git add scripts/article_export/network_spec.py tests/article_export/test_network_spec.py
git commit -m "feat(article): extract NetworkSpec from PPO checkpoint"
```

---

### Task 8: Replay recorder

**Files:**
- Create: `scripts/article_export/replay_recorder.py`
- Create: `tests/article_export/test_replay_recorder.py`

- [ ] **Step 1: Write failing test**

```python
# tests/article_export/test_replay_recorder.py
import os
import json
import tempfile
import pytest
from pathlib import Path
from scripts.article_export.replay_recorder import record_replay


@pytest.mark.skipif(
    not os.path.exists("models/v6-256x3.zip"),
    reason="needs real PPO checkpoint",
)
def test_record_replay_writes_valid_json():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "replay.json"
        record_replay(
            agent_model=Path("models/v6-256x3.zip"),
            agent_batch_id="v6",
            opponents=["random"],
            data_path=Path("data/pokemon.jsonl"),
            out_path=out,
            replay_id="test-game",
            seed=42,
        )
        data = json.loads(out.read_text())
        assert data["id"] == "test-game"
        assert data["agent_batch"] == "v6"
        assert data["opponents"] == ["random"]
        assert len(data["turns"]) > 0
        first_turn = data["turns"][0]
        assert "observation" in first_turn
        assert "action" in first_turn
        assert "policy_top_k" in first_turn
        assert len(first_turn["policy_top_k"]) <= 5
        assert data["winner"] in (data["agent_batch"], "random")
```

- [ ] **Step 2: Run test to verify fail**

Run: `uv run pytest tests/article_export/test_replay_recorder.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement recorder**

```python
# scripts/article_export/replay_recorder.py
import numpy as np
import torch
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.agents.base import describe_action
from pokemon_splendor.agents.rl import RLAgent
from scripts.article_export.models import Replay, TurnRecord

MAX_STEPS = 1000


def _make_opponent(t: str, env, name: str):
    if t == "random":
        return None
    if t == "early-capture":
        from pokemon_splendor.agents.early_capture import EarlyCaptureAgent
        return EarlyCaptureAgent(env, name)
    if t == "denial":
        from pokemon_splendor.agents.denial import DenialAgent
        return DenialAgent(env, name)
    if t == "high-point":
        from pokemon_splendor.agents.high_point import HighPointCaptureAgent
        return HighPointCaptureAgent(env, name)
    if t.endswith(".zip"):
        return RLAgent(t)
    raise ValueError(f"unknown opponent: {t}")


def _policy_top_k(model, obs: np.ndarray, mask: np.ndarray, k: int = 5):
    obs_t = torch.as_tensor(obs).float().unsqueeze(0)
    mask_t = torch.as_tensor(mask).bool().unsqueeze(0)
    with torch.no_grad():
        dist = model.policy.get_distribution(obs_t, action_masks=mask_t)
        probs = dist.distribution.probs.squeeze(0).cpu().numpy()
        value = model.policy.predict_values(obs_t).item()
    top_idx = np.argsort(-probs)[:k]
    return [{"action": int(i), "prob": float(probs[i])} for i in top_idx], value


def record_replay(
    agent_model: Path,
    agent_batch_id: str,
    opponents: list[str],
    data_path: Path,
    out_path: Path,
    replay_id: str,
    seed: int,
) -> None:
    num_players = 1 + len(opponents)
    env = PokemonSplendorEnv(data_path, num_players=num_players)
    env.reset(seed=seed)
    agent = RLAgent(str(agent_model))
    agent_name = env.possible_agents[0]
    opp_map = {
        env.possible_agents[i + 1]: _make_opponent(opponents[i], env, env.possible_agents[i + 1])
        for i in range(len(opponents))
    }

    turns: list[TurnRecord] = []
    for step_idx in range(MAX_STEPS):
        if not env.agents:
            break
        name = env.agent_selection
        obs, _, term, trunc, _ = env.last()
        if term or trunc:
            break
        mask = env.action_mask(name)
        if name == agent_name:
            top_k, value = _policy_top_k(agent.model, obs, mask)
            action = int(agent.act(obs, mask))
            player = next(p for p in env.game.players if p.name == name)
            desc = describe_action(action, env.game, player)
            turns.append(TurnRecord(
                turn=step_idx,
                player=name,
                observation=obs.astype(float).tolist(),
                action=action,
                action_desc=desc,
                value=value,
                policy_top_k=top_k,
            ))
        else:
            opp = opp_map.get(name)
            if opp is None:
                action = int(np.random.choice(np.where(mask)[0]))
            else:
                action = int(opp.act(obs, mask))
        env.step(action)

    winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
    winner_label = agent_batch_id if winner.name == agent_name else next(
        (opponents[i] for i, n in enumerate(env.possible_agents[1:])
         if n == winner.name),
        "unknown",
    )
    rounds = env.game.round

    replay = Replay(
        id=replay_id,
        agent_batch=agent_batch_id,
        opponents=opponents,
        turns=turns,
        winner=winner_label,
        rounds=rounds,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(replay.model_dump_json(indent=2))
```

- [ ] **Step 4: Run test to verify pass**

Run: `uv run pytest tests/article_export/test_replay_recorder.py -v`
Expected: 1 passed (or skipped if checkpoint missing)

- [ ] **Step 5: Commit**

```bash
git add scripts/article_export/replay_recorder.py tests/article_export/test_replay_recorder.py
git commit -m "feat(article): record game replay with per-turn obs, action, policy_top_k"
```

---

### Task 9: ONNX exporter

**Files:**
- Create: `scripts/article_export/onnx_export.py`
- Create: `tests/article_export/test_onnx_export.py`

- [ ] **Step 1: Write failing test**

```python
# tests/article_export/test_onnx_export.py
import os
import tempfile
import numpy as np
import pytest
from pathlib import Path
from scripts.article_export.onnx_export import export_policy_to_onnx


@pytest.mark.skipif(
    not os.path.exists("models/v6-256x3.zip"),
    reason="needs real PPO checkpoint",
)
def test_onnx_export_roundtrip():
    import onnxruntime as ort
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "network.onnx"
        export_policy_to_onnx(Path("models/v6-256x3.zip"), out)
        assert out.exists()
        sess = ort.InferenceSession(str(out))
        input_meta = sess.get_inputs()[0]
        obs = np.zeros(input_meta.shape, dtype=np.float32)
        outputs = sess.run(None, {input_meta.name: obs})
        # Expect: policy_logits, value, then hidden activations
        assert len(outputs) >= 2
```

- [ ] **Step 2: Run test to verify fail**

Run: `uv run pytest tests/article_export/test_onnx_export.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement exporter**

```python
# scripts/article_export/onnx_export.py
import torch
import torch.nn as nn
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.agents.rl import SingleAgentEnv
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker


def _mask_fn(env):
    return env.action_masks()


class PolicyWrapper(nn.Module):
    """Wraps a MaskablePPO policy to emit policy logits, value, and per-layer activations."""

    def __init__(self, policy):
        super().__init__()
        self.shared = policy.mlp_extractor.policy_net
        self.policy_head = policy.action_net
        self.value_extractor = policy.mlp_extractor.value_net
        self.value_head = policy.value_net

    def forward(self, obs):
        x = obs
        activations = []
        for layer in self.shared:
            x = layer(x)
            if isinstance(layer, nn.Linear):
                activations.append(x.clone())
        policy_logits = self.policy_head(x)
        vx = obs
        for layer in self.value_extractor:
            vx = layer(vx)
        value = self.value_head(vx).squeeze(-1)
        return (policy_logits, value, *activations)


def export_policy_to_onnx(model_path: Path, out_path: Path) -> None:
    env = ActionMasker(
        SingleAgentEnv(Path("data/pokemon.jsonl"), num_players=2),
        _mask_fn,
    )
    model = MaskablePPO.load(model_path, env=env)
    wrapper = PolicyWrapper(model.policy).eval()

    obs_size = model.policy.observation_space.shape[0]
    dummy = torch.zeros(1, obs_size, dtype=torch.float32)

    num_layers = sum(
        1 for m in model.policy.mlp_extractor.policy_net.modules()
        if isinstance(m, nn.Linear)
    )
    activation_names = [f"hidden_{i}" for i in range(num_layers)]
    output_names = ["policy_logits", "value", *activation_names]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        wrapper,
        dummy,
        str(out_path),
        input_names=["observation"],
        output_names=output_names,
        dynamic_axes={"observation": {0: "batch"}},
        opset_version=17,
    )
```

- [ ] **Step 4: Run test to verify pass**

Run: `uv run pytest tests/article_export/test_onnx_export.py -v`
Expected: 1 passed (or skipped if checkpoint missing)

- [ ] **Step 5: Commit**

```bash
git add scripts/article_export/onnx_export.py tests/article_export/test_onnx_export.py
git commit -m "feat(article): export PPO policy to ONNX with hidden activations as outputs"
```

---

### Task 10: Narrative augmenter

**Files:**
- Create: `scripts/article_export/narrative.py`
- Create: `tests/article_export/test_narrative.py`

The training log narrative ("Assessment:" line) is terse and internal. The article needs human-friendly per-batch narratives. We keep them in a separate YAML file so the writer can iterate without touching parsing logic.

- [ ] **Step 1: Create the narrative YAML**

```yaml
# scripts/article_export/narratives/v1-to-v7.yaml
v1: |
  The first version played against a completely random opponent.
  It had no idea how Splendor worked — its only signal was "did I win?".
  After 200,000 games it still hadn't learned to buy anything.
v3: |
  Mixing denial and high-point as opponents broke a plateau the agent
  had been stuck on. Two adversarial strategies forced the agent to
  develop a more general policy.
v6: |
  Training against three opponents (denial + two earlier self-play
  versions) restored the agent's generalisation after v5 had
  over-specialised. v6 was the first version to beat denial in
  four-player play.
```

- [ ] **Step 2: Write failing test**

```python
# tests/article_export/test_narrative.py
from pathlib import Path
from scripts.article_export.narrative import load_narratives, apply_narratives
from scripts.article_export.models import (
    BatchResult, TrainingMetrics,
)


def test_load_narratives():
    narrs = load_narratives(
        Path("scripts/article_export/narratives/v1-to-v7.yaml")
    )
    assert "v1" in narrs
    assert "buy anything" in narrs["v1"]


def test_apply_narratives_overrides_only_listed():
    batches = [
        BatchResult(
            id="v1", stage=1, opponents=[], episodes=0, lr=0.0,
            result=TrainingMetrics(
                total_timesteps=0, explained_variance=0, entropy_loss=0,
                value_loss=0, clip_fraction=0,
            ),
            benchmarks=[], narrative="original v1",
        ),
        BatchResult(
            id="v2", stage=1, opponents=[], episodes=0, lr=0.0,
            result=TrainingMetrics(
                total_timesteps=0, explained_variance=0, entropy_loss=0,
                value_loss=0, clip_fraction=0,
            ),
            benchmarks=[], narrative="original v2",
        ),
    ]
    apply_narratives(batches, {"v1": "new v1"})
    assert batches[0].narrative == "new v1"
    assert batches[1].narrative == "original v2"
```

- [ ] **Step 3: Run test to verify fail**

Run: `uv run pytest tests/article_export/test_narrative.py -v`
Expected: FAIL (module not found)

- [ ] **Step 4: Implement**

```python
# scripts/article_export/narrative.py
from pathlib import Path
from scripts.article_export.models import BatchResult


def load_narratives(yaml_path: Path) -> dict[str, str]:
    import yaml
    data = yaml.safe_load(yaml_path.read_text())
    return {k: v.strip() for k, v in (data or {}).items()}


def apply_narratives(batches: list[BatchResult], narrs: dict[str, str]) -> None:
    for b in batches:
        if b.id in narrs:
            b.narrative = narrs[b.id]
```

- [ ] **Step 5: Run test to verify pass**

Run: `uv run pytest tests/article_export/test_narrative.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/article_export/narrative.py scripts/article_export/narratives/ tests/article_export/test_narrative.py
git commit -m "feat(article): narrative YAML override layer for batch descriptions"
```

---

### Task 11: Top-level CLI: `export_article_data.py`

**Files:**
- Create: `scripts/export_article_data.py`

- [ ] **Step 1: Write the CLI**

```python
#!/usr/bin/env python
# scripts/export_article_data.py
import argparse
from pathlib import Path
from scripts.article_export.log_parser import parse_training_log
from scripts.article_export.narrative import apply_narratives, load_narratives
from scripts.article_export.network_spec import write_network_spec
from scripts.article_export.writer import write_run_index, write_run_outputs


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--models-dir", type=Path, default=Path("models"))
    p.add_argument("--network-from", default=None,
                   help="Batch id to extract network.json from (default: last batch)")
    p.add_argument("--narratives", type=Path, default=None)
    p.add_argument("--out", type=Path, required=True,
                   help="frontend/article/data/runs/")
    p.add_argument("--default", action="store_true",
                   help="Mark this run as the default in index.json")
    args = p.parse_args()

    batches = parse_training_log(args.log)
    if args.narratives:
        apply_narratives(batches, load_narratives(args.narratives))

    run_out = args.out / args.run_id
    write_run_outputs(
        run_out, run_id=args.run_id, title=args.title,
        batches=batches, set_default=args.default,
    )
    write_run_index(
        args.out, run_id=args.run_id,
        title=args.title, set_default=args.default,
    )

    network_batch = args.network_from or batches[-1].id
    model_path = args.models_dir / f"{network_batch}-256x3.zip"
    if model_path.exists():
        write_network_spec(model_path, run_out / "network.json")

    print(f"Wrote {run_out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it runs end-to-end**

```bash
uv run python scripts/export_article_data.py \
  --run-id v1-to-v7 \
  --title "First curriculum" \
  --log training_log.txt \
  --narratives scripts/article_export/narratives/v1-to-v7.yaml \
  --out frontend/article/data/runs/ \
  --default
```

Expected output (on stderr/stdout): `Wrote frontend/article/data/runs/v1-to-v7`
Expected files:
- `frontend/article/data/runs/v1-to-v7/summary.json`
- `frontend/article/data/runs/v1-to-v7/curves.json`
- `frontend/article/data/runs/v1-to-v7/network.json`
- `frontend/article/data/runs/index.json`

- [ ] **Step 3: Verify JSON validity**

```bash
uv run python -c "import json; json.load(open('frontend/article/data/runs/v1-to-v7/summary.json'))"
uv run python -c "import json; json.load(open('frontend/article/data/runs/index.json'))"
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add scripts/export_article_data.py frontend/article/data/runs/
git commit -m "feat(article): top-level export_article_data.py CLI"
```

---

### Task 12: Top-level CLI: `record_replay.py` and `export_onnx.py`

**Files:**
- Create: `scripts/record_replay.py`
- Create: `scripts/export_onnx.py`

- [ ] **Step 1: Write `record_replay.py`**

```python
#!/usr/bin/env python
# scripts/record_replay.py
import argparse
from pathlib import Path
from scripts.article_export.replay_recorder import record_replay


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--batch-id", required=True)
    p.add_argument("--opponents", required=True, help="comma-separated")
    p.add_argument("--data", type=Path, default=Path("data/pokemon.jsonl"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--id", required=True, help="Replay identifier")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    opponents = [o.strip() for o in args.opponents.split(",")]
    record_replay(
        agent_model=args.model,
        agent_batch_id=args.batch_id,
        opponents=opponents,
        data_path=args.data,
        out_path=args.out,
        replay_id=args.id,
        seed=args.seed,
    )
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `export_onnx.py`**

```python
#!/usr/bin/env python
# scripts/export_onnx.py
import argparse
from pathlib import Path
from scripts.article_export.onnx_export import export_policy_to_onnx


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    export_policy_to_onnx(args.model, args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify end-to-end**

```bash
uv run python scripts/record_replay.py \
  --model models/v6-256x3.zip --batch-id v6 \
  --opponents denial,early-capture,random \
  --out frontend/article/data/runs/v1-to-v7/replays/v6-vs-denial-seed42.json \
  --id v6-vs-denial-seed42 --seed 42

uv run python scripts/export_onnx.py \
  --model models/v6-256x3.zip \
  --out frontend/article/data/runs/v1-to-v7/network.onnx
```

Expected: both files written, no errors.

- [ ] **Step 4: Commit**

```bash
git add scripts/record_replay.py scripts/export_onnx.py frontend/article/data/runs/v1-to-v7/
git commit -m "feat(article): record_replay.py and export_onnx.py CLIs"
```

---

### Task 13: Add `.gitignore` entries and pyproject deps

**Files:**
- Modify: `.gitignore`
- Modify: `pyproject.toml`

- [ ] **Step 1: Ignore generated ONNX (large binary)**

Append to `.gitignore`:
```
frontend/article/data/runs/**/network.onnx
```

- [ ] **Step 2: Add pyyaml and onnx to pyproject.toml**

In `pyproject.toml` under `[project] dependencies`, add: `pyyaml>=6.0`, `onnx>=1.16`, `onnxruntime>=1.17`.

- [ ] **Step 3: Lock and verify**

```bash
uv sync
uv run pytest tests/article_export/ -v
```

Expected: all tests pass, no missing imports.

- [ ] **Step 4: Commit**

```bash
git add .gitignore pyproject.toml uv.lock
git commit -m "chore(article): add export dependencies and gitignore onnx artifacts"
```

---

## Done

After this plan:
- `frontend/article/data/runs/<run-id>/` contains `summary.json`, `curves.json`, `network.json`, `network.onnx`, and `replays/*.json` for one run.
- `frontend/article/data/runs/index.json` lists available runs.
- Three CLI scripts (`export_article_data.py`, `record_replay.py`, `export_onnx.py`) regenerate the data idempotently.
- Plan 2 (article shell) can begin.
