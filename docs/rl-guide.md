# Reinforcement Learning Guide — Pokémon Splendor

## Concepts

### Observation Size
The vector fed into the neural network describing the full game state. Fixed at **345 floats** regardless of player count:
```
6 board tokens + 14×20 card slots + 4×13 player slots + 4 current-player one-hot + 3 phase = 345
```
Player slots for absent players are zero-padded, making models portable across 2/3/4-player games.

---

### Actor and Critic
Two neural networks trained simultaneously:

**Actor (policy network):** takes observation → outputs action probabilities → plays the game.

**Critic (value network):** takes observation → outputs a single number estimating total future reward from this state. Provides a learning signal at every step so the actor doesn't have to wait until game end.

They share the same MLP backbone with separate output heads:
```
obs (345 floats)
  → Linear(128) → tanh
  → Linear(128) → tanh
  ↙               ↘
Linear(108)      Linear(1)
action logits    state value
(actor)          (critic)
```

---

### MaskablePPO
PPO (Proximal Policy Optimization) is a policy gradient algorithm — it trains the actor to output higher probability for actions that led to higher rewards. "Proximal" means it limits how much the policy can change per update, preventing catastrophic forgetting.

**Maskable** PPO zeroes out illegal actions before softmax so they get zero probability by construction. Essential here since ~90 of 108 actions are invalid at any given step.

During training: softmax over valid actions → sample stochastically.
During inference (`deterministic=True`): argmax over valid actions → always picks highest-probability action.

---

### Neural Network Architecture
Default SB3 `MlpPolicy`: two hidden layers of 64 units. This project uses **[128, 128]**:
```
obs (345) → Linear(128) → tanh → Linear(128) → tanh → Linear(108) → softmax (masked)
```

**Why tanh:** bounded output (-1, 1) matches normalized inputs; smooth gradients everywhere; no dying neuron problem. Fine for shallow networks (2 layers). ReLU is preferred for very deep networks (10+ layers) where vanishing gradients become a concern.

**Why [128, 128] not [64, 64] or [512, 512]:**
- Input features are already meaningful (tokens, points, bonuses) — no need for many layers to discover hidden structure
- 90-card dataset creates enough state variety that 64 units underfit
- PPO's noisy gradient estimates can't reliably train very wide networks without much more data

**Shallow vs deep networks:**
- Use shallow (2-3 layers) when inputs are already featurized/normalized, like this game's obs vector
- Use deep (10+ layers) when inputs are raw/unstructured (pixels, audio, text) and require hierarchical feature extraction

---

### Training Metrics

| Metric | What it means | Healthy range |
|---|---|---|
| `ep_len_mean` | Average game length in player_0 steps | Stabilises around 80–120 |
| `ep_rew_mean` | Average reward per episode | Should track win rate, not just grow |
| `explained_variance` | How well critic predicts returns (0=useless, 1=perfect) | >0.7 |
| `value_loss` | Critic prediction error | Should decrease; rising = reward instability |
| `entropy_loss` | Policy randomness (more negative = more decisive) | Don't let it drop below -3 early |
| `approx_kl` | How much policy changed this update | <0.05 ideally |
| `clip_fraction` | % of updates hitting PPO clip boundary | ~10–20% |

**episodes ≈ total_timesteps / ep_len_mean**
(e.g. 3M steps ÷ 100 steps/game ≈ 30,000 games)

**n_steps** (default 2048): steps collected per PPO update cycle.
`total_timesteps = iterations × n_steps`

---

### Reward Function
Shaping rewards should sum to less than the terminal reward over a full game.

```
Terminal:           win +1.0 / loss -1.0
Points gained:      × 0.01 per point (on catch or evolve)
Bonuses gained:     × 0.01 per bonus (on catch or evolve)
```

Full game budget: ~10 catches × 2pts × 0.01 + ~5 bonus gains × 0.01 ≈ **0.25 total**
Terminal signal (±1.0) dominates → agent optimises for winning, not reward farming.

**Do not reward:** token taking, reserving, game length.
**Do not penalise game length:** games end naturally around 100 steps; a length penalty pushes toward cheap cards over high-value chains.

---

### Curriculum Learning
Train on progressively harder opponents. Keep player count fixed across stages (obs size is tied to num_players, and a saved model's input layer is fixed at training time).

```bash
# Stage 1: learn basics
uv run pokemon-splendor --mode train --opponents random --episodes 3000000 --save v1.zip

# Stage 2: rule-based opponent (confirm >60% vs random before this)
uv run pokemon-splendor --mode train --opponents high-point --episodes 3000000 --resume v1.zip --save v2.zip

# Stage 3: adversarial (confirm v2 has real skills first)
uv run pokemon-splendor --mode train --opponents v2.zip --resume v2.zip --episodes 5000000 --save v3.zip
```

**Do not start adversarial training from scratch** — two untrained models reinforce each other's bad habits.

---

## Commands

### Play

```bash
# Two random agents (default)
uv run pokemon-splendor

# Human vs rule-based agent
uv run pokemon-splendor --players human,high-point

# Human vs trained model
uv run pokemon-splendor --players human,v3.zip

# Two trained models
uv run pokemon-splendor --players v2.zip,v3.zip
```

### Benchmark

```bash
# RL model vs random (2-player)
uv run pokemon-splendor --players v1.zip,random --mode benchmark --games 100

# RL model vs rule-based (2-player)
uv run pokemon-splendor --players v2.zip,high-point --mode benchmark --games 100

# Two RL models vs each other
uv run pokemon-splendor --players v2.zip,v3.zip --mode benchmark --games 100

# 4-player benchmark (all player counts work since obs is fixed at 345)
uv run pokemon-splendor --players v3.zip,high-point,denial,early-capture --mode benchmark --games 50
```

### Train

```bash
# 2-player: RL vs random (1 opponent = 2 players)
uv run pokemon-splendor --mode train --opponents random --episodes 3000000 --save v1.zip

# 2-player: resume training against stronger opponent
uv run pokemon-splendor --mode train --opponents high-point --episodes 3000000 --resume v1.zip --save v2.zip

# 2-player: adversarial against existing model
uv run pokemon-splendor --mode train --opponents v2.zip --resume v2.zip --episodes 5000000 --save v3.zip

# 3-player: RL vs two opponents (2 opponents = 3 players)
uv run pokemon-splendor --mode train --opponents random,high-point --episodes 3000000 --save v1_3p.zip

# 4-player: RL vs three opponents (3 opponents = 4 players)
uv run pokemon-splendor --mode train --opponents random,high-point,denial --episodes 3000000 --save v1_4p.zip

# Curriculum — fix player count, escalate opponent quality
uv run pokemon-splendor --mode train --opponents random,random --episodes 2000000 --save v1.zip
uv run pokemon-splendor --mode train --opponents random,high-point --episodes 3000000 --resume v1.zip --save v2.zip
uv run pokemon-splendor --mode train --opponents high-point,denial --episodes 5000000 --resume v2.zip --save v3.zip
```

### Available agent types
```
random          uniform random valid action
human           interactive stdin
early-capture   catches cheapest affordable card
high-point      maximises points-per-round ratio
bonus-engine    builds bonus engine first, then switches to points
evolution-chain scores cards by full evolution chain value
denial          reserves cards opponents can almost afford
model.zip       any .zip path loads that trained RL model
```

### Data Management

```bash
# Enter REPL
uv run pokemon-splendor --mode data

# With a different data file
uv run pokemon-splendor --mode data --data path/to/pokemon.jsonl
```

REPL commands: `l`ist, `s`how, `a`dd, `u`pdate, `d`elete, `q`uit
