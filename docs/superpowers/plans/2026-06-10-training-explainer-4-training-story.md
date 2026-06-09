# Training Explainer Plan 4: Training Story

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the training curve chart, the benchmark bars, the GameReplayPlayer that wraps the existing Board.svelte for replay rendering, the scrub-to-batch coupling, and ship Section 5 (Training Story) — the longest section, where the agent visibly improves as the reader scrolls.

**Architecture:** Two presentational components (`TrainingCurve.svelte`, `BenchmarkBars.svelte`) consume `Curves` and `BatchResult` from the typed loaders. `GameReplayPlayer.svelte` takes a `Replay` and a `turnIndex` and renders the corresponding game state by piping fixture observations into a non-interactive `Board.svelte`. `useReplayScrubber.ts` maps scroll progress to `(batchIndex, turnIndex)` pairs. `TrainingStory.svelte` orchestrates: chapters scroll past on the left, the curve and replay sit sticky on the right, both driven by a single scroll progress value.

**Tech Stack:** Svelte 4, TypeScript, SVG for charts (no D3), Svelte's `tweened` store for chart animation.

---

### Task 1: Reusable Splendor board snapshot type

**Files:**
- Create: `frontend/article/replay/snapshot.ts`
- Create: `frontend/article/replay/__tests__/snapshot.test.ts`

Game replays from Plan 1 record per-turn observations (flat float vectors). We need to convert them to renderable `BoardSnapshot` objects matching the existing `Board.svelte` prop shape.

- [ ] **Step 1: Check the existing Board.svelte prop shape**

Inspect `frontend/src/components/Board.svelte` and `frontend/src/lib/gameStore.ts` for the existing game-state TypeScript types. Note their property names; we'll mirror them in `BoardSnapshot` to allow direct passthrough.

Hand-document the shape in code:

```ts
// frontend/article/replay/snapshot.ts
import type { TurnRecord } from '../lib/types';

export interface CardSnapshot {
  name: string;
  tier: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
  point: number;
  cost: Record<string, number>;
  bonus: string | null;
}

export interface PlayerSnapshot {
  name: string;
  points: number;
  tokens: Record<string, number>;
  cards: CardSnapshot[];
  reserved_cards: CardSnapshot[];
}

export interface BoardSnapshot {
  common_revealed: (CardSnapshot | null)[];
  uncommon_revealed: (CardSnapshot | null)[];
  rare_revealed: (CardSnapshot | null)[];
  epic_revealed: (CardSnapshot | null)[];
  legendary_revealed: (CardSnapshot | null)[];
  tokens: Record<string, number>;
  players: PlayerSnapshot[];
  active_player: string;
}
```

- [ ] **Step 2: Add a replay-to-snapshot decoder placeholder**

```ts
// Append to frontend/article/replay/snapshot.ts
export interface ReplaySnapshots {
  initial: BoardSnapshot;
  turns: { turn: number; snapshot: BoardSnapshot; description: string }[];
}

export function loadReplaySnapshots(replayId: string): Promise<ReplaySnapshots> {
  return fetch(`/runs/v1-to-v7/snapshots/${replayId}.json`)
    .then((r) => {
      if (!r.ok) throw new Error(`snapshot ${r.status}`);
      return r.json();
    });
}
```

- [ ] **Step 3: Write failing test**

```ts
// frontend/article/replay/__tests__/snapshot.test.ts
import { describe, it, expect, vi } from 'vitest';
import { loadReplaySnapshots } from '../snapshot';

describe('loadReplaySnapshots', () => {
  it('fetches a snapshot file', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        initial: { tokens: {}, common_revealed: [], uncommon_revealed: [],
                   rare_revealed: [], epic_revealed: [], legendary_revealed: [],
                   players: [], active_player: 'p0' },
        turns: [],
      }),
    }) as unknown as typeof fetch;
    const snaps = await loadReplaySnapshots('test');
    expect(snaps.initial.active_player).toBe('p0');
  });

  it('throws on missing replay file', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 });
    await expect(loadReplaySnapshots('missing')).rejects.toThrow('404');
  });
});
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: 2 passed (snapshot)

- [ ] **Step 5: Commit**

```bash
git add frontend/article/replay/
git commit -m "feat(article): BoardSnapshot types and loadReplaySnapshots"
```

---

### Task 2: Extend the Plan 1 replay recorder to emit board snapshots

**Files:**
- Modify: `scripts/article_export/replay_recorder.py`
- Create: `tests/article_export/test_replay_recorder_snapshots.py`

The article needs board snapshots, not raw observations. Extend the recorder.

- [ ] **Step 1: Write failing test**

```python
# tests/article_export/test_replay_recorder_snapshots.py
import os
import json
import tempfile
import pytest
from pathlib import Path
from scripts.article_export.replay_recorder import record_replay_with_snapshots


@pytest.mark.skipif(
    not os.path.exists("models/v6-256x3.zip"),
    reason="needs real PPO checkpoint",
)
def test_record_replay_emits_snapshots():
    with tempfile.TemporaryDirectory() as tmp:
        snap_out = Path(tmp) / "snapshots.json"
        record_replay_with_snapshots(
            agent_model=Path("models/v6-256x3.zip"),
            agent_batch_id="v6",
            opponents=["random"],
            data_path=Path("data/pokemon.jsonl"),
            replay_out=Path(tmp) / "replay.json",
            snapshot_out=snap_out,
            replay_id="test-game",
            seed=42,
        )
        data = json.loads(snap_out.read_text())
        assert "initial" in data
        assert "turns" in data
        assert len(data["turns"]) > 0
        first = data["turns"][0]
        assert "snapshot" in first
        assert "active_player" in first["snapshot"]
```

- [ ] **Step 2: Run test to verify fail**

Run: `uv run pytest tests/article_export/test_replay_recorder_snapshots.py -v`
Expected: FAIL (function not found)

- [ ] **Step 3: Implement snapshot serialiser**

Append to `scripts/article_export/replay_recorder.py`:

```python
def _serialize_card(card) -> dict | None:
    if card is None:
        return None
    return {
        "name": card.name,
        "tier": card.tier.value,
        "point": card.point,
        "cost": {k.name if hasattr(k, "name") else str(k): v
                 for k, v in card.cost.items()},
        "bonus": card.bonus.name if card.bonus else None,
    }


def _serialize_player(player) -> dict:
    from collections import Counter
    return {
        "name": player.name,
        "points": player.points,
        "tokens": dict(Counter(t.name.value for t in player.tokens)),
        "cards": [_serialize_card(c) for c in player.cards],
        "reserved_cards": [_serialize_card(c) for c in player.reserved_cards],
    }


def _serialize_board(env) -> dict:
    from collections import Counter
    game = env.game
    return {
        "common_revealed": [_serialize_card(c) for c in game.board.common_revealed],
        "uncommon_revealed": [_serialize_card(c) for c in game.board.uncommon_revealed],
        "rare_revealed": [_serialize_card(c) for c in game.board.rare_revealed],
        "epic_revealed": [_serialize_card(c) for c in game.board.epic_revealed],
        "legendary_revealed": [_serialize_card(c) for c in game.board.legendary_revealed],
        "tokens": dict(Counter(t.name.value for t in game.board.tokens)),
        "players": [_serialize_player(p) for p in game.players],
        "active_player": env.agent_selection if env.agents else "",
    }


def record_replay_with_snapshots(
    agent_model: Path,
    agent_batch_id: str,
    opponents: list[str],
    data_path: Path,
    replay_out: Path,
    snapshot_out: Path,
    replay_id: str,
    seed: int,
) -> None:
    """Run a game and emit both the per-turn replay JSON and the snapshots JSON."""
    num_players = 1 + len(opponents)
    env = PokemonSplendorEnv(data_path, num_players=num_players)
    env.reset(seed=seed)
    agent = RLAgent(str(agent_model))
    agent_name = env.possible_agents[0]
    opp_map = {
        env.possible_agents[i + 1]: _make_opponent(opponents[i], env, env.possible_agents[i + 1])
        for i in range(len(opponents))
    }

    initial_snap = _serialize_board(env)
    turn_records: list[TurnRecord] = []
    snapshot_turns: list[dict] = []

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
            turn_records.append(TurnRecord(
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
                desc = "random move"
            else:
                action = int(opp.act(opp.act.__self__._env_obs(name) if hasattr(opp.act, '__self__') else obs, mask)) if False else int(opp.act(obs, mask))
                player = next(p for p in env.game.players if p.name == name)
                desc = describe_action(action, env.game, player)

        env.step(action)
        snapshot_turns.append({
            "turn": step_idx,
            "snapshot": _serialize_board(env),
            "description": desc if name == agent_name else f"{name}: {desc}",
        })

    winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
    winner_label = agent_batch_id if winner.name == agent_name else next(
        (opponents[i] for i, n in enumerate(env.possible_agents[1:])
         if n == winner.name),
        "unknown",
    )
    replay = Replay(
        id=replay_id, agent_batch=agent_batch_id, opponents=opponents,
        turns=turn_records, winner=winner_label, rounds=env.game.round,
    )
    replay_out.parent.mkdir(parents=True, exist_ok=True)
    replay_out.write_text(replay.model_dump_json(indent=2))

    snapshot_out.parent.mkdir(parents=True, exist_ok=True)
    snapshot_out.write_text(__import__("json").dumps({
        "initial": initial_snap,
        "turns": snapshot_turns,
    }, indent=2))
```

- [ ] **Step 4: Run test to verify pass**

Run: `uv run pytest tests/article_export/test_replay_recorder_snapshots.py -v`
Expected: 1 passed (or skipped)

- [ ] **Step 5: Commit**

```bash
git add scripts/article_export/replay_recorder.py tests/article_export/test_replay_recorder_snapshots.py
git commit -m "feat(article): record replay emits board snapshots json"
```

---

### Task 3: Snapshots CLI

**Files:**
- Modify: `scripts/record_replay.py`

- [ ] **Step 1: Update CLI to accept snapshot output**

Replace `scripts/record_replay.py`:

```python
#!/usr/bin/env python
# scripts/record_replay.py
import argparse
from pathlib import Path
from scripts.article_export.replay_recorder import record_replay_with_snapshots


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--batch-id", required=True)
    p.add_argument("--opponents", required=True, help="comma-separated")
    p.add_argument("--data", type=Path, default=Path("data/pokemon.jsonl"))
    p.add_argument("--replay-out", type=Path, required=True)
    p.add_argument("--snapshot-out", type=Path, required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    opponents = [o.strip() for o in args.opponents.split(",")]
    record_replay_with_snapshots(
        agent_model=args.model,
        agent_batch_id=args.batch_id,
        opponents=opponents,
        data_path=args.data,
        replay_out=args.replay_out,
        snapshot_out=args.snapshot_out,
        replay_id=args.id,
        seed=args.seed,
    )
    print(f"Wrote {args.replay_out} and {args.snapshot_out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate snapshots for v1, v3, v6 against the same seed**

```bash
mkdir -p frontend/article/data/runs/v1-to-v7/replays
mkdir -p frontend/article/data/runs/v1-to-v7/snapshots

for v in v1 v3 v6; do
  uv run python scripts/record_replay.py \
    --model models/${v}-256x3.zip --batch-id ${v} \
    --opponents random,early-capture,denial \
    --replay-out frontend/article/data/runs/v1-to-v7/replays/${v}-seed42.json \
    --snapshot-out frontend/article/data/runs/v1-to-v7/snapshots/${v}-seed42.json \
    --id ${v}-seed42 --seed 42
done
```

Expected: 6 files written.

- [ ] **Step 3: Commit data + CLI change**

```bash
git add scripts/record_replay.py frontend/article/data/runs/v1-to-v7/replays/ frontend/article/data/runs/v1-to-v7/snapshots/
git commit -m "feat(article): per-batch replay snapshots for the same seed"
```

---

### Task 4: TrainingCurve component

**Files:**
- Create: `frontend/article/charts/TrainingCurve.svelte`
- Create: `frontend/article/charts/__tests__/TrainingCurve.test.ts`

- [ ] **Step 1: Write a smoke test for prop handling**

```ts
// frontend/article/charts/__tests__/TrainingCurve.test.ts
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import TrainingCurve from '../TrainingCurve.svelte';

describe('TrainingCurve', () => {
  it('renders an SVG with one polyline', () => {
    const { container } = render(TrainingCurve, {
      props: {
        batches: [
          { id: 'v1', total_timesteps: 200000, explained_variance: -0.1,
            entropy_loss: -1.5, value_loss: 0.05 },
          { id: 'v2', total_timesteps: 500000, explained_variance: 0.1,
            entropy_loss: -1.0, value_loss: 0.04 },
        ],
        metric: 'explained_variance',
        currentIndex: 1,
      },
    });
    expect(container.querySelector('svg')).toBeTruthy();
    expect(container.querySelectorAll('circle').length).toBe(2);
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm run test:article`
Expected: FAIL

- [ ] **Step 3: Implement TrainingCurve**

```svelte
<!-- frontend/article/charts/TrainingCurve.svelte -->
<script lang="ts">
  import type { CurvesPerBatch } from '../lib/types';

  export let batches: CurvesPerBatch[];
  export let metric: 'explained_variance' | 'entropy_loss' | 'value_loss';
  export let currentIndex: number;

  const padding = { top: 24, right: 24, bottom: 32, left: 40 };
  const width = 600;
  const height = 300;
  $: innerW = width - padding.left - padding.right;
  $: innerH = height - padding.top - padding.bottom;

  $: ys = batches.map((b) => b[metric]);
  $: yMin = Math.min(...ys, 0);
  $: yMax = Math.max(...ys, 0.1);
  $: yScale = (v: number) =>
    padding.top + innerH - ((v - yMin) / (yMax - yMin)) * innerH;
  $: xScale = (i: number) =>
    padding.left + (batches.length === 1 ? innerW / 2 : (i / (batches.length - 1)) * innerW);

  $: points = batches.map((b, i) => `${xScale(i)},${yScale(b[metric])}`).join(' ');
</script>

<svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
  <line x1={padding.left} x2={width - padding.right}
        y1={yScale(0)} y2={yScale(0)}
        stroke="rgba(255,255,255,0.15)" stroke-dasharray="4 4" />
  <polyline fill="none" stroke="#ff3d8a" stroke-width="2" points={points} />
  {#each batches as b, i}
    <circle
      cx={xScale(i)}
      cy={yScale(b[metric])}
      r={i === currentIndex ? 6 : 3}
      fill={i === currentIndex ? '#ff3d8a' : 'rgba(243,241,236,0.4)'} />
    <text x={xScale(i)} y={height - 8} fill="rgba(243,241,236,0.5)"
          text-anchor="middle" font-size="11">{b.id}</text>
  {/each}
  <text x={8} y={padding.top - 4} fill="rgba(243,241,236,0.7)" font-size="11">
    {metric}
  </text>
</svg>

<style>
  svg { width: 100%; height: auto; display: block; }
</style>
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add frontend/article/charts/TrainingCurve.svelte frontend/article/charts/__tests__/TrainingCurve.test.ts
git commit -m "feat(article): TrainingCurve SVG component"
```

---

### Task 5: BenchmarkBars component

**Files:**
- Create: `frontend/article/charts/BenchmarkBars.svelte`
- Create: `frontend/article/charts/__tests__/BenchmarkBars.test.ts`

- [ ] **Step 1: Write failing test**

```ts
// frontend/article/charts/__tests__/BenchmarkBars.test.ts
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import BenchmarkBars from '../BenchmarkBars.svelte';

describe('BenchmarkBars', () => {
  it('renders one bar per opponent', () => {
    const { container } = render(BenchmarkBars, {
      props: {
        benchmark: {
          opponents: ['agent', 'random', 'early-capture', 'denial'],
          win_rates: [0.4, 0.0, 0.2, 0.4],
          games: 200,
        },
        agentIndex: 0,
      },
    });
    expect(container.querySelectorAll('.bar').length).toBe(4);
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm run test:article`
Expected: FAIL

- [ ] **Step 3: Implement BenchmarkBars**

```svelte
<!-- frontend/article/charts/BenchmarkBars.svelte -->
<script lang="ts">
  import type { BenchmarkResult } from '../lib/types';
  export let benchmark: BenchmarkResult;
  export let agentIndex: number = 0;
</script>

<div class="bars">
  {#each benchmark.opponents as opp, i}
    <div class="row">
      <div class="label" class:agent={i === agentIndex}>{opp}</div>
      <div class="track">
        <div class="bar"
             class:agent={i === agentIndex}
             style="width: {benchmark.win_rates[i] * 100}%">
        </div>
      </div>
      <div class="value">{Math.round(benchmark.win_rates[i] * 100)}%</div>
    </div>
  {/each}
</div>

<style>
  .bars {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-size: 0.9rem;
  }
  .row {
    display: grid;
    grid-template-columns: 8rem 1fr 3rem;
    gap: 0.75rem;
    align-items: center;
  }
  .label { color: var(--muted); }
  .label.agent { color: var(--fg); font-weight: 600; }
  .track {
    background: rgba(255,255,255,0.05);
    height: 0.5rem;
    border-radius: 3px;
    overflow: hidden;
  }
  .bar { background: rgba(243,241,236,0.5); height: 100%; }
  .bar.agent { background: var(--accent); }
  .value { text-align: right; font-variant-numeric: tabular-nums; }
</style>
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: passing

- [ ] **Step 5: Commit**

```bash
git add frontend/article/charts/BenchmarkBars.svelte frontend/article/charts/__tests__/BenchmarkBars.test.ts
git commit -m "feat(article): BenchmarkBars component"
```

---

### Task 6: GameReplayPlayer component

**Files:**
- Create: `frontend/article/replay/GameReplayPlayer.svelte`

The article doesn't need full Board.svelte interactivity — just the visual rendering of a static board. We build a simplified renderer here rather than wrapping the live game store (which has too many dependencies). This trades reuse for clarity.

- [ ] **Step 1: Implement renderer**

```svelte
<!-- frontend/article/replay/GameReplayPlayer.svelte -->
<script lang="ts">
  import type { BoardSnapshot } from './snapshot';

  export let snapshot: BoardSnapshot;
  export let description: string = '';

  const TIER_ORDER: (keyof BoardSnapshot)[] = [
    'legendary_revealed', 'epic_revealed', 'rare_revealed',
    'uncommon_revealed', 'common_revealed',
  ];
</script>

<div class="board">
  <div class="tokens">
    {#each Object.entries(snapshot.tokens) as [color, count]}
      <span class="token" data-color={color}>{count}× {color}</span>
    {/each}
  </div>
  <div class="grid">
    {#each TIER_ORDER as tier}
      <div class="row">
        {#each (snapshot[tier] as any[]) as card}
          {#if card}
            <div class="card" data-tier={card.tier}>
              <div class="name">{card.name}</div>
              <div class="meta">
                <span>+{card.point}</span>
                <span>{card.bonus ?? ''}</span>
              </div>
            </div>
          {:else}
            <div class="card empty"></div>
          {/if}
        {/each}
      </div>
    {/each}
  </div>
  {#if description}
    <p class="caption">{description}</p>
  {/if}
</div>

<style>
  .board {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-size: 0.85rem;
  }
  .tokens {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.5rem;
    background: rgba(255,255,255,0.03);
    border-radius: 6px;
  }
  .grid {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  .row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.25rem;
  }
  .card {
    aspect-ratio: 2/3;
    background: rgba(255,255,255,0.04);
    border-radius: 6px;
    padding: 0.4rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    font-size: 0.7rem;
  }
  .card.empty {
    background: rgba(255,255,255,0.015);
    border: 1px dashed rgba(255,255,255,0.05);
  }
  .card[data-tier="legendary"] { background: linear-gradient(135deg, #6e4cff, #ff3d8a); }
  .card[data-tier="epic"] { background: rgba(110,76,255,0.4); }
  .card[data-tier="rare"] { background: rgba(255,196,77,0.3); }
  .card[data-tier="uncommon"] { background: rgba(220,220,220,0.2); }
  .card[data-tier="common"] { background: rgba(170,120,80,0.25); }
  .name { font-weight: 600; }
  .meta { display: flex; justify-content: space-between; color: rgba(255,255,255,0.7); }
  .caption {
    margin: 0; color: var(--muted); font-size: 0.85rem;
  }
</style>
```

- [ ] **Step 2: Smoke test render**

Add a temporary debug page or use Vite dev with a small test page; verify visual output renders.

- [ ] **Step 3: Commit**

```bash
git add frontend/article/replay/GameReplayPlayer.svelte
git commit -m "feat(article): GameReplayPlayer renders BoardSnapshot"
```

---

### Task 7: Replay scrubber hook

**Files:**
- Create: `frontend/article/replay/useReplayScrubber.ts`
- Create: `frontend/article/replay/__tests__/useReplayScrubber.test.ts`

- [ ] **Step 1: Write failing test**

```ts
// frontend/article/replay/__tests__/useReplayScrubber.test.ts
import { describe, it, expect } from 'vitest';
import { mapScrollToBatchTurn } from '../useReplayScrubber';

describe('mapScrollToBatchTurn', () => {
  it('maps 0..1 to (batchIdx, turnIdx)', () => {
    const batchCounts = [10, 20, 5];
    expect(mapScrollToBatchTurn(0, batchCounts)).toEqual([0, 0]);
    expect(mapScrollToBatchTurn(1, batchCounts)).toEqual([2, 4]);
    const [b, _t] = mapScrollToBatchTurn(0.5, batchCounts);
    expect(b).toBe(1);
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm run test:article`
Expected: FAIL

- [ ] **Step 3: Implement scrubber math**

```ts
// frontend/article/replay/useReplayScrubber.ts
import { clamp } from '../lib/scrollProgress';

export function mapScrollToBatchTurn(
  t: number, batchTurnCounts: number[],
): [number, number] {
  const total = batchTurnCounts.reduce((s, n) => s + n, 0);
  if (total === 0) return [0, 0];
  const target = clamp(t, 0, 1) * (total - 1);
  let cumulative = 0;
  for (let i = 0; i < batchTurnCounts.length; i++) {
    if (target < cumulative + batchTurnCounts[i]) {
      return [i, Math.floor(target - cumulative)];
    }
    cumulative += batchTurnCounts[i];
  }
  const last = batchTurnCounts.length - 1;
  return [last, batchTurnCounts[last] - 1];
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: passing

- [ ] **Step 5: Commit**

```bash
git add frontend/article/replay/useReplayScrubber.ts frontend/article/replay/__tests__/useReplayScrubber.test.ts
git commit -m "feat(article): scroll-to-(batch,turn) mapping"
```

---

### Task 8: TrainingStory section

**Files:**
- Modify: `frontend/article/sections/TrainingStory.svelte`

- [ ] **Step 1: Implement section**

```svelte
<!-- frontend/article/sections/TrainingStory.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { scrollScrub } from '../lib/scrollProgress';
  import { loadCurves, loadRunSummary } from '../lib/data';
  import { loadReplaySnapshots, type ReplaySnapshots } from '../replay/snapshot';
  import { mapScrollToBatchTurn } from '../replay/useReplayScrubber';
  import TrainingCurve from '../charts/TrainingCurve.svelte';
  import BenchmarkBars from '../charts/BenchmarkBars.svelte';
  import GameReplayPlayer from '../replay/GameReplayPlayer.svelte';
  import type { BatchResult, CurvesPerBatch } from '../lib/types';

  let stickyEl: HTMLElement;
  let curves: CurvesPerBatch[] = [];
  let batches: BatchResult[] = [];
  let storyBatches = ['v1', 'v3', 'v6']; // batches with snapshot files
  let snapshotsByBatch: Record<string, ReplaySnapshots> = {};
  let currentBatchIdx = 0;
  let currentTurnIdx = 0;
  let cleanup: () => void = () => undefined;

  $: currentBatchId = storyBatches[currentBatchIdx];
  $: currentSnapshots = snapshotsByBatch[currentBatchId];
  $: currentSnapshot = currentSnapshots?.turns[currentTurnIdx]?.snapshot
                       ?? currentSnapshots?.initial;
  $: currentDescription = currentSnapshots?.turns[currentTurnIdx]?.description ?? '';
  $: currentBatchInfo = batches.find((b) => b.id === currentBatchId);

  onMount(async () => {
    const [summaryRes, curvesRes] = await Promise.all([
      loadRunSummary('v1-to-v7'),
      loadCurves('v1-to-v7'),
    ]);
    batches = summaryRes.batches;
    curves = curvesRes.batches;
    const snaps = await Promise.all(
      storyBatches.map((id) => loadReplaySnapshots(`${id}-seed42`)),
    );
    snapshotsByBatch = Object.fromEntries(
      storyBatches.map((id, i) => [id, snaps[i]]),
    );
    const batchTurnCounts = storyBatches.map(
      (id) => snapshotsByBatch[id]?.turns.length ?? 0,
    );
    cleanup = scrollScrub(stickyEl, (t) => {
      const [b, tu] = mapScrollToBatchTurn(t, batchTurnCounts);
      currentBatchIdx = b;
      currentTurnIdx = tu;
    }, { pin: true, start: 'top top', end: '+=400%' });
  });

  onDestroy(() => cleanup());
</script>

<section class="training-story" bind:this={stickyEl}>
  <div class="sticky-frame">
    <div class="story-text">
      {#if currentBatchInfo}
        <h2>Batch {currentBatchInfo.id}</h2>
        <p class="narrative">{currentBatchInfo.narrative}</p>
        <div class="stats">
          <div><strong>Opponents:</strong> {currentBatchInfo.opponents.join(', ')}</div>
          <div><strong>Episodes:</strong> {currentBatchInfo.episodes.toLocaleString()}</div>
          <div><strong>LR:</strong> {currentBatchInfo.lr}</div>
        </div>
        {#if currentBatchInfo.benchmarks.length}
          <h3>Benchmark</h3>
          <BenchmarkBars
            benchmark={currentBatchInfo.benchmarks[0]}
            agentIndex={0} />
        {/if}
      {/if}
    </div>
    <div class="visuals">
      <TrainingCurve
        batches={curves}
        metric="explained_variance"
        currentIndex={curves.findIndex((c) => c.id === currentBatchId)} />
      {#if currentSnapshot}
        <GameReplayPlayer
          snapshot={currentSnapshot}
          description={currentDescription} />
      {/if}
    </div>
  </div>
</section>

<style>
  .training-story {
    height: 500vh;
    position: relative;
  }
  .sticky-frame {
    position: sticky;
    top: 0;
    height: 100vh;
    display: grid;
    grid-template-columns: 1fr 1.4fr;
    gap: 3rem;
    padding: 3rem;
    align-items: center;
  }
  .story-text h2 {
    font-size: clamp(1.75rem, 3vw, 2.5rem);
    margin: 0 0 1rem;
    letter-spacing: -0.02em;
  }
  .story-text h3 {
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent);
    margin: 2rem 0 0.75rem;
  }
  .narrative { font-size: 1.1rem; color: #d6d3cb; }
  .stats {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 0.9rem;
    color: var(--muted);
    margin: 1.5rem 0;
  }
  .visuals {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }
</style>
```

- [ ] **Step 2: Verify visually**

`npm run dev:article`. Scroll into section 5. Expected: text on left, curve + replay on right, both updating as scroll progresses through five viewport-heights.

- [ ] **Step 3: Commit**

```bash
git add frontend/article/sections/TrainingStory.svelte
git commit -m "feat(article): TrainingStory section with coupled curve and replay scrub"
```

---

## Done

After this plan:
- Section 5 (Training Story) shows the agent learning batch-by-batch as the reader scrolls.
- `TrainingCurve` and `BenchmarkBars` are reusable presentational components.
- `GameReplayPlayer` renders any `BoardSnapshot` independent of the live game store.
- Replay snapshots for v1, v3, v6 are baked at the same seed so the reader sees the same situation handled differently.
- Plan 5 (Agent In Action + polish) is unblocked.
