# DifferentialAgent Rewrite: Unified Threat-Weighted Scoring

**Date:** 2026-06-10
**Status:** Approved design
**File:** `src/pokemon_splendor/agents/differential.py` (full rewrite of `DifferentialAgent`)

## Goal

Replace the current priority-ladder DifferentialAgent with the strongest deterministic,
heuristic-only (no simulation/search) rule-based agent. The agent sabotages opponents
(block-reserves, token denial, evolution-target denial) **only when beneficial to itself** —
enforced structurally by scoring every legal action on one scale and picking the argmax.

## Success criteria

1. **Primary:** >50% win rate vs `DenialAgent` head-to-head (2-player benchmark mode,
   e.g. `--mode benchmark --players differential,denial --games 200+`).
2. Secondary: competitive against the other rule-based agents (bonus_engine, high_point,
   early_capture, evolution_chain) — top scorer in 4p mixed games.

## Decision procedure

Every turn, for every legal main-phase action `a` in the mask:

```
score(a) = self_value(a) + λ × harm(a)
```

Play `argmax score(a)`. Capture, reserve, and token-take compete on one scale —
no priority ladder. Sabotage actions win only when `λ × harm` exceeds the best
self-progress alternative.

## Core quantities

### Effective cost & rounds-to-catch (per player p, card X)

Reuse existing helpers: `get_player_bonuses`, `calculate_effective_cost`.

```
shortfall(p, X) = Σ_c max(0, effective_cost_c(X, p) − tokens_c(p))
rounds(p, X)    = max(1, (shortfall + 2) / 3)
ppr(p, X)       = point(X) / rounds(p, X)        (0 for 0-point cards)
```

### Color demand (per player p, color c)

```
demand_c(p) = board_demand_c(p) + evolve_demand_c(p)     (normalized over colors to sum to 1)
```

**board_demand_c(p)** — how much the current board wants color c, for player p:

```
board_demand_c(p) = Σ over revealed cards k:  point_k × effective_cost_c(k, p)
```

Point-weighting makes colors needed by high-scoring cards count more. Recomputed each turn.

**evolve_demand_c(p)** — missing evolve-bonuses for cards p holds:

```
evolve_demand_c(p) = Σ over unevolved held cards with evolve_into:
                       w_evo(card) × max(0, evolve_req_c(card) − bonuses_c(p))

w_evo(card) = max(0, point(evolve_target) − point(card)) / max(1, missing_bonuses_total)
```

Evolution gain is the **point differential** (the source card stops scoring once evolved —
see `_recalculate_points`, rules.py:50), not the target's raw points.

Note: evolution requires *bonuses* (not tokens) — `get_evolvable_cards` checks `card.evolve`
against `player_bonuses`. So a bonus in a color a player needs for evolution is double-duty.

### Engine quality (per player p)

```
engine_quality(p) = Σ_c bonuses_c(p)^1.5 × demand_c(p)
```

The exponent rewards concentration (5 yellow ≫ 1 of each); demand-weighting kills credit
for engines misaligned with the board (deep yellow engine + yellow-light board = dead weight).
Normalize across players when used in threat.

### Threat (per opponent o)

The game ends when any player reaches 18 points, then **highest points wins** (card count
tiebreak) — see `check_win_condition`, rules.py:282. A player can finish above 18, so threat
compares projected final scores, not distance-to-18:

```
H                    = estimated turns until the first player triggers 18
scoring_rate(p)      = Σ ppr of p's top affordable/near-affordable cards (capped at top 2)
projected_points(p)  = points_p + H × scoring_rate(p)

threat(o) = α × projected_points(o) / max_p projected_points(p)
          + β × engine_quality(o)            (normalized across players)
```

### Sabotage weight

```
λ = λ_base + λ_scale × max_o threat(o)
```

Small early (sabotage is wasteful when nobody is ahead), large when a leader emerges.

## Action scoring

### Capture card X (board slot or own reserve)

```
self_value = ppr(self, X) + engine_delta(X) + evo_unlock(X)
```

- `engine_delta(X)`: increase in our `engine_quality` from X's bonus color.
- `evo_unlock(X)`: point-differential progress toward evolutions of cards we hold whose
  bonus requirements X's bonus advances; **plus**, if X *is* the evolve target of a card we
  hold, the point differential of that evolution (catching the target both scores it and
  banks the evolution).

```
harm = threat(o) × ppr(o, X)                  if X is among threat-leader o's top buys
     + E × threat(o) × evo_differential(o, X) if X is the target of an evolution o could
                                              perform soon (apply_evolve requires the target
                                              on board/reserve — buying it kills the evolve)
```

### Reserve card X

```
self_value = δ × [capture self_value of X] + master_bonus − slot_penalty(len(reserved))
harm       = same harm as capturing X (denial works either way)
```

- δ < 1: deferred value (reserving costs a turn before the buy).
- `master_bonus`: small constant when the Master-token variant is legal.
- `slot_penalty`: grows steeply at 2 reserved cards to keep slots open.

Pure block-reserves emerge naturally: low self_value, high λ×harm.

### Take tokens (3-different combos and 2-same)

```
self_value = Σ_t min(needed_t, taken_t) × urgency
```

- `needed`: shortfall toward our **target card** = the unaffordable card with the highest
  capture self_value.
- `urgency`: higher when one token-take away from affording the target.

```
harm = Σ_t shortage(o, t)
```

`shortage(o, t)` > 0 only when threat-leader o needs token t for their predicted next buy
**and** the bank supply of t is low enough that taking it actually delays them.

### Fallback

If no scored action exists (degenerate mask), play the first legal action.

## Endgame mode

Trigger: any player ≥ 18, or projected to trigger within one round.

- `engine_delta` and `evo_unlock`-for-future terms → 0 (no future to invest in).
- δ → near 0 (reserving rarely pays off).
- Objective: maximize own points this final round; harm targets the projected winner's
  last big buy/evolution.
- Tiebreak nudge: among equal-point actions, prefer the one adding a card
  (card count breaks ties at game end).

## Discard / evolve phases

- **Discard:** keep base-class behavior (discard most-held non-Master type).
- **Evolve:** override base class — evolve the card with the largest **point differential**
  (target − source), not the first legal one. Pass only if no positive-differential
  evolution is legal.

## Tunable weights (initial values, to be swept via benchmark)

| Weight | Meaning | Initial |
|---|---|---|
| exponent | bonus concentration | 1.5 |
| α | projected-points share in threat | 1.0 |
| β | engine quality in threat | 0.5 |
| λ_base | baseline sabotage weight | 0.2 |
| λ_scale | threat-scaled sabotage weight | 1.0 |
| δ | reserve deferral discount | 0.6 |
| E | evolution-denial harm multiplier | 1.0 |
| master_bonus | reserve-with-Master bump | 0.15 |
| slot_penalty | 0/1/2 reserved | 0 / 0.2 / 2.0 |
| urgency | 1-take-from-affording multiplier | 1.5 (else 1.0) |

Tuning loop: benchmark vs DenialAgent, adjust the weight most implicated in observed
losses, re-run. Stop at >50% over ≥200 games.

## Architecture

Single file rewrite of `src/pokemon_splendor/agents/differential.py`:

- `DifferentialAgent(RuleBasedAgent)` — keeps class name and registry entry
  (`__main__.py` `agent_type == "differential"`) unchanged.
- Internal pure helper methods, each independently testable:
  `_demand`, `_engine_quality`, `_threat`, `_lambda`, `_capture_value`, `_reserve_value`,
  `_token_value`, `_harm_capture`, `_harm_tokens`, `_is_endgame`.
- `_main_action(mask)` enumerates legal actions, scores, argmaxes.
- Override `_handle_evolve` for point-differential evolution choice.
- Weights as module-level constants for easy sweeping.

No engine changes; no state mutation (read-only evaluation of `self._game`).

## Testing

- Unit tests for the pure helpers with hand-built `Player`/`Game` fixtures:
  concentration (5-yellow > 5-spread), demand alignment, evolve demand uses point
  differential, threat ordering, endgame switch zeroing engine terms.
- Behavioral tests: block-reserve chosen when opponent one turn from a big buy and we
  have nothing good; block-reserve NOT chosen when we can buy well ourselves.
- Benchmark gate: `--mode benchmark --players differential,denial --games 200`,
  require >50% win rate.
