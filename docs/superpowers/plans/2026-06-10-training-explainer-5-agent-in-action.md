# Training Explainer Plan 5: Agent In Action + Polish

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Section 7 (Agent In Action), where the game replay and the WebGL network are coupled by scroll position with live activations from ONNX. Then add the hero moments (particle assembly, 3D unfurl), wire activation feeding for both viz implementations, and set the performance budget gate.

**Architecture:** A new `lib/onnxRunner.ts` wraps `onnxruntime-web` to run a forward pass per turn and return `LayerActivations`. Section 7 holds a sticky two-column layout with `GameReplayPlayer` on the left and `WebGLNetworkViz` on the right; scroll progress drives both. `viz/effects/` houses optional post-processing (Three.js bloom). Hero particle field lives in `viz/HeroParticles.ts` and mounts behind the Hero section text. Performance budget is enforced via a CI script that fails the build on bundle-size regression.

**Tech Stack:** onnxruntime-web, three.js, postprocessing (UnrealBloomPass equivalent), Vite plugin for bundle analysis.

---

### Task 1: ONNX runtime wrapper

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/article/lib/onnxRunner.ts`
- Create: `frontend/article/lib/__tests__/onnxRunner.test.ts`

- [ ] **Step 1: Install dependency**

```bash
cd frontend && npm install onnxruntime-web
```

- [ ] **Step 2: Write failing test (smoke)**

```ts
// frontend/article/lib/__tests__/onnxRunner.test.ts
import { describe, it, expect } from 'vitest';
import { extractActivations } from '../onnxRunner';

describe('extractActivations', () => {
  it('packs ORT output map into LayerActivations', () => {
    const fakeOut = {
      policy_logits: { data: new Float32Array([1, 2, 3, 4]) },
      value: { data: new Float32Array([0.5]) },
      hidden_0: { data: new Float32Array([0.1, 0.2]) },
      hidden_1: { data: new Float32Array([0.3, 0.4]) },
    };
    const acts = extractActivations(fakeOut as any);
    expect(acts.layers).toHaveLength(2);
    expect(acts.layers[0]).toEqual(new Float32Array([0.1, 0.2]));
    expect(acts.value).toBeCloseTo(0.5);
    expect(acts.policy.length).toBe(4);
  });
});
```

- [ ] **Step 3: Run test to verify fail**

Run: `cd frontend && npm run test:article`
Expected: FAIL

- [ ] **Step 4: Implement runner**

```ts
// frontend/article/lib/onnxRunner.ts
import type { LayerActivations } from '../viz/types';

let session: any | null = null;
let loading: Promise<void> | null = null;

export async function loadOnnxNetwork(runId: string): Promise<void> {
  if (session) return;
  if (loading) return loading;
  loading = (async () => {
    const ort = await import('onnxruntime-web');
    session = await ort.InferenceSession.create(`/runs/${runId}/network.onnx`, {
      executionProviders: ['wasm'],
    });
  })();
  return loading;
}

function softmax(logits: Float32Array): Float32Array {
  let max = -Infinity;
  for (let i = 0; i < logits.length; i++) if (logits[i] > max) max = logits[i];
  let sum = 0;
  const out = new Float32Array(logits.length);
  for (let i = 0; i < logits.length; i++) {
    out[i] = Math.exp(logits[i] - max);
    sum += out[i];
  }
  for (let i = 0; i < out.length; i++) out[i] /= sum;
  return out;
}

export function extractActivations(
  outputs: Record<string, { data: Float32Array }>,
): LayerActivations {
  const layers: Float32Array[] = [];
  const keys = Object.keys(outputs)
    .filter((k) => k.startsWith('hidden_'))
    .sort();
  for (const k of keys) layers.push(outputs[k].data);
  const policy = softmax(outputs.policy_logits.data);
  const value = outputs.value.data[0];
  return { layers, policy, value };
}

export async function runNetwork(
  observation: Float32Array,
): Promise<LayerActivations> {
  if (!session) throw new Error('ONNX network not loaded');
  const ort = await import('onnxruntime-web');
  const tensor = new ort.Tensor('float32', observation, [1, observation.length]);
  const out = await session.run({ observation: tensor });
  return extractActivations(out);
}
```

- [ ] **Step 5: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: passing

- [ ] **Step 6: Commit**

```bash
git add frontend/article/lib/onnxRunner.ts frontend/article/lib/__tests__/onnxRunner.test.ts frontend/package.json frontend/package-lock.json
git commit -m "feat(article): onnxRunner wraps onnxruntime-web for activation extraction"
```

---

### Task 2: Wire Canvas2D activations from a real Float32Array

The shape of `setActivations` was stubbed in Plan 3. Activation-driven colouring is already there for Canvas2D; this task wires the `LayerActivations` from `onnxRunner` into the call site.

**Files:**
- Modify: `frontend/article/viz/Canvas2DNetworkViz.ts`

- [ ] **Step 1: Add policy/value uses in `setActivations`**

The current `setActivations` colours by node activation. Extend it to also reflect the policy distribution on the output column (top row already maps to `layerOutputs.policy`).

Already covered in Plan 3 Task 4 — verify the code paths concrete `LayerActivations` (layers + policy + value) reach the right columns and proceed without re-implementation. Just write a regression test:

```ts
// Append to frontend/article/viz/__tests__/Canvas2DNetworkViz.test.ts
import { describe, it, expect } from 'vitest';
describe('Canvas2DNetworkViz setActivations', () => {
  it('does not throw on real-shaped activations', () => {
    const viz = new Canvas2DNetworkViz();
    const container = document.createElement('div');
    Object.defineProperty(container, 'clientWidth', { value: 400 });
    Object.defineProperty(container, 'clientHeight', { value: 200 });
    document.body.appendChild(container);
    viz.mount(container, {
      inputSize: 421, hiddenLayers: [256, 256, 256], outputSize: 50,
    });
    expect(() => viz.setActivations(
      new Float32Array(421),
      {
        layers: [new Float32Array(256), new Float32Array(256), new Float32Array(256)],
        policy: new Float32Array(50),
        value: 0.5,
      },
    )).not.toThrow();
    viz.dispose();
  });
});
```

- [ ] **Step 2: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: passing

- [ ] **Step 3: Commit**

```bash
git add frontend/article/viz/__tests__/Canvas2DNetworkViz.test.ts
git commit -m "test(article): Canvas2D handles realistic activation shapes"
```

---

### Task 3: Wire WebGL activations into instance colours

**Files:**
- Modify: `frontend/article/viz/WebGLNetworkViz.ts`

- [ ] **Step 1: Switch InstancedMesh to per-instance colour**

Replace the material/mesh setup in `buildLayers`:

```ts
// Replace the sphere/material setup near the top of buildLayers:
const sphere = new THREE.SphereGeometry(0.05, 12, 12);
const material = new THREE.MeshBasicMaterial({
  vertexColors: false,
});

// Inside the layerSizes.forEach loop, after creating the InstancedMesh:
const colors = new Float32Array(visible * 3);
for (let i = 0; i < visible; i++) {
  colors[i * 3] = 1.0;       // R
  colors[i * 3 + 1] = 0.24;  // G
  colors[i * 3 + 2] = 0.54;  // B
}
mesh.instanceColor = new THREE.InstancedBufferAttribute(colors, 3);
(mesh.material as THREE.MeshBasicMaterial).vertexColors = true;
```

Then implement `setActivations`:

```ts
setActivations(obs: Float32Array, layerOutputs: LayerActivations): void {
  if (!this.network) return;
  const sources: Float32Array[] = [obs, ...layerOutputs.layers, layerOutputs.policy];
  for (let li = 0; li < this.nodeMeshes.length; li++) {
    const mesh = this.nodeMeshes[li];
    const colorAttr = mesh.instanceColor;
    if (!colorAttr) continue;
    const src = sources[li];
    if (!src) continue;
    const count = mesh.count;
    for (let i = 0; i < count; i++) {
      const idx = Math.floor((i / count) * src.length);
      const a = Math.max(0, Math.min(1, src[idx]));
      colorAttr.setXYZ(i, 1.0, 0.24 + a * 0.6, 0.54 + a * 0.3);
    }
    colorAttr.needsUpdate = true;
  }
}
```

- [ ] **Step 2: Verify visually**

Browser: `npm run dev:article`. Section 6 nodes should remain pink at first. After Section 7 wires real activations (next task), nodes should brighten variably.

- [ ] **Step 3: Commit**

```bash
git add frontend/article/viz/WebGLNetworkViz.ts
git commit -m "feat(article): WebGLNetworkViz wires per-instance activation colour"
```

---

### Task 4: AgentInAction section

**Files:**
- Modify: `frontend/article/sections/AgentInAction.svelte`

- [ ] **Step 1: Implement coupled section**

```svelte
<!-- frontend/article/sections/AgentInAction.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { scrollScrub } from '../lib/scrollProgress';
  import { loadReplay, loadNetworkSpec } from '../lib/data';
  import { loadReplaySnapshots, type ReplaySnapshots } from '../replay/snapshot';
  import { loadOnnxNetwork, runNetwork } from '../lib/onnxRunner';
  import { createNetworkViz } from '../viz/createNetworkViz';
  import GameReplayPlayer from '../replay/GameReplayPlayer.svelte';
  import type { NetworkVisualization } from '../viz/NetworkVisualization';
  import type { Replay } from '../lib/types';

  let stickyEl: HTMLElement;
  let vizContainer: HTMLElement;
  let viz: NetworkVisualization | null = null;
  let cleanup: () => void = () => undefined;

  let replay: Replay | null = null;
  let snapshots: ReplaySnapshots | null = null;
  let currentTurn = 0;
  let topActions: { action: number; prob: number; desc: string }[] = [];

  $: currentSnapshot = snapshots?.turns[currentTurn]?.snapshot ?? snapshots?.initial;
  $: currentReplayTurn = replay?.turns[currentTurn];

  onMount(async () => {
    const spec = await loadNetworkSpec('v1-to-v7');
    viz = createNetworkViz('webgl');
    viz.mount(vizContainer, {
      inputSize: spec.input_size,
      hiddenLayers: Array(spec.num_layers).fill(spec.hidden_size),
      outputSize: spec.output_size,
    });
    [replay, snapshots] = await Promise.all([
      loadReplay('v1-to-v7', 'v6-seed42'),
      loadReplaySnapshots('v6-seed42'),
    ]);
    await loadOnnxNetwork('v1-to-v7');

    cleanup = scrollScrub(stickyEl, async (t) => {
      if (!replay || !snapshots) return;
      const idx = Math.min(
        replay.turns.length - 1,
        Math.floor(t * replay.turns.length),
      );
      if (idx !== currentTurn) {
        currentTurn = idx;
        const turn = replay.turns[idx];
        const obs = new Float32Array(turn.observation);
        try {
          const acts = await runNetwork(obs);
          viz?.setActivations(obs, acts);
        } catch (e) {
          console.warn('runNetwork failed', e);
        }
        viz?.setHighlightedAction(turn.action);
        topActions = turn.policy_top_k.map((tk) => ({
          action: tk.action,
          prob: tk.prob,
          desc: turn.action === tk.action ? turn.action_desc : `action ${tk.action}`,
        }));
      }
    }, { pin: true, start: 'top top', end: '+=400%' });
  });

  onDestroy(() => {
    cleanup();
    viz?.dispose();
  });
</script>

<section class="agent-in-action" bind:this={stickyEl}>
  <div class="sticky-frame">
    <div class="left">
      {#if currentSnapshot}
        <GameReplayPlayer
          snapshot={currentSnapshot}
          description={snapshots?.turns[currentTurn]?.description ?? ''} />
      {/if}
      {#if currentReplayTurn}
        <div class="value">
          <span class="label">Network's confidence:</span>
          <span class="bar">
            <span class="bar-fill" style="width: {currentReplayTurn.value * 100}%"></span>
          </span>
          <span class="value-num">{Math.round(currentReplayTurn.value * 100)}%</span>
        </div>
      {/if}
    </div>
    <div class="right">
      <div class="viz" bind:this={vizContainer}></div>
      <div class="top-actions">
        <h4>Top action probabilities</h4>
        {#each topActions as ta}
          <div class="action">
            <span class="desc">{ta.desc}</span>
            <span class="prob">
              <span class="prob-fill" style="width: {ta.prob * 100}%"></span>
              {Math.round(ta.prob * 100)}%
            </span>
          </div>
        {/each}
      </div>
    </div>
  </div>
</section>

<style>
  .agent-in-action {
    height: 500vh;
    position: relative;
  }
  .sticky-frame {
    position: sticky;
    top: 0;
    height: 100vh;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    padding: 2rem;
  }
  .left, .right { display: flex; flex-direction: column; gap: 1rem; }
  .viz { flex: 1; min-height: 0; }
  .value { display: grid; grid-template-columns: auto 1fr auto; gap: 0.75rem; align-items: center; font-size: 0.9rem; }
  .label { color: var(--muted); }
  .bar { background: rgba(255,255,255,0.06); height: 0.5rem; border-radius: 3px; overflow: hidden; }
  .bar-fill { display: block; background: var(--accent); height: 100%; }
  .value-num { font-variant-numeric: tabular-nums; }
  .top-actions h4 {
    font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--muted); margin: 0 0 0.5rem;
  }
  .action {
    display: grid;
    grid-template-columns: 1fr 8rem;
    gap: 0.75rem;
    align-items: center;
    font-size: 0.85rem;
    padding: 0.4rem 0;
  }
  .desc { color: #d6d3cb; }
  .prob {
    position: relative;
    background: rgba(255,255,255,0.06);
    border-radius: 3px;
    padding: 0.2rem 0.5rem;
    text-align: right;
    font-size: 0.75rem;
    overflow: hidden;
  }
  .prob-fill {
    position: absolute;
    top: 0; left: 0; bottom: 0;
    background: rgba(255,61,138,0.4);
  }
</style>
```

- [ ] **Step 2: Verify visually**

Browser: scroll into section 7. Expected: replay on left advances turn-by-turn, network on right lights up with activations, top-k action bars update.

- [ ] **Step 3: Commit**

```bash
git add frontend/article/sections/AgentInAction.svelte
git commit -m "feat(article): AgentInAction section with coupled replay + live network"
```

---

### Task 5: Hero particle assembly

**Files:**
- Create: `frontend/article/viz/HeroParticles.ts`
- Modify: `frontend/article/sections/Hero.svelte`

- [ ] **Step 1: Implement particle field**

```ts
// frontend/article/viz/HeroParticles.ts
import * as THREE from 'three';

export class HeroParticles {
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private points: THREE.Points;
  private targetPositions: Float32Array;
  private startPositions: Float32Array;
  private startTime = performance.now();
  private rafHandle = 0;
  private container: HTMLElement;
  private positions: Float32Array;

  constructor(container: HTMLElement, count: number = 4000) {
    this.container = container;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    this.renderer.setClearColor(0x000000, 0);
    container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(
      45, container.clientWidth / container.clientHeight, 0.1, 100,
    );
    this.camera.position.set(0, 0, 6);

    this.positions = new Float32Array(count * 3);
    this.startPositions = new Float32Array(count * 3);
    this.targetPositions = new Float32Array(count * 3);

    for (let i = 0; i < count; i++) {
      // Random start: scattered across a sphere of radius 8
      const r = 8 * Math.cbrt(Math.random());
      const phi = Math.acos(2 * Math.random() - 1);
      const theta = 2 * Math.PI * Math.random();
      const sx = r * Math.sin(phi) * Math.cos(theta);
      const sy = r * Math.sin(phi) * Math.sin(theta);
      const sz = r * Math.cos(phi);
      this.startPositions[i * 3] = sx;
      this.startPositions[i * 3 + 1] = sy;
      this.startPositions[i * 3 + 2] = sz;
      // Target: a 4×5 grid of card slots
      const col = i % 5;
      const row = Math.floor((i / 5) % 4);
      this.targetPositions[i * 3] = (col - 2) * 1.0 + (Math.random() - 0.5) * 0.2;
      this.targetPositions[i * 3 + 1] = (1.5 - row) * 0.9 + (Math.random() - 0.5) * 0.15;
      this.targetPositions[i * 3 + 2] = (Math.random() - 0.5) * 0.3;
      this.positions[i * 3] = sx;
      this.positions[i * 3 + 1] = sy;
      this.positions[i * 3 + 2] = sz;
    }

    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(this.positions, 3));
    const mat = new THREE.PointsMaterial({
      color: 0xff3d8a, size: 0.03, transparent: true, opacity: 0.85,
    });
    this.points = new THREE.Points(geom, mat);
    this.scene.add(this.points);

    this.startTime = performance.now();
    this.loop();
  }

  private loop = () => {
    const elapsed = (performance.now() - this.startTime) / 1000;
    const t = Math.min(1, elapsed / 4.0);
    const eased = 1 - Math.pow(1 - t, 3);
    const count = this.positions.length / 3;
    for (let i = 0; i < count; i++) {
      const k = i * 3;
      this.positions[k] = this.startPositions[k] * (1 - eased) + this.targetPositions[k] * eased;
      this.positions[k + 1] = this.startPositions[k + 1] * (1 - eased) + this.targetPositions[k + 1] * eased;
      this.positions[k + 2] = this.startPositions[k + 2] * (1 - eased) + this.targetPositions[k + 2] * eased;
    }
    (this.points.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    this.renderer.render(this.scene, this.camera);
    this.rafHandle = requestAnimationFrame(this.loop);
  };

  dispose(): void {
    cancelAnimationFrame(this.rafHandle);
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}
```

- [ ] **Step 2: Mount in Hero**

```svelte
<!-- frontend/article/sections/Hero.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { HeroParticles } from '../viz/HeroParticles';

  let particleContainer: HTMLElement;
  let particles: HeroParticles | null = null;

  onMount(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduced) {
      particles = new HeroParticles(particleContainer);
    }
  });
  onDestroy(() => particles?.dispose());
</script>

<section class="hero">
  <div class="particles" bind:this={particleContainer}></div>
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
    position: relative;
    display: grid;
    place-items: center;
    text-align: center;
    padding: 4rem 1.5rem;
  }
  .particles {
    position: absolute; inset: 0;
    z-index: 0;
    opacity: 0.65;
  }
  .content { position: relative; z-index: 1; max-width: 56rem; }
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

- [ ] **Step 3: Verify visually**

Browser: load page. Expected: 4000 pink particles converge from a sphere into a 4×5 grid behind the headline over 4 seconds.

- [ ] **Step 4: Commit**

```bash
git add frontend/article/viz/HeroParticles.ts frontend/article/sections/Hero.svelte
git commit -m "feat(article): hero particle assembly behind headline"
```

---

### Task 6: 3D unfurl on entering Section 6

**Files:**
- Modify: `frontend/article/viz/WebGLNetworkViz.ts`

- [ ] **Step 1: Use scroll progress to lift Z**

In `setScrollProgress`, instead of just dolly-x, animate the z-spread of layers based on scroll progress 0→0.3 ("unfurl phase"):

```ts
setScrollProgress(t: number): void {
  this.scrollT = t;
  if (!this.camera) return;
  const dollyT = Math.max(0, (t - 0.3)) / 0.7;
  this.camera.position.x = (dollyT - 0.5) * 6;
  const unfurl = Math.min(1, t / 0.3);
  this.nodeMeshes.forEach((mesh, li) => {
    const targetZ = (li - (this.nodeMeshes.length - 1) / 2) * 0.0
      + (1 - unfurl) * 0;
    // Slide each layer along Z based on unfurl.
    mesh.position.z = (li - (this.nodeMeshes.length - 1) / 2) * unfurl * 1.5;
  });
  this.edgeLines.forEach((line, li) => {
    line.position.z = (li - (this.edgeLines.length - 1) / 2) * unfurl * 1.5;
  });
  this.camera.lookAt(0, 0, 0);
}
```

- [ ] **Step 2: Verify visually**

Scroll into Section 6. Expected: layers start coplanar then separate into 3D as scroll progresses through the first third.

- [ ] **Step 3: Commit**

```bash
git add frontend/article/viz/WebGLNetworkViz.ts
git commit -m "feat(article): WebGLNetworkViz 3D unfurl driven by scroll progress"
```

---

### Task 7: Bundle analyser + size gate

**Files:**
- Modify: `frontend/vite.article.config.ts`
- Modify: `frontend/package.json`
- Create: `frontend/scripts/check-bundle-size.mjs`

- [ ] **Step 1: Install analyser**

```bash
cd frontend && npm install -D rollup-plugin-visualizer
```

- [ ] **Step 2: Add visualiser to vite config**

In `frontend/vite.article.config.ts`, import and plug in:

```ts
import { visualizer } from 'rollup-plugin-visualizer';
// ...
plugins: [
  svelte(),
  visualizer({ filename: 'dist-article/stats.html', gzipSize: true }),
],
```

- [ ] **Step 3: Add size gate script**

```mjs
// frontend/scripts/check-bundle-size.mjs
import { readdirSync, statSync } from 'fs';
import { join } from 'path';

const MAX_TOTAL_BYTES = 4 * 1024 * 1024; // 4 MB
const MAX_JS_BYTES = 600 * 1024;          // 600 KB raw (no gzip check here)
const DIST = 'dist-article';

let total = 0;
let js = 0;
const walk = (dir) => {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    const s = statSync(p);
    if (s.isDirectory()) walk(p);
    else {
      total += s.size;
      if (f.endsWith('.js')) js += s.size;
    }
  }
};
walk(DIST);

console.log(`Total: ${(total / 1024).toFixed(1)} KB`);
console.log(`JS:    ${(js / 1024).toFixed(1)} KB`);

if (total > MAX_TOTAL_BYTES) {
  console.error(`Bundle exceeds total budget of ${MAX_TOTAL_BYTES} bytes`);
  process.exit(1);
}
if (js > MAX_JS_BYTES) {
  console.error(`JS exceeds budget of ${MAX_JS_BYTES} bytes`);
  process.exit(1);
}
```

- [ ] **Step 4: Add npm script**

In `frontend/package.json`:
```json
"check-bundle": "node scripts/check-bundle-size.mjs"
```

- [ ] **Step 5: Verify**

```bash
cd frontend && npm run build:article && npm run check-bundle
```

Expected: prints sizes, exits 0 if within budget.

- [ ] **Step 6: Commit**

```bash
git add frontend/vite.article.config.ts frontend/package.json frontend/package-lock.json frontend/scripts/check-bundle-size.mjs
git commit -m "ci(article): bundle size gate (4MB total / 600KB JS)"
```

---

### Task 8: Reduced motion handling

**Files:**
- Modify: `frontend/article/lib/scrollProgress.ts`
- Modify: `frontend/article/sections/AgentInAction.svelte`
- Modify: `frontend/article/sections/TrainingStory.svelte`
- Modify: `frontend/article/sections/NetworkAnatomy.svelte`
- Modify: `frontend/article/sections/NetworkInDepth.svelte`

- [ ] **Step 1: Add `prefersReducedMotion` helper**

In `frontend/article/lib/scrollProgress.ts`, export:

```ts
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
```

- [ ] **Step 2: Replace scrub with section-based reveal in sticky sections**

In `NetworkAnatomy.svelte`, `NetworkInDepth.svelte`, `TrainingStory.svelte`, `AgentInAction.svelte`, wrap the `onMount` scrub init:

```ts
import { prefersReducedMotion } from '../lib/scrollProgress';
// ...
if (prefersReducedMotion()) {
  // Jump directly to the most-interesting state and skip scrubbing.
  viz?.setScrollProgress(0.5);
} else {
  cleanup = scrollScrub(stickyEl, (t) => viz?.setScrollProgress(t), { pin: true, start: 'top top', end: '+=200%' });
}
```

- [ ] **Step 3: Verify**

In Chrome devtools, enable `prefers-reduced-motion`. Reload the article. Expected: smooth scroll disabled, sticky sections don't pin, vizzes show their mid-state.

- [ ] **Step 4: Commit**

```bash
git add frontend/article/lib/scrollProgress.ts frontend/article/sections/
git commit -m "feat(article): respect prefers-reduced-motion in scroll-driven sections"
```

---

### Task 9: Build, deploy verification, README

**Files:**
- Create: `frontend/article/README.md`

- [ ] **Step 1: Write the README**

```markdown
# Pokemon Splendor — Training Explainer

A standalone Svelte article that explains how the Splendor agent was trained.

## Develop

```bash
npm install
npm run dev:article
```

Serves at http://localhost:5174

## Build

```bash
npm run build:article
npm run check-bundle
```

Output: `dist-article/`

## Regenerate data

From repo root:

```bash
uv run python scripts/export_article_data.py \
  --run-id v1-to-v7 --title "First curriculum" \
  --log training_log.txt \
  --narratives scripts/article_export/narratives/v1-to-v7.yaml \
  --out frontend/article/data/runs/ --default

for v in v1 v3 v6; do
  uv run python scripts/record_replay.py \
    --model models/${v}-256x3.zip --batch-id ${v} \
    --opponents random,early-capture,denial \
    --replay-out frontend/article/data/runs/v1-to-v7/replays/${v}-seed42.json \
    --snapshot-out frontend/article/data/runs/v1-to-v7/snapshots/${v}-seed42.json \
    --id ${v}-seed42 --seed 42
done

uv run python scripts/export_onnx.py \
  --model models/v6-256x3.zip \
  --out frontend/article/data/runs/v1-to-v7/network.onnx
```

## Architecture

See `docs/superpowers/specs/2026-06-09-training-explainer-design.md`.
```

- [ ] **Step 2: Final smoke test**

```bash
cd frontend && npm run build:article && npm run check-bundle
cd dist-article && python3 -m http.server 5180 &
PID=$!
sleep 1
curl -sS http://localhost:5180/ | grep -q "How we taught" && echo OK
kill $PID
```

Expected: prints `OK` after both bundle build and serve succeed.

- [ ] **Step 3: Commit**

```bash
git add frontend/article/README.md
git commit -m "docs(article): README with develop/build/data instructions"
```

---

## Done

After this plan:
- Section 7 (Agent In Action) is the article's climax: replay + network coupled by scroll, real ONNX activations driving the WebGL viz.
- Hero section has the 4000-particle assembly behind the headline.
- 3D unfurl in Section 6 separates layers as the reader enters.
- Bundle size is gated at 4 MB total / 600 KB JS.
- `prefers-reduced-motion` skips smooth scroll, pinning, and the particle hero.
- A README documents the develop/build/data flow.

The article is complete and deployable. Future training runs append to `frontend/article/data/runs/` and appear automatically via the run index.
