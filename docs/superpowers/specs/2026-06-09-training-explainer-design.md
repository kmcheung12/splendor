# RL Training Explainer — Design Spec

## Overview

An interactive, scroll-driven web article that explains how the Pokemon Splendor RL agent was trained. Inspired by Bartosz Ciechanowski's articles and Tensorflow Playground: the page tells the story linearly (top to bottom), with three centrepiece interactive elements — a live game replay, a training curve explorer, and a neural network visualisation. Audience is both general readers (no ML background) and practitioners; the narrative is layered so technical depth reveals as the reader scrolls.

The article is a **standalone Svelte app** under `frontend/article/` that shares components (board, cards, tokens, player panels) with the existing game app. A **Python export pipeline** generates JSON data files (training stats, game replays, model snapshots) into `frontend/article/data/`; the article reads them at build time. Designed for extensibility: future training runs add new JSON files and appear in the article automatically.

---

## Goal

- A page at `geo-dude.com/splendor/training` (or similar) that an interested reader can scroll through in 10–20 minutes and come away understanding: what reinforcement learning is, how this specific agent was trained, why it plays the way it does.
- Reusable visual primitives so future training runs add to the article without rewriting components.
- Visual quality at the level of Ciechanowski / Awwwards-tier explainers — not a typical "blog post with embedded charts".

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Source of truth                                            │
│   training_log.txt   model .zip files   game replay traces  │
└──────────────┬──────────────────────────────────────────────┘
               │ scripts/export_article_data.py
               ▼
┌─────────────────────────────────────────────────────────────┐
│  frontend/article/data/                                     │
│   runs/index.json          (list of available runs)         │
│   runs/<run-id>/           (one directory per training run) │
│     summary.json           (batches, results, narrative)    │
│     curves.json            (training metric timeseries)     │
│     replays/<id>.json      (full game replays)              │
│     network.json           (architecture spec + weight stats)│
└──────────────┬──────────────────────────────────────────────┘
               │ Vite build reads JSON at compile time
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Svelte article bundle (static)                             │
│   Article.svelte                                            │
│     sections/                                               │
│       Hero.svelte           (opening particle + thesis)     │
│       Game101.svelte        (game rules with mini-board)    │
│       RL101.svelte          (reward, state, action concepts)│
│       NetworkAnatomy.svelte (Canvas2D NN diagram)           │
│       TrainingStory.svelte  (TrainingCurve + GameReplay)    │
│       NetworkInDepth.svelte (WebGL NN with live activations)│
│       AgentInAction.svelte  (coupled replay + NN viz)       │
│       Closing.svelte        (links, credits, what's next)   │
│     viz/                                                    │
│       NetworkVisualization.ts  (interface)                  │
│       Canvas2DNetworkViz.ts                                 │
│       WebGLNetworkViz.ts                                    │
│       createNetworkViz.ts      (factory)                    │
│     replay/                                                 │
│       GameReplayPlayer.svelte  (wraps Board.svelte)         │
│       useReplayScrubber.ts     (scroll → turn index)        │
│     charts/                                                 │
│       TrainingCurve.svelte     (SVG + tweened)              │
│       BenchmarkBars.svelte                                  │
│     lib/                                                    │
│       scrollProgress.ts        (Lenis + ScrollTrigger)      │
│       data.ts                  (JSON loaders, typed)        │
└─────────────────────────────────────────────────────────────┘
```

The article bundle is built and deployed independently of the game app but shares component code through relative imports (`../../components/Board.svelte`). The article never talks to a server at runtime — all data is baked in at build time.

---

## Article Structure

Linear scroll-through, eight sections. Each centrepiece interaction is anchored to a sticky viewport that scrubs as the reader scrolls past it.

### 1. Hero
Full-viewport opening. Title, one-sentence thesis: *"We taught a neural network to play Splendor by letting it play itself a million times."* Background: particles forming into a board state, cards flipping in. Lenis smooth scroll begins on first scroll input.

### 2. Game 101
Inline mini-board (reused `Board.svelte` in compact mode). Reader scrolls through a 4–5 turn example: take tokens → reserve → catch. Each action triggers a synchronised diagram callout explaining the rule. Sticky board on the right; text scrolls on the left.

### 3. RL 101
Concepts: **observation**, **action**, **reward**, **policy**, **value**. Each concept is paired with its concrete Splendor instance — observation is the board state vector, action is the 50-dim discrete space, reward is +1 for winning. Inline animated diagrams (SVG) show the agent-environment loop.

### 4. Network Anatomy
First appearance of the network. **Canvas2D implementation** — clean, didactic. Layers as columns of nodes, edges between them. Reader scrubs over the network as text explains: input layer (observation), hidden layers (256 wide × 3), policy head (action probabilities), value head (win probability). No activations yet — this section is about structure.

### 5. Training Story
The longest section. The training curve appears in a sticky viewport on the right; on the left, the story scrolls past in chapters — *"v1: random opponent, learns the basics"*, *"v2: high-point, plateaus at 45%"*, *"v3: mixed opponents break the plateau"*, etc. As each chapter scrolls into view, the curve animates the corresponding batch and a small replay snippet plays the agent at that stage. The same game-state-at-time-T is shown for each batch, so the reader sees the agent literally getting better at the same situation.

### 6. Network In Depth
**WebGL implementation.** The Canvas2D diagram from §4 lifts off the page, rotates into 3D space, layers separate like sediment. Edge glow shader; depth fog. Reader can mouse-drag to rotate. Inline annotations point at policy head and value head as they fork in the network topology. Reader scrubs the camera with scroll.

### 7. Agent In Action
Coupled viewport: the game replay on the left, the WebGL network on the right, both driven by the same scroll position. As the reader scrolls through a single championship-quality game, each turn highlights:
- the input observation (board state, tokens, opponent hands)
- the activations flowing through the network
- the top-k action probabilities the network considered
- the chosen action overlaid on the board

This is the payoff moment: the abstract network from §6 is now *thinking* in real time as the agent plays.

### 8. Closing
Links to source code, the play-the-agent demo, training logs. Brief acknowledgement of what's still missing (compares vs MCTS, AlphaZero results). Credits.

---

## Data Pipeline

### Python: `scripts/export_article_data.py`

Reads `training_log.txt`, model `.zip` and `.pt` files, and a curated list of replay game JSONs. Writes typed JSON into `frontend/article/data/runs/<run-id>/`. Idempotent — re-running regenerates from sources.

CLI:
```bash
uv run python scripts/export_article_data.py \
  --run-id v1-to-v6 \
  --log training_log.txt \
  --models-dir models/ \
  --replays-dir frontend/article/data/replays-source/ \
  --out frontend/article/data/runs/v1-to-v6/
```

### Data shapes

`runs/index.json`:
```json
{
  "runs": [
    { "id": "v1-to-v6", "title": "First curriculum: random → self-play", "default": true }
  ]
}
```

`summary.json`:
```json
{
  "title": "...",
  "batches": [
    {
      "id": "v1",
      "stage": 1,
      "opponents": ["random"],
      "episodes": 200000,
      "lr": 0.0001,
      "result": { "explained_variance": -0.12, "value_loss": 0.04 },
      "benchmarks": [
        { "opponents": ["random","early-capture","denial"], "wins": [0.0, 0.0, 0.42, 0.58], "games": 200 }
      ],
      "narrative": "Pure random opponent. The agent has not yet learned to buy anything."
    }
  ]
}
```

`curves.json`:
```json
{
  "batches": [
    { "id": "v1", "timesteps": [...], "explained_variance": [...], "entropy_loss": [...] }
  ]
}
```

`replays/<id>.json`:
```json
{
  "id": "v6-vs-denial-game-42",
  "agent_batch": "v6",
  "opponents": ["denial", "early-capture", "random"],
  "turns": [
    { "turn": 1, "player": "v6", "observation": [...], "action": 12, "action_desc": "take 3 different tokens", "value": 0.51, "policy_top_k": [{ "action": 12, "prob": 0.41 }, ...] }
  ],
  "winner": "v6",
  "rounds": 28
}
```

`network.json`:
```json
{
  "hidden_size": 256,
  "num_layers": 3,
  "input_size": 421,
  "output_size": 50,
  "weight_stats": [
    { "layer": 0, "shape": [256, 421], "mean": 0.001, "std": 0.04 }
  ]
}
```

Replays are pre-generated by a sibling script `scripts/record_replay.py` that runs a single game and captures per-turn observations, activations (from the loaded model), and chosen actions. Activations are not embedded directly in `replays/*.json` to keep size reasonable; instead the replay records the observation and the live article re-runs the network in-browser on demand. (See "Network in browser" below.)

### Network in browser

The trained policy network runs in the browser via ONNX Runtime Web. `scripts/export_onnx.py` exports a `.zip` PPO model to `frontend/article/data/runs/<run-id>/network.onnx`. The article loads ONNX once, then runs forward passes per replay turn to get fresh activations to drive the viz. This avoids embedding hundreds of MB of activation traces and means the viz responds correctly if the reader scrubs to any turn.

Activation extraction: ONNX Runtime Web's session output can be hooked to return intermediate tensors. The exported ONNX is configured to emit each hidden layer's pre-activation as a named output.

---

## Rendering Abstraction

Two NN visualisation implementations behind one interface, swappable per section.

### Interface

```ts
// frontend/article/viz/NetworkVisualization.ts
export interface NetworkVisualization {
  mount(container: HTMLElement, network: NetworkSpec): void;
  setActivations(obs: Float32Array, layerOutputs: LayerActivations): void;
  setScrollProgress(t: number): void;
  setHighlightedAction(actionIdx: number | null): void;
  dispose(): void;
}

export interface NetworkSpec {
  inputSize: number;
  hiddenLayers: number[];
  outputSize: number;
}

export interface LayerActivations {
  layers: Float32Array[];
  policy: Float32Array;
  value: number;
}

export type VizType = 'canvas2d' | 'webgl';
export function createNetworkViz(type: VizType): NetworkVisualization;
```

### Canvas2DNetworkViz

Top-down 2D layout. Nodes as filled circles; edges as alpha-modulated lines. Activations animate node fill colour (cool → hot) and edge alpha. Layer columns left-to-right. `setScrollProgress(t)` reveals layers progressively (t=0 → input only; t=1 → full network including heads).

Used in §4 Network Anatomy and as a fallback for environments where WebGL is unavailable.

### WebGLNetworkViz (Three.js)

Layers as parallel planes in 3D space. Nodes as `InstancedMesh` of spheres. Edges as `LineSegments` with a custom glow shader. Camera dolly driven by `setScrollProgress`. Activations animate via uniform updates on a per-frame basis. Bloom post-processing for the hero feel.

`setHighlightedAction(idx)` raises the corresponding output node, scales the edges feeding it, draws a glow path back through the contributing hidden neurons (rank-1 attribution: top contributors by weight × activation).

Used in §6 Network In Depth and §7 Agent In Action.

### Factory

```ts
export function createNetworkViz(type: VizType): NetworkVisualization {
  if (type === 'webgl') {
    if (!isWebGLAvailable()) return new Canvas2DNetworkViz();
    return new WebGLNetworkViz();
  }
  return new Canvas2DNetworkViz();
}
```

Falls back to Canvas2D when WebGL is unavailable.

---

## Scroll Choreography

### Lenis (smooth scroll)

Lenis owns the actual scroll position. Mounted once at app root. Gives momentum-style scroll on touchpads and inertia on wheel. Disabled on `prefers-reduced-motion`.

### GSAP ScrollTrigger (scrub timelines)

Each centrepiece interaction registers a `ScrollTrigger` with `scrub: true`, pinning the viewport while the reader scrolls past. The trigger emits a 0..1 progress value consumed by:

- `NetworkVisualization.setScrollProgress(t)`
- `GameReplayPlayer.setReplayProgress(t)` — maps t → turn index
- Section-specific reveal logic (e.g. text columns sliding in)

Pattern (one `scrollProgress.ts` helper exposes both):

```ts
export function scrollScrub(
  triggerEl: HTMLElement,
  onUpdate: (t: number) => void,
  opts?: { start?: string; end?: string; pin?: boolean }
): () => void;
```

### Reduced motion

`@media (prefers-reduced-motion)`: Lenis disabled, GSAP scrub replaced with section-based reveals (IntersectionObserver), Three.js bloom/postprocessing disabled, particle hero replaced with a static board image.

---

## Visual Design

### Palette

Anchored on the existing game's Pokémon-TCG tier colours:
- Common — brown gradient
- Uncommon — silver gradient
- Rare — gold gradient
- Epic — purple gradient
- Legendary — rainbow shimmer

Article background: near-black (`#0a0d12`) with subtle warm noise texture. Text: warm off-white. Accent: a single hot colour (electric pink `#ff3d8a`) used sparingly for "this is the important word" callouts and current-scroll-position indicators.

### Motion language

- **Slow, weighted ease curves.** No bouncy springs. Cards land with `cubic-bezier(0.22, 1, 0.36, 1)` and a slight settle. Camera moves use the same curve.
- **Long durations.** Hero opening is 4 seconds; section transitions 800ms; small UI feedbacks 200ms. The article rewards patience.
- **Sound is not in scope.** Optional ambient pad considered but cut for accessibility.

### Hero moments (where stunning is mandatory)

1. **Opening particle assembly** — 4-second WebGL particle field resolves into the actual current board state. Particles colour-coded by where they'll land (red → tokens, gold → Legendary slot, etc.).
2. **Network 3D unfurl** — at start of §6, the flat 2D network rotates into 3D with parallax depth, layers separating into z-space, glow turning on like a switch.
3. **Coupled scrubbing in §7** — the moment when scroll movement *simultaneously* advances the game replay, fires activations through the network, and lights up the chosen action's softmax bar. This is the conceptual climax of the article.

Other sections favour clarity over spectacle.

---

## Performance Budget

| Target | Budget |
|---|---|
| First contentful paint | < 1.5s (text + hero shell) |
| Hero particle field ready | < 3s |
| Sustained frame rate during scrub | 60 fps on a 2020-era laptop |
| Bundle size (gzip) | < 600 KB JS + < 200 KB ONNX |
| Total page weight | < 4 MB |

Strategies:
- ONNX model lazy-loaded only when §7 (Agent In Action) is approaching viewport.
- Three.js bundle code-split — not loaded until §6.
- Game replay JSON files lazy-loaded per section.
- All images served via `srcset` and AVIF where supported.

---

## File Structure & File Changes

```
frontend/
  article/                                 [NEW]
    index.html
    main.ts
    Article.svelte
    sections/
      Hero.svelte
      Game101.svelte
      RL101.svelte
      NetworkAnatomy.svelte
      TrainingStory.svelte
      NetworkInDepth.svelte
      AgentInAction.svelte
      Closing.svelte
    viz/
      NetworkVisualization.ts
      Canvas2DNetworkViz.ts
      WebGLNetworkViz.ts
      createNetworkViz.ts
    replay/
      GameReplayPlayer.svelte
      useReplayScrubber.ts
    charts/
      TrainingCurve.svelte
      BenchmarkBars.svelte
    lib/
      scrollProgress.ts
      data.ts
      onnxRunner.ts
    data/
      runs/
        v1-to-v6/
          summary.json
          curves.json
          network.json
          network.onnx
          replays/
            v6-vs-denial-game-42.json
            v1-vs-random-game-3.json
            ...
        index.json
  src/                                     [EXISTING]
    components/                            [SHARED — used by both apps]
    App.svelte                             [existing game app]
  vite.article.config.ts                   [NEW — separate Vite config]
  package.json                             [MODIFY — add article build script]

scripts/                                   [NEW SCRIPTS]
  export_article_data.py
  export_onnx.py
  record_replay.py
```

---

## Out of Scope

- A way for readers to train their own model in-browser (Tensorflow Playground does this with toy networks; our PPO agent is too large).
- Multi-language / i18n.
- Comments or discussion threads.
- Server-side rendering — the article is a fully static bundle.
- Analytics — no tracking.
- A11y beyond `prefers-reduced-motion` and semantic HTML. Full screen-reader narration of the interactive sections is acknowledged as a gap.
- Mobile-first layout. The article assumes a desktop reader; mobile gets a degraded "read the text, see static images" experience.
- A unified runs comparison page. v1-to-v6 is the only run authored in this spec; the extensibility hooks are present, but a "compare runs" section is future work.

---

## Testing

- **Unit tests** — Python export pipeline (golden JSON snapshots), JSON loaders, replay scrubber math.
- **Visual regression** — Playwright + percy-style snapshots of each section at three scroll positions.
- **Performance budget gate** — Lighthouse CI in the build, fails on regression to bundle size or LCP.
- **Manual** — full scroll-through on Chrome / Safari / Firefox at 1440p, 1080p, and a Retina MacBook. Reduced-motion mode separately verified.

---

## Open Decisions Worth Flagging

These are *decided* in this spec but worth highlighting for the implementer to push back on if they hit friction:

- **ONNX Runtime Web vs. embedding activations as JSON.** Decided in favour of ONNX because it scales to arbitrary scrubbing. If ONNX bundle size becomes a problem, fall back to pre-baked activation JSON for a fixed set of "story moment" turns.
- **GSAP ScrollTrigger over hand-rolled IntersectionObserver.** Decided for the scrub interaction primitive. The article *can* be written with only IntersectionObserver for section reveals, but the scrub-driven coupling of replay + network in §7 essentially requires ScrollTrigger.
- **Lenis vs. native scroll.** Decided in favour of Lenis for desktop, with `prefers-reduced-motion` opting back to native. If Lenis interacts badly with ScrollTrigger pinning (it has a known caveat), we use Lenis's official `lenis-scrolltrigger` glue.
