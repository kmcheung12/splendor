# Training Explainer Plan 2: Article Shell

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the static Svelte article bundle as a second app in `frontend/`, wire Lenis smooth scroll + GSAP ScrollTrigger, load the run data from Plan 1, and ship the four non-interactive sections (Hero, Game101, RL101, Closing). Output: a deployable static site reachable via `npm run dev:article` and `npm run build:article`.

**Architecture:** A sibling Svelte app under `frontend/article/`. Shares `frontend/src/components/` (Board, CardSlot, etc.) via relative imports — no duplication. Uses a separate `vite.article.config.ts` and `index.html` so it builds to `frontend/dist-article/`. Scroll choreography lives in `lib/scrollProgress.ts` as a thin wrapper over Lenis + ScrollTrigger.

**Tech Stack:** Svelte 4, Vite, TypeScript, Lenis, GSAP + ScrollTrigger, ESLint + Prettier (inherits from existing frontend).

---

### Task 1: Vite config and entry HTML for article app

**Files:**
- Create: `frontend/vite.article.config.ts`
- Create: `frontend/article/index.html`
- Create: `frontend/article/main.ts`
- Create: `frontend/article/Article.svelte`
- Modify: `frontend/package.json`
- Modify: `frontend/tsconfig.json`

- [ ] **Step 1: Add the Vite config**

```ts
// frontend/vite.article.config.ts
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { resolve } from 'path';

export default defineConfig({
  plugins: [svelte()],
  root: 'article',
  publicDir: resolve(__dirname, 'article/data'),
  build: {
    outDir: resolve(__dirname, 'dist-article'),
    emptyOutDir: true,
  },
  server: { port: 5174 },
});
```

- [ ] **Step 2: Add `index.html` and `main.ts`**

```html
<!-- frontend/article/index.html -->
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>How we taught a network to play Splendor</title>
    <link rel="stylesheet" href="./style.css" />
  </head>
  <body>
    <div id="article"></div>
    <script type="module" src="./main.ts"></script>
  </body>
</html>
```

```ts
// frontend/article/main.ts
import Article from './Article.svelte';

const app = new Article({ target: document.getElementById('article')! });
export default app;
```

- [ ] **Step 3: Add a minimal Article.svelte**

```svelte
<!-- frontend/article/Article.svelte -->
<script lang="ts">
</script>

<main>
  <h1>How we taught a network to play Splendor</h1>
  <p>Coming soon.</p>
</main>

<style>
  main {
    max-width: 720px;
    margin: 0 auto;
    padding: 4rem 1.5rem;
    color: #f3f1ec;
    background: #0a0d12;
    min-height: 100vh;
    font-family: system-ui, sans-serif;
  }
</style>
```

- [ ] **Step 4: Add package.json scripts**

In `frontend/package.json` under `scripts`, add:
```json
"dev:article": "vite --config vite.article.config.ts",
"build:article": "vite build --config vite.article.config.ts"
```

- [ ] **Step 5: Verify dev server boots**

```bash
cd frontend && npm install && npm run dev:article
```

Expected: Vite says "Local: http://localhost:5174/". Visit the URL, see the placeholder title.

- [ ] **Step 6: Commit**

```bash
git add frontend/vite.article.config.ts frontend/article/ frontend/package.json frontend/tsconfig.json
git commit -m "feat(article): scaffold Svelte article app at frontend/article"
```

---

### Task 2: Install Lenis + GSAP

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install deps**

```bash
cd frontend && npm install lenis gsap
```

- [ ] **Step 2: Verify installation**

```bash
cd frontend && node -e "console.log(require('lenis/package.json').version)"
cd frontend && node -e "console.log(require('gsap/package.json').version)"
```

Expected: both versions print without error.

- [ ] **Step 3: Commit lock + manifest**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(article): add lenis and gsap deps"
```

---

### Task 3: Scroll progress library

**Files:**
- Create: `frontend/article/lib/scrollProgress.ts`
- Create: `frontend/article/lib/__tests__/scrollProgress.test.ts`
- Modify: `frontend/vite.article.config.ts` (test setup)
- Modify: `frontend/package.json` (vitest dep)

- [ ] **Step 1: Install vitest + jsdom**

```bash
cd frontend && npm install -D vitest jsdom @testing-library/svelte
```

- [ ] **Step 2: Add vitest config to vite.article.config.ts**

Update `frontend/vite.article.config.ts` to add `test` block:
```ts
// At top:
/// <reference types="vitest" />
// In config:
test: {
  environment: 'jsdom',
  globals: true,
  include: ['article/**/*.test.ts'],
},
```

Add test script to `frontend/package.json`:
```json
"test:article": "vitest --config vite.article.config.ts --run"
```

- [ ] **Step 3: Write failing test**

```ts
// frontend/article/lib/__tests__/scrollProgress.test.ts
import { describe, it, expect, vi } from 'vitest';
import { clamp, mapRange } from '../scrollProgress';

describe('clamp', () => {
  it('clamps to range', () => {
    expect(clamp(-1, 0, 1)).toBe(0);
    expect(clamp(2, 0, 1)).toBe(1);
    expect(clamp(0.5, 0, 1)).toBe(0.5);
  });
});

describe('mapRange', () => {
  it('linearly maps a value across ranges', () => {
    expect(mapRange(50, 0, 100, 0, 1)).toBeCloseTo(0.5);
    expect(mapRange(0, 0, 100, 0, 1)).toBeCloseTo(0);
    expect(mapRange(100, 0, 100, 0, 1)).toBeCloseTo(1);
  });

  it('clamps outside source range by default', () => {
    expect(mapRange(150, 0, 100, 0, 1)).toBeCloseTo(1);
    expect(mapRange(-50, 0, 100, 0, 1)).toBeCloseTo(0);
  });
});
```

- [ ] **Step 4: Run test to verify fail**

Run: `cd frontend && npm run test:article`
Expected: FAIL (module not found)

- [ ] **Step 5: Implement library**

```ts
// frontend/article/lib/scrollProgress.ts
import Lenis from 'lenis';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

let lenis: Lenis | null = null;

export function initSmoothScroll(): () => void {
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReduced) return () => undefined;
  lenis = new Lenis({ smoothWheel: true, lerp: 0.1 });
  const raf = (t: number) => {
    lenis?.raf(t);
    requestAnimationFrame(raf);
  };
  requestAnimationFrame(raf);
  lenis.on('scroll', ScrollTrigger.update);
  return () => {
    lenis?.destroy();
    lenis = null;
  };
}

export interface ScrubOptions {
  start?: string;
  end?: string;
  pin?: boolean;
}

export function scrollScrub(
  triggerEl: Element,
  onUpdate: (t: number) => void,
  opts: ScrubOptions = {},
): () => void {
  const trigger = ScrollTrigger.create({
    trigger: triggerEl,
    start: opts.start ?? 'top top',
    end: opts.end ?? 'bottom top',
    scrub: true,
    pin: opts.pin ?? false,
    onUpdate: (self) => onUpdate(self.progress),
  });
  return () => trigger.kill();
}

export function clamp(x: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, x));
}

export function mapRange(
  x: number, inLo: number, inHi: number, outLo: number, outHi: number,
): number {
  const t = clamp((x - inLo) / (inHi - inLo), 0, 1);
  return outLo + t * (outHi - outLo);
}
```

- [ ] **Step 6: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add frontend/article/lib/ frontend/vite.article.config.ts frontend/package.json frontend/package-lock.json
git commit -m "feat(article): scrollProgress lib with Lenis init and scrub helper"
```

---

### Task 4: Typed data loaders

**Files:**
- Create: `frontend/article/lib/data.ts`
- Create: `frontend/article/lib/types.ts`
- Create: `frontend/article/lib/__tests__/data.test.ts`
- Create: `frontend/article/lib/__tests__/fixtures/summary.json`

- [ ] **Step 1: Write types matching Plan 1 Pydantic models**

```ts
// frontend/article/lib/types.ts
export interface TrainingMetrics {
  total_timesteps: number;
  explained_variance: number;
  entropy_loss: number;
  value_loss: number;
  clip_fraction: number;
}

export interface BenchmarkResult {
  opponents: string[];
  win_rates: number[];
  games: number;
}

export interface BatchResult {
  id: string;
  stage: number;
  opponents: string[];
  episodes: number;
  lr: number;
  result: TrainingMetrics;
  benchmarks: BenchmarkResult[];
  narrative: string;
}

export interface RunSummary {
  title: string;
  batches: BatchResult[];
}

export interface RunIndexEntry {
  id: string;
  title: string;
  default: boolean;
}

export interface RunIndex {
  runs: RunIndexEntry[];
}

export interface CurvesPerBatch {
  id: string;
  total_timesteps: number;
  explained_variance: number;
  entropy_loss: number;
  value_loss: number;
}

export interface Curves {
  batches: CurvesPerBatch[];
}

export interface NetworkSpec {
  hidden_size: number;
  num_layers: number;
  input_size: number;
  output_size: number;
}

export interface TurnRecord {
  turn: number;
  player: string;
  observation: number[];
  action: number;
  action_desc: string;
  value: number;
  policy_top_k: { action: number; prob: number }[];
}

export interface Replay {
  id: string;
  agent_batch: string;
  opponents: string[];
  turns: TurnRecord[];
  winner: string;
  rounds: number;
}
```

- [ ] **Step 2: Add fixture**

```json
// frontend/article/lib/__tests__/fixtures/summary.json
{
  "title": "Test run",
  "batches": [
    {
      "id": "v1",
      "stage": 1,
      "opponents": ["random"],
      "episodes": 200000,
      "lr": 0.0001,
      "result": {
        "total_timesteps": 200000, "explained_variance": -0.1,
        "entropy_loss": -1.8, "value_loss": 0.04, "clip_fraction": 0.3
      },
      "benchmarks": [],
      "narrative": "test"
    }
  ]
}
```

- [ ] **Step 3: Write failing test**

```ts
// frontend/article/lib/__tests__/data.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { loadRunSummary } from '../data';
import fixture from './fixtures/summary.json';

describe('loadRunSummary', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => fixture,
    }) as unknown as typeof fetch;
  });

  it('fetches and validates run summary', async () => {
    const summary = await loadRunSummary('v1-to-v7');
    expect(summary.title).toBe('Test run');
    expect(summary.batches[0].id).toBe('v1');
  });

  it('throws on missing required field', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ batches: [] }),
    }) as unknown as typeof fetch;
    await expect(loadRunSummary('x')).rejects.toThrow(/title/);
  });
});
```

- [ ] **Step 4: Run test to verify fail**

Run: `cd frontend && npm run test:article`
Expected: FAIL (module not found)

- [ ] **Step 5: Implement loaders**

```ts
// frontend/article/lib/data.ts
import type {
  RunSummary, RunIndex, Curves, NetworkSpec, Replay,
} from './types';

function validateRunSummary(x: unknown): RunSummary {
  if (!x || typeof x !== 'object') throw new Error('summary not an object');
  const o = x as Record<string, unknown>;
  if (typeof o.title !== 'string') throw new Error('summary.title missing');
  if (!Array.isArray(o.batches)) throw new Error('summary.batches missing');
  return o as unknown as RunSummary;
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return (await res.json()) as T;
}

export async function loadRunIndex(): Promise<RunIndex> {
  return fetchJson<RunIndex>('/runs/index.json');
}

export async function loadRunSummary(runId: string): Promise<RunSummary> {
  const raw = await fetchJson<unknown>(`/runs/${runId}/summary.json`);
  return validateRunSummary(raw);
}

export async function loadCurves(runId: string): Promise<Curves> {
  return fetchJson<Curves>(`/runs/${runId}/curves.json`);
}

export async function loadNetworkSpec(runId: string): Promise<NetworkSpec> {
  return fetchJson<NetworkSpec>(`/runs/${runId}/network.json`);
}

export async function loadReplay(runId: string, replayId: string): Promise<Replay> {
  return fetchJson<Replay>(`/runs/${runId}/replays/${replayId}.json`);
}
```

- [ ] **Step 6: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: all tests pass (clamp/mapRange 4 + data 2 = 6)

- [ ] **Step 7: Commit**

```bash
git add frontend/article/lib/
git commit -m "feat(article): typed data loaders with runtime validation"
```

---

### Task 5: Section component skeletons

**Files:**
- Create: `frontend/article/sections/Hero.svelte`
- Create: `frontend/article/sections/Game101.svelte`
- Create: `frontend/article/sections/RL101.svelte`
- Create: `frontend/article/sections/NetworkAnatomy.svelte`
- Create: `frontend/article/sections/TrainingStory.svelte`
- Create: `frontend/article/sections/NetworkInDepth.svelte`
- Create: `frontend/article/sections/AgentInAction.svelte`
- Create: `frontend/article/sections/Closing.svelte`

- [ ] **Step 1: Write 8 skeleton components**

Each file follows the same pattern. Example for Hero:

```svelte
<!-- frontend/article/sections/Hero.svelte -->
<section class="hero">
  <slot />
</section>

<style>
  .hero {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4rem 1.5rem;
  }
</style>
```

Repeat the same structure with semantic class names (`.game101`, `.rl101`, `.network-anatomy`, `.training-story`, `.network-in-depth`, `.agent-in-action`, `.closing`) for the other 7 files. Each is a `<section>` with a `<slot />` and a minimum height of `100vh` (sections 5/6/7) or `auto` (sections 1/2/3/4/8).

- [ ] **Step 2: Verify nothing breaks**

```bash
cd frontend && npm run build:article
```

Expected: build succeeds (sections aren't yet imported anywhere — pure smoke test).

- [ ] **Step 3: Commit**

```bash
git add frontend/article/sections/
git commit -m "feat(article): create empty section component skeletons"
```

---

### Task 6: Wire Article.svelte to the 8 sections + smooth scroll

**Files:**
- Modify: `frontend/article/Article.svelte`
- Create: `frontend/article/style.css`

- [ ] **Step 1: Add global style**

```css
/* frontend/article/style.css */
:root {
  --bg: #0a0d12;
  --fg: #f3f1ec;
  --accent: #ff3d8a;
  --muted: #9aa0a6;
}

* { box-sizing: border-box; }

html, body {
  margin: 0; padding: 0;
  background: var(--bg);
  color: var(--fg);
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

a { color: var(--accent); }
```

- [ ] **Step 2: Wire Article.svelte**

```svelte
<!-- frontend/article/Article.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { initSmoothScroll } from './lib/scrollProgress';
  import Hero from './sections/Hero.svelte';
  import Game101 from './sections/Game101.svelte';
  import RL101 from './sections/RL101.svelte';
  import NetworkAnatomy from './sections/NetworkAnatomy.svelte';
  import TrainingStory from './sections/TrainingStory.svelte';
  import NetworkInDepth from './sections/NetworkInDepth.svelte';
  import AgentInAction from './sections/AgentInAction.svelte';
  import Closing from './sections/Closing.svelte';

  let cleanup: () => void = () => undefined;

  onMount(() => {
    cleanup = initSmoothScroll();
  });
  onDestroy(() => cleanup());
</script>

<Hero />
<Game101 />
<RL101 />
<NetworkAnatomy />
<TrainingStory />
<NetworkInDepth />
<AgentInAction />
<Closing />
```

- [ ] **Step 3: Verify**

```bash
cd frontend && npm run dev:article
```

Open http://localhost:5174 and scroll. Expected: smooth wheel-based scrolling, 8 empty sections.

- [ ] **Step 4: Commit**

```bash
git add frontend/article/Article.svelte frontend/article/style.css
git commit -m "feat(article): wire 8 sections + Lenis smooth scroll"
```

---

### Task 7: Hero section content

**Files:**
- Modify: `frontend/article/sections/Hero.svelte`

- [ ] **Step 1: Implement Hero**

```svelte
<!-- frontend/article/sections/Hero.svelte -->
<section class="hero">
  <div class="content">
    <h1>We taught a neural network<br />to play Splendor.</h1>
    <p class="subtitle">
      One million games. Seven generations. Here's how the agent learned —
      and how we know it really did.
    </p>
    <div class="scroll-hint">Scroll to begin</div>
  </div>
</section>

<style>
  .hero {
    min-height: 100vh;
    display: grid;
    place-items: center;
    text-align: center;
    padding: 4rem 1.5rem;
  }
  .content { max-width: 56rem; }
  h1 {
    font-size: clamp(2.5rem, 7vw, 5rem);
    font-weight: 700;
    line-height: 1.05;
    letter-spacing: -0.02em;
    margin: 0 0 1.5rem;
  }
  .subtitle {
    color: var(--muted);
    font-size: clamp(1.1rem, 2vw, 1.35rem);
    max-width: 38rem;
    margin: 0 auto;
  }
  .scroll-hint {
    margin-top: 4rem;
    font-size: 0.8rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--muted);
    opacity: 0.7;
  }
</style>
```

- [ ] **Step 2: Verify visually in browser**

Run `npm run dev:article`, open the page. Expected: centred headline, subtitle, scroll-hint at bottom of viewport.

- [ ] **Step 3: Commit**

```bash
git add frontend/article/sections/Hero.svelte
git commit -m "feat(article): hero section with headline and subtitle"
```

---

### Task 8: RL101 section content

**Files:**
- Modify: `frontend/article/sections/RL101.svelte`

- [ ] **Step 1: Implement RL101**

```svelte
<!-- frontend/article/sections/RL101.svelte -->
<section class="rl101">
  <div class="prose">
    <h2>How a network learns by playing</h2>
    <p>
      Reinforcement learning is what happens when an agent plays a game,
      tries things, and gets a single number back at the end — did it win?
      The agent uses that single number to nudge every decision it made
      slightly more toward the kind of decision that wins.
    </p>

    <div class="concept-grid">
      <div class="concept">
        <h3>Observation</h3>
        <p>What the agent sees. For us: a vector of every card on the
          board, every token in every pile, and every player's hand.</p>
      </div>
      <div class="concept">
        <h3>Action</h3>
        <p>What the agent does. One of fifty possible moves: take tokens,
          reserve a card, catch a card.</p>
      </div>
      <div class="concept">
        <h3>Reward</h3>
        <p>The signal it learns from. We give +1 for winning the game and
          0 for everything else. That's it.</p>
      </div>
      <div class="concept">
        <h3>Policy</h3>
        <p>The agent's strategy — a function from observation to a
          probability over each action.</p>
      </div>
      <div class="concept">
        <h3>Value</h3>
        <p>The agent's gut feel — a single number that estimates "from
          this position, how likely am I to win?"</p>
      </div>
    </div>

    <p>
      Every action the agent took during a winning game becomes a tiny
      vote toward doing that action again. Every action during a losing
      game becomes a tiny vote against. Repeated a million times, the
      votes accumulate into a strategy.
    </p>
  </div>
</section>

<style>
  .rl101 {
    padding: 8rem 1.5rem;
  }
  .prose {
    max-width: 60rem;
    margin: 0 auto;
  }
  h2 {
    font-size: clamp(2rem, 4vw, 3rem);
    margin-bottom: 2rem;
    letter-spacing: -0.02em;
  }
  p {
    font-size: 1.15rem;
    color: #d6d3cb;
    margin: 0 0 1.5rem;
  }
  .concept-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
    gap: 1.5rem;
    margin: 3rem 0;
  }
  .concept {
    padding: 1.5rem;
    border-left: 2px solid var(--accent);
    background: rgba(255,255,255,0.02);
  }
  .concept h3 {
    margin: 0 0 0.75rem;
    font-size: 1.1rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent);
  }
  .concept p { font-size: 0.95rem; margin: 0; }
</style>
```

- [ ] **Step 2: Verify in browser**

Expected: section visible after Hero with five concept cards.

- [ ] **Step 3: Commit**

```bash
git add frontend/article/sections/RL101.svelte
git commit -m "feat(article): RL101 section with five concept cards"
```

---

### Task 9: Closing section content

**Files:**
- Modify: `frontend/article/sections/Closing.svelte`

- [ ] **Step 1: Implement Closing**

```svelte
<!-- frontend/article/sections/Closing.svelte -->
<section class="closing">
  <div class="prose">
    <h2>Try it yourself.</h2>
    <p>
      The trained agent is playable in your browser. The training scripts,
      benchmarks, and source code are open.
    </p>
    <ul class="links">
      <li><a href="https://geo-dude.com/splendor">Play against the agent</a></li>
      <li><a href="https://github.com/your-org/splendor">Source on GitHub</a></li>
      <li><a href="https://github.com/your-org/splendor/blob/main/training_log.txt">Full training log</a></li>
    </ul>
    <p class="credits">
      Built with Svelte, GSAP, and Three.js. The neural network was trained
      using <a href="https://github.com/Stable-Baselines-Team/stable-baselines3-contrib">MaskablePPO</a>.
      Inspired by Bartosz Ciechanowski and Tensorflow Playground.
    </p>
  </div>
</section>

<style>
  .closing {
    padding: 12rem 1.5rem;
    text-align: center;
  }
  .prose {
    max-width: 48rem;
    margin: 0 auto;
  }
  h2 { font-size: clamp(2.5rem, 5vw, 4rem); margin: 0 0 2rem; }
  .links {
    list-style: none;
    padding: 0;
    margin: 3rem 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .links a {
    font-size: 1.2rem;
    text-decoration: none;
    border-bottom: 1px solid currentColor;
  }
  .credits { font-size: 0.9rem; color: var(--muted); margin-top: 4rem; }
</style>
```

- [ ] **Step 2: Verify visually**

Expected: closing section at end of page.

- [ ] **Step 3: Commit**

```bash
git add frontend/article/sections/Closing.svelte
git commit -m "feat(article): closing section with links and credits"
```

---

### Task 10: Mini-board reuse from existing components (Game101)

**Files:**
- Modify: `frontend/article/sections/Game101.svelte`

The existing `frontend/src/components/Board.svelte` requires a `gameStore` shape. For the article we don't connect to a live game — we render a static snapshot.

- [ ] **Step 1: Add a static snapshot fixture**

Create `frontend/article/data/snapshots/early-board.json`:

```json
{
  "common_revealed": [], "uncommon_revealed": [], "rare_revealed": [],
  "epic_revealed": [], "legendary_revealed": [],
  "tokens": [],
  "players": []
}
```

(Real snapshot content will be wired in Plan 4 when GameReplayPlayer is built. For now, Game101 ships placeholder text and lays out the structure.)

- [ ] **Step 2: Implement Game101 with placeholder**

```svelte
<!-- frontend/article/sections/Game101.svelte -->
<section class="game101">
  <div class="prose">
    <h2>Splendor in 90 seconds</h2>
    <p>
      Players take turns. Each turn you do one of three things: grab
      tokens, reserve a card for later, or buy a card you can afford.
      Cards give you points and bonuses that make future cards cheaper.
      The first player to fifteen points wins the round.
    </p>
    <p class="aside">
      This article is about a variant called Pokémon Splendor — same rules,
      but with Pokémon cards and a tier system that rewards building
      evolution chains.
    </p>
  </div>
  <!-- Mini board mockup placeholder. Replaced in Plan 4 with GameReplayPlayer. -->
  <aside class="board-placeholder">
    <span>Mini board renders here in Plan 4</span>
  </aside>
</section>

<style>
  .game101 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4rem;
    padding: 8rem 4rem;
    max-width: 90rem;
    margin: 0 auto;
    align-items: center;
  }
  .prose h2 {
    font-size: clamp(2rem, 4vw, 3rem);
    margin: 0 0 1.5rem;
    letter-spacing: -0.02em;
  }
  .prose p { font-size: 1.15rem; color: #d6d3cb; }
  .aside { color: var(--muted); font-size: 1rem; }
  .board-placeholder {
    aspect-ratio: 1;
    border: 1px dashed rgba(255,255,255,0.1);
    display: grid;
    place-items: center;
    color: var(--muted);
    font-size: 0.9rem;
  }
  @media (max-width: 800px) {
    .game101 { grid-template-columns: 1fr; }
  }
</style>
```

- [ ] **Step 3: Verify visually**

Expected: side-by-side layout on desktop, board placeholder shown.

- [ ] **Step 4: Commit**

```bash
git add frontend/article/sections/Game101.svelte frontend/article/data/snapshots/
git commit -m "feat(article): Game101 section with prose + board placeholder"
```

---

### Task 11: Smoke test the build

**Files:** *(none)*

- [ ] **Step 1: Build**

```bash
cd frontend && npm run build:article
```

Expected: produces `frontend/dist-article/index.html` and bundled JS/CSS.

- [ ] **Step 2: Verify static serve works**

```bash
cd frontend/dist-article && python3 -m http.server 5180 &
SERVE_PID=$!
sleep 1
curl -sS http://localhost:5180/ | grep -q "How we taught" && echo OK
kill $SERVE_PID
```

Expected: prints `OK`.

- [ ] **Step 3: Commit**

```bash
git add frontend/dist-article/
git commit -m "build(article): first successful static build"
```

(If `dist-article` is in `.gitignore`, skip the add — the build artifact doesn't need to be tracked. The commit is optional.)

---

## Done

After this plan:
- `npm run dev:article` serves the article at http://localhost:5174 with smooth Lenis scroll.
- `npm run build:article` produces a static bundle at `frontend/dist-article/`.
- Sections 1 (Hero), 3 (RL101), and 8 (Closing) have prose content; Section 2 (Game101) has structural prose with a placeholder for the live board.
- Sections 4–7 are empty placeholders ready for Plans 3, 4, 5.
- Data loaders (`loadRunSummary`, `loadCurves`, `loadNetworkSpec`, `loadReplay`) are typed and tested.
- Scroll choreography helpers (`scrollScrub`, `clamp`, `mapRange`) are ready for use.
