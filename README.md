# Pokemon Splendor

Online demo
https://geo-dude.com/splendor

Desktop
![Desktop](desktop.png)

Mobile
<p>
  <img src="mobile.png" width="45%">
  <img src="mobile2.png" width="45%">
</p>

## Play

```bash
# Two random agents (rendered)
uv run pokemon-splendor

# Human vs rule-based agent
uv run pokemon-splendor --players human,high-point

# Human vs MCTS
uv run pokemon-splendor --players human,mcts --mcts-sims 200 --mcts-depth 4

# Human vs trained RL model
uv run pokemon-splendor --players human,v73p3.zip

# Human vs AlphaZero checkpoint
uv run pokemon-splendor --players human,alpha:alpha_checkpoints/alpha_0100.pt
```

Available agent types: `random`, `human`, `early-capture`, `high-point`, `bonus-engine`,
`evolution-chain`, `denial`, `mcts`, `<model>.zip`, `alpha:<path.pt>`

---

## Benchmark

```bash
# 2-player head-to-head (500 games for statistical confidence)
uv run pokemon-splendor --mode benchmark --games 500 \
    --players v73p3.zip,v7e.zip --workers 12

# 4-player mixed table (most informative for generalisation)
uv run pokemon-splendor --mode benchmark --games 500 \
    --players v73p3.zip,random,denial,early-capture --workers 12

# RL model vs MCTS
uv run pokemon-splendor --mode benchmark --games 100 \
    --players v73p3.zip,mcts --mcts-sims 50 --mcts-depth 2 --workers 8

# Alpha vs MCTS
uv run pokemon-splendor --mode benchmark --games 100 \
    --players alpha:alpha_checkpoints/alpha_0100.pt,mcts \
    --mcts-sims 50 --mcts-depth 2 --workers 8

# Compare two alpha checkpoints
uv run pokemon-splendor --mode benchmark --games 100 \
    --players alpha:alpha_checkpoints/alpha_0010.pt,alpha:alpha_checkpoints/alpha_0100.pt \
    --workers 8
```

Use `--workers` to parallelise across CPU cores. `--games 500` gives a ±4.4% confidence
interval at 95% — enough to distinguish real improvement from noise.

The 4-player mixed benchmark is more informative than 2-player for generalisation: a model
that only wins in 2-player may be exploiting opponent-specific patterns rather than playing
strong general Splendor.

---

## PPO / RL training

### Working curriculum (v7e → v73p3)

```bash
# Fine-tune from strongest existing model against mixed opponents
uv run pokemon-splendor --mode train \
    --opponents denial,v7e.zip --episodes 1000000 \
    --resume v7e.zip --lr 0.00003 --save v73p.zip --workers 8

# Continue from best checkpoint — same opponents, lower lr
uv run pokemon-splendor --mode train \
    --opponents denial,v7e.zip --episodes 1000000 \
    --resume v73p.zip --lr 0.00002 --save v73p3.zip --workers 8

# Train from scratch with a larger network (512 wide, 4 layers)
uv run pokemon-splendor --mode train --opponents random \
    --episodes 200000 --hidden-size 512 --hidden-layers 4 --save v1-512.zip
```

`--hidden-size` and `--hidden-layers` set the PPO network width and depth for new models. They are **ignored on `--resume`** — the architecture is always read from the `.zip` file.

**Benchmark results (500 games, 4-player mixed vs random/denial/early-capture):**

| Model | Win rate | Notes |
|-------|----------|-------|
| v7e   | 33.0%    | baseline |
| v73p  | 39.4%    | fine-tune from v7e |
| v73p3 | 43.8%    | continued fine-tune |
| v73p4 | 47.4%    | lr=1e-05 |
| v73p5 | 54.4%    | lr=5e-06 |
| v7-4p | 58.2%    | 4-player training vs denial,v73p4,v7e |
| v7-4p2 | 60.6%  | +MCTS opponent (slow) |
| v7-4p3 | 62.8%  | self-play opponents |
| v7-sp  | 67.0%  | self-play vs self, lr=1e-06 |
| v7-sp4 | 77.8%  | self-play x4 |
| v7-sp7 | 81.8%  | self-play x7 |
| v7-sp16 | 84.8% | self-play x16, lr raised to 3e-06 |
| v7-sp20 | ~85%  | self-play x20, converged ceiling |

v73p5 vs v73p4 in 2-player head-to-head: **58.8%**
v7-4p vs v73p5 in 2-player head-to-head: **57.8%**

**Note on MCTS benchmarks:** The 4-player mixed benchmark saturates once the model
dominates denial/early-capture. Use multi-model head-to-head (2000 games) and
self-referential MCTS for later-stage evaluation:

```bash
# Multi-model spanning full range — best for detecting real progress
uv run pokemon-splendor --mode benchmark --games 2000 \
    --players v7-sp20.zip,v7-sp16.zip,v7-sp12.zip,v7-sp9.zip --workers 12

# Self-referential MCTS — measures how much search adds over pure policy
uv run pokemon-splendor --mode benchmark --games 400 \
    --players v7-sp20.zip,mcts --mcts-sims 200 --mcts-depth 3 \
    --mcts-opponent v7-sp20.zip --workers 8
```

v7-sp20 wins ~27% against MCTS(200 sims, depth 3) using its own policy as rollout.
Explicit search still adds value; the gap closes as the policy improves.

**Self-play curriculum (v7-sp series):**

The fixed-opponent ceiling (~62%) was broken by training against the model itself.
Self-play compounds: sp9→sp16→sp20 spans a 22pp gap in multi-model benchmarks.

```bash
# Start self-play from best fixed-opponent model
uv run pokemon-splendor --mode train \
    --opponents denial,v7-4p3.zip,v7-4p3.zip --episodes 1000000 \
    --resume v7-4p3.zip --lr 0.000001 --save v7-sp.zip --workers 8

# Continue — always train against current best twice
uv run pokemon-splendor --mode train \
    --opponents v7-sp16.zip,v7-sp19.zip,v7-sp19.zip --episodes 1000000 \
    --resume v7-sp19.zip --lr 0.000008 --save v7-sp20.zip --workers 8
```

Key lessons:
- **lr=1e-06** for early self-play; raise to **3e-06 then 8e-06** as clip_fraction approaches zero
- **5e-07 is too small** — policy freezes (clip_fraction=0, no learning)
- **Train against current best twice** — one diversity anchor (older model or denial)
- **Adjacent benchmarks are unreliable** — per-iteration gains (~1-2pp) are smaller than benchmark noise; span 4+ iterations for a meaningful comparison
- **Entropy collapse** (entropy_loss approaching -0.25) signals the policy is over-converging; inject diversity or raise lr
- **Converged** when 2000-game head-to-head between consecutive models is ~50%

### Key training lessons

**Mixed opponents prevent catastrophic forgetting.** Training against a single opponent
(e.g. only `v7e.zip`) causes the model to overfit to that opponent's patterns. Adding
`denial` as a second opponent anchors generalisation and prevents regression.

**Watch `explained_variance` in training output.** Values below 0.3 mean the critic
hasn't converged — more episodes will likely improve the policy further. The v73p3 run
finished at 0.104, leaving significant room for improvement.

**Confirm improvement before continuing.** Always benchmark the new model against the
previous one before committing to the next training run:
```bash
uv run pokemon-splendor --mode benchmark --games 500 \
    --players new.zip,old.zip --workers 12
```

If the new model regresses, go back to the last good checkpoint rather than continuing.

**Decrease lr as training matures:**
- Initial fine-tuning: `--lr 0.00003`
- Continued runs: `--lr 0.00002`
- Stabilising: `--lr 0.00001`

**MCTS opponents are slow.** Using `mcts:sims:depth:model.zip` as an opponent drops fps
significantly (400–600 vs 1200+ for RL opponents). Use low sim counts to keep throughput
reasonable:
```bash
# Train against MCTS using a trained model as its rollout policy
uv run pokemon-splendor --mode train \
    --opponents "mcts:50:2:v73p5.zip",denial --episodes 1000000 \
    --resume v7-4p.zip --lr 0.000001 --save v7-mcts.zip --workers 8
```
The format is `mcts:<sims>:<depth>:<model.zip>`. 50 sims / depth 2 is a reasonable
balance; higher sims give a stronger opponent but drop fps further.

**4-player training improves generalisation.** Training against 3 opponents (4-player)
produces higher explained_variance and stronger benchmark results than 3-player, despite
noisier reward signal. Use `--opponents a,b,c` for 4-player training:
```bash
uv run pokemon-splendor --mode train \
    --opponents denial,v73p4.zip,v7e.zip --episodes 1000000 \
    --resume v73p5.zip --lr 0.000002 --save v7-4p.zip --workers 8
```

### Training from scratch (curriculum)

```bash
# Stage 1: learn basics against random (~200k steps)
uv run pokemon-splendor --mode train --opponents random \
    --episodes 200000 --save v1.zip

# Stage 2: tighten up against a rule-based opponent (~300k steps)
uv run pokemon-splendor --mode train --opponents high-point \
    --resume v1.zip --episodes 300000 --save v2.zip

# Stage 3: adversarial — train against mixed opponents
uv run pokemon-splendor --mode train --opponents denial,v2.zip \
    --resume v2.zip --episodes 500000 --save v3.zip
```

The rule-based stage (v2) is the key bridge. If v2 isn't beating `high-point` at least
~55% of the time, Stage 3 is premature.

---

## AlphaZero training

Each iteration: generates self-play games, trains on a replay buffer, saves a checkpoint.
Meaningful play typically emerges after 50–100 iterations.

```bash
# Train from scratch
uv run pokemon-splendor --mode alpha-train \
    --alpha-iters 200 --alpha-games 100 --alpha-sims 100 --alpha-depth 4 \
    --alpha-checkpoint-dir alpha_checkpoints --workers 8

# Train with a larger network (512×4)
uv run pokemon-splendor --mode alpha-train \
    --alpha-iters 200 --alpha-games 100 --alpha-sims 100 --alpha-depth 4 \
    --alpha-hidden-size 512 --alpha-hidden-layers 4 \
    --alpha-checkpoint-dir alpha_checkpoints_512 --workers 8

# Resume from a checkpoint
uv run pokemon-splendor --mode alpha-train \
    --alpha-resume alpha_checkpoints/alpha_0100.pt --alpha-start-iter 101 \
    --alpha-iters 200 --alpha-games 100 --alpha-sims 100 --alpha-depth 4 \
    --alpha-checkpoint-dir alpha_checkpoints --workers 8
```

**Recommended: 100 games per iteration.** 20 games/iter produces noisy gradients that contaminate the replay buffer — once a bad model is accepted, it poisons the buffer in a feedback loop. 100 games/iter provides stable signal.

**Migrate existing checkpoints** after a training run completes (one-time, idempotent):
```bash
uv run python scripts/migrate_alpha_checkpoints.py --dry-run  # preview
uv run python scripts/migrate_alpha_checkpoints.py            # apply
```
This embeds architecture metadata into legacy `.pt` files so they load correctly after upgrading.

**Benchmark results at 100 iterations:**
- iter 100 vs iter 1: **67% win rate** — consistent improvement
- iter 100 vs random: ~98%
- iter 100 vs mcts (50 sims): ~8% — MCTS with hand-crafted eval remains strong

Policy loss dropped from ~4.68 (random) to 1.33 at iter 100. Value loss 0.060.
The gap vs MCTS reflects that 100 gradient updates is still early — thousands of
iterations and more games per iteration are needed to approach MCTS strength.

---

## Data REPL

```bash
uv run pokemon-splendor --mode data
```
