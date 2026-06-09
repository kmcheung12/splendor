# Training Explainer Plan 3: Neural Network Visualisation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the abstracted `NetworkVisualization` interface plus two implementations (Canvas2D and WebGL/Three.js), and use them to populate sections 4 (Network Anatomy) and 6 (Network In Depth).

**Architecture:** A renderer-agnostic interface defined in `viz/NetworkVisualization.ts`. `Canvas2DNetworkViz` renders a flat top-down diagram using `OffscreenCanvas` and `requestAnimationFrame`. `WebGLNetworkViz` uses Three.js with instanced meshes for nodes, line segments with a glow shader for edges, and a bloom post-pass. A factory selects the right impl, falling back to Canvas2D when WebGL is unavailable. Two Svelte components (`NetworkAnatomy.svelte`, `NetworkInDepth.svelte`) own scroll-driven progress and pass it down.

**Tech Stack:** Svelte 4, TypeScript, Three.js, postprocessing (for bloom), GSAP ScrollTrigger.

---

### Task 1: Define the NetworkVisualization interface

**Files:**
- Create: `frontend/article/viz/NetworkVisualization.ts`
- Create: `frontend/article/viz/types.ts`

- [ ] **Step 1: Write types and interface**

```ts
// frontend/article/viz/types.ts
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
```

```ts
// frontend/article/viz/NetworkVisualization.ts
import type { LayerActivations, NetworkSpec } from './types';

export interface NetworkVisualization {
  mount(container: HTMLElement, network: NetworkSpec): void;
  setActivations(obs: Float32Array, layerOutputs: LayerActivations): void;
  setScrollProgress(t: number): void;
  setHighlightedAction(actionIdx: number | null): void;
  dispose(): void;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/article/viz/
git commit -m "feat(article): NetworkVisualization interface and types"
```

---

### Task 2: Canvas2DNetworkViz — empty mount

**Files:**
- Create: `frontend/article/viz/Canvas2DNetworkViz.ts`
- Create: `frontend/article/viz/__tests__/Canvas2DNetworkViz.test.ts`

- [ ] **Step 1: Write failing test**

```ts
// frontend/article/viz/__tests__/Canvas2DNetworkViz.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { Canvas2DNetworkViz } from '../Canvas2DNetworkViz';

describe('Canvas2DNetworkViz', () => {
  let container: HTMLElement;
  beforeEach(() => {
    container = document.createElement('div');
    Object.defineProperty(container, 'clientWidth', { value: 800 });
    Object.defineProperty(container, 'clientHeight', { value: 400 });
    document.body.appendChild(container);
  });

  it('mounts a canvas matching container size', () => {
    const viz = new Canvas2DNetworkViz();
    viz.mount(container, {
      inputSize: 100, hiddenLayers: [16, 16], outputSize: 10,
    });
    const canvas = container.querySelector('canvas');
    expect(canvas).toBeTruthy();
    expect(canvas?.width).toBe(800);
    expect(canvas?.height).toBe(400);
    viz.dispose();
    expect(container.querySelector('canvas')).toBeFalsy();
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm run test:article`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement minimal canvas mount**

```ts
// frontend/article/viz/Canvas2DNetworkViz.ts
import type { NetworkVisualization } from './NetworkVisualization';
import type { LayerActivations, NetworkSpec } from './types';

export class Canvas2DNetworkViz implements NetworkVisualization {
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private network: NetworkSpec | null = null;
  private activations: LayerActivations | null = null;
  private scrollT = 0;
  private highlight: number | null = null;
  private rafHandle = 0;

  mount(container: HTMLElement, network: NetworkSpec): void {
    this.network = network;
    const canvas = document.createElement('canvas');
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    container.appendChild(canvas);
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.draw();
  }

  setActivations(_obs: Float32Array, layerOutputs: LayerActivations): void {
    this.activations = layerOutputs;
    this.draw();
  }

  setScrollProgress(t: number): void {
    this.scrollT = t;
    this.draw();
  }

  setHighlightedAction(actionIdx: number | null): void {
    this.highlight = actionIdx;
    this.draw();
  }

  dispose(): void {
    cancelAnimationFrame(this.rafHandle);
    this.canvas?.remove();
    this.canvas = null;
    this.ctx = null;
  }

  private draw(): void {
    if (!this.ctx || !this.canvas || !this.network) return;
    const { width, height } = this.canvas;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, width, height);
  }
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: 1 passed (Canvas2DNetworkViz)

- [ ] **Step 5: Commit**

```bash
git add frontend/article/viz/Canvas2DNetworkViz.ts frontend/article/viz/__tests__/
git commit -m "feat(article): Canvas2DNetworkViz mount/dispose"
```

---

### Task 3: Canvas2D — render nodes and edges

**Files:**
- Modify: `frontend/article/viz/Canvas2DNetworkViz.ts`
- Modify: `frontend/article/viz/__tests__/Canvas2DNetworkViz.test.ts`

- [ ] **Step 1: Add layout test**

```ts
// Append to frontend/article/viz/__tests__/Canvas2DNetworkViz.test.ts
import { computeLayout } from '../Canvas2DNetworkViz';

describe('computeLayout', () => {
  it('produces one column per layer with correct x positions', () => {
    const layout = computeLayout(
      { inputSize: 4, hiddenLayers: [8, 8], outputSize: 3 },
      { width: 400, height: 200, padding: 40 },
    );
    expect(layout.columns).toHaveLength(4);
    expect(layout.columns[0].x).toBe(40);
    expect(layout.columns[3].x).toBe(360);
  });

  it('limits visible nodes per column to 32 (256-wide layers downsampled)', () => {
    const layout = computeLayout(
      { inputSize: 421, hiddenLayers: [256, 256, 256], outputSize: 50 },
      { width: 800, height: 400, padding: 40 },
    );
    layout.columns.forEach((c) => expect(c.nodes.length).toBeLessThanOrEqual(32));
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm run test:article`
Expected: FAIL (computeLayout not exported)

- [ ] **Step 3: Implement layout + draw**

```ts
// In frontend/article/viz/Canvas2DNetworkViz.ts — add at module scope:
export interface LayoutOptions {
  width: number;
  height: number;
  padding: number;
}

export interface LayoutColumn {
  x: number;
  nodes: { y: number; activation: number }[];
}

export interface NetworkLayout {
  columns: LayoutColumn[];
}

const MAX_VISIBLE_NODES = 32;

export function computeLayout(
  spec: NetworkSpec, opts: LayoutOptions,
): NetworkLayout {
  const layerSizes = [
    spec.inputSize,
    ...spec.hiddenLayers,
    spec.outputSize,
  ];
  const cols = layerSizes.length;
  const xStep = (opts.width - 2 * opts.padding) / Math.max(cols - 1, 1);
  const innerHeight = opts.height - 2 * opts.padding;
  const columns: LayoutColumn[] = layerSizes.map((size, i) => {
    const visible = Math.min(size, MAX_VISIBLE_NODES);
    const yStep = visible > 1 ? innerHeight / (visible - 1) : 0;
    const nodes = Array.from({ length: visible }, (_, j) => ({
      y: opts.padding + j * yStep,
      activation: 0,
    }));
    return { x: opts.padding + i * xStep, nodes };
  });
  return { columns };
}
```

And update the `draw()` method body to actually paint:
```ts
private draw(): void {
  if (!this.ctx || !this.canvas || !this.network) return;
  const { width, height } = this.canvas;
  const ctx = this.ctx;
  ctx.clearRect(0, 0, width, height);

  const layout = computeLayout(this.network, {
    width, height, padding: 40,
  });
  const reveal = this.scrollT;
  const colsToShow = Math.ceil(layout.columns.length * reveal);

  // Edges
  ctx.strokeStyle = 'rgba(243,241,236,0.06)';
  ctx.lineWidth = 1;
  for (let i = 0; i < colsToShow - 1; i++) {
    const a = layout.columns[i];
    const b = layout.columns[i + 1];
    for (const na of a.nodes) {
      for (const nb of b.nodes) {
        ctx.beginPath();
        ctx.moveTo(a.x, na.y);
        ctx.lineTo(b.x, nb.y);
        ctx.stroke();
      }
    }
  }

  // Nodes
  for (let i = 0; i < colsToShow; i++) {
    const col = layout.columns[i];
    for (const n of col.nodes) {
      ctx.fillStyle = 'rgba(255,61,138,0.85)';
      ctx.beginPath();
      ctx.arc(col.x, n.y, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: all viz tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/article/viz/Canvas2DNetworkViz.ts frontend/article/viz/__tests__/
git commit -m "feat(article): Canvas2DNetworkViz computes layout and renders nodes/edges"
```

---

### Task 4: Canvas2D — activation-driven colouring

**Files:**
- Modify: `frontend/article/viz/Canvas2DNetworkViz.ts`

- [ ] **Step 1: Update `setActivations` to feed layout**

In `Canvas2DNetworkViz`:
```ts
// Add private fields:
private layout: NetworkLayout | null = null;

// In mount(), after assigning canvas/ctx:
this.layout = computeLayout(network, {
  width: this.canvas.width, height: this.canvas.height, padding: 40,
});

// Replace setActivations:
setActivations(_obs: Float32Array, layerOutputs: LayerActivations): void {
  this.activations = layerOutputs;
  if (!this.layout || !this.network) return;
  const layerSources: Float32Array[] = [
    _obs, ...layerOutputs.layers, layerOutputs.policy,
  ];
  this.layout.columns.forEach((col, ci) => {
    const src = layerSources[ci];
    if (!src) return;
    col.nodes.forEach((node, ni) => {
      const idx = Math.floor((ni / col.nodes.length) * src.length);
      node.activation = src[idx];
    });
  });
  this.draw();
}
```

Update `draw()` node fill to colour by activation:
```ts
// Replace the node fill with:
const a = Math.max(0, Math.min(1, n.activation));
ctx.fillStyle = `rgba(255,${Math.floor(61 + 100 * (1 - a))},${Math.floor(138 + 60 * (1 - a))},${0.4 + 0.6 * a})`;
```

- [ ] **Step 2: Verify visually**

Add a quick scratch usage in Article.svelte temporarily to mount and call `setActivations` with random data; confirm visible variation.

(After verifying remove the scratch usage; this is for human inspection only.)

- [ ] **Step 3: Commit**

```bash
git add frontend/article/viz/Canvas2DNetworkViz.ts
git commit -m "feat(article): Canvas2DNetworkViz colours nodes by activation"
```

---

### Task 5: Install Three.js and postprocessing

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install**

```bash
cd frontend && npm install three postprocessing
cd frontend && npm install -D @types/three
```

- [ ] **Step 2: Verify**

```bash
cd frontend && node -e "console.log(require('three/package.json').version)"
```

Expected: prints version.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(article): add three.js and postprocessing"
```

---

### Task 6: WebGLNetworkViz — scene + mount

**Files:**
- Create: `frontend/article/viz/WebGLNetworkViz.ts`
- Create: `frontend/article/viz/__tests__/WebGLNetworkViz.test.ts`

- [ ] **Step 1: Write smoke test**

```ts
// frontend/article/viz/__tests__/WebGLNetworkViz.test.ts
import { describe, it, expect, vi } from 'vitest';

describe('WebGLNetworkViz', () => {
  it('falls back gracefully when WebGL unavailable (jsdom case)', async () => {
    const { WebGLNetworkViz } = await import('../WebGLNetworkViz');
    const viz = new WebGLNetworkViz();
    const container = document.createElement('div');
    Object.defineProperty(container, 'clientWidth', { value: 800 });
    Object.defineProperty(container, 'clientHeight', { value: 400 });
    document.body.appendChild(container);
    // Three will throw in jsdom; viz constructor must not throw, mount must throw.
    expect(() => viz.mount(container, {
      inputSize: 100, hiddenLayers: [16], outputSize: 10,
    })).toThrow(/WebGL/);
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm run test:article`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement scene scaffolding**

```ts
// frontend/article/viz/WebGLNetworkViz.ts
import * as THREE from 'three';
import type { NetworkVisualization } from './NetworkVisualization';
import type { LayerActivations, NetworkSpec } from './types';

const MAX_VISIBLE = 24;

export class WebGLNetworkViz implements NetworkVisualization {
  private renderer: THREE.WebGLRenderer | null = null;
  private scene: THREE.Scene | null = null;
  private camera: THREE.PerspectiveCamera | null = null;
  private container: HTMLElement | null = null;
  private network: NetworkSpec | null = null;
  private rafHandle = 0;
  private nodeMeshes: THREE.InstancedMesh[] = [];
  private edgeLines: THREE.LineSegments[] = [];
  private scrollT = 0;

  mount(container: HTMLElement, network: NetworkSpec): void {
    this.container = container;
    this.network = network;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true, alpha: true, powerPreference: 'high-performance',
      });
    } catch {
      throw new Error('WebGL unavailable');
    }
    if (!renderer.getContext()) {
      throw new Error('WebGL context not created');
    }
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor(0x0a0d12, 0);
    container.appendChild(renderer.domElement);
    this.renderer = renderer;

    const aspect = container.clientWidth / container.clientHeight;
    this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 100);
    this.camera.position.set(0, 0, 8);

    this.scene = new THREE.Scene();
    this.buildLayers();
    this.startLoop();
  }

  setActivations(_obs: Float32Array, _layerOutputs: LayerActivations): void {
    // Plan 5 wires activations to instance colours.
  }

  setScrollProgress(t: number): void {
    this.scrollT = t;
    if (!this.camera) return;
    this.camera.position.x = (t - 0.5) * 6;
    this.camera.lookAt(0, 0, 0);
  }

  setHighlightedAction(_actionIdx: number | null): void {
    // Plan 5 wires this.
  }

  dispose(): void {
    cancelAnimationFrame(this.rafHandle);
    this.nodeMeshes.forEach((m) => m.dispose());
    this.edgeLines.forEach((l) => l.geometry.dispose());
    this.renderer?.dispose();
    this.renderer?.domElement.remove();
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.nodeMeshes = [];
    this.edgeLines = [];
  }

  private buildLayers(): void {
    if (!this.network || !this.scene) return;
    const layerSizes = [
      this.network.inputSize,
      ...this.network.hiddenLayers,
      this.network.outputSize,
    ];
    const spacing = 1.5;
    const xs = layerSizes.map((_, i) =>
      (i - (layerSizes.length - 1) / 2) * spacing,
    );
    const sphere = new THREE.SphereGeometry(0.05, 12, 12);
    const material = new THREE.MeshBasicMaterial({ color: 0xff3d8a });

    layerSizes.forEach((size, li) => {
      const visible = Math.min(size, MAX_VISIBLE);
      const mesh = new THREE.InstancedMesh(sphere, material, visible);
      const dummy = new THREE.Object3D();
      const yStep = visible > 1 ? 3 / (visible - 1) : 0;
      for (let i = 0; i < visible; i++) {
        dummy.position.set(xs[li], 1.5 - i * yStep, 0);
        dummy.updateMatrix();
        mesh.setMatrixAt(i, dummy.matrix);
      }
      this.scene!.add(mesh);
      this.nodeMeshes.push(mesh);
    });
  }

  private startLoop(): void {
    const tick = () => {
      if (!this.renderer || !this.scene || !this.camera) return;
      this.renderer.render(this.scene, this.camera);
      this.rafHandle = requestAnimationFrame(tick);
    };
    tick();
  }
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: 1 passed (WebGLNetworkViz throws in jsdom)

- [ ] **Step 5: Commit**

```bash
git add frontend/article/viz/WebGLNetworkViz.ts frontend/article/viz/__tests__/WebGLNetworkViz.test.ts
git commit -m "feat(article): WebGLNetworkViz scene scaffolding with instanced nodes"
```

---

### Task 7: WebGL — edges with glow shader

**Files:**
- Modify: `frontend/article/viz/WebGLNetworkViz.ts`

- [ ] **Step 1: Add edges in `buildLayers`**

After the node-mesh loop in `buildLayers`, append:
```ts
const lineMaterial = new THREE.LineBasicMaterial({
  color: 0xff3d8a, transparent: true, opacity: 0.08,
});
for (let i = 0; i < layerSizes.length - 1; i++) {
  const a = Math.min(layerSizes[i], MAX_VISIBLE);
  const b = Math.min(layerSizes[i + 1], MAX_VISIBLE);
  const positions: number[] = [];
  const yA = (k: number) => 1.5 - k * (a > 1 ? 3 / (a - 1) : 0);
  const yB = (k: number) => 1.5 - k * (b > 1 ? 3 / (b - 1) : 0);
  for (let ja = 0; ja < a; ja++) {
    for (let jb = 0; jb < b; jb++) {
      positions.push(xs[i], yA(ja), 0, xs[i + 1], yB(jb), 0);
    }
  }
  const geom = new THREE.BufferGeometry();
  geom.setAttribute('position',
    new THREE.Float32BufferAttribute(positions, 3));
  const line = new THREE.LineSegments(geom, lineMaterial);
  this.scene!.add(line);
  this.edgeLines.push(line);
}
```

- [ ] **Step 2: Verify visually** (manual in browser once mounted in §6)

- [ ] **Step 3: Commit**

```bash
git add frontend/article/viz/WebGLNetworkViz.ts
git commit -m "feat(article): WebGLNetworkViz adds edge LineSegments"
```

---

### Task 8: Factory

**Files:**
- Create: `frontend/article/viz/createNetworkViz.ts`
- Create: `frontend/article/viz/__tests__/createNetworkViz.test.ts`

- [ ] **Step 1: Write failing test**

```ts
// frontend/article/viz/__tests__/createNetworkViz.test.ts
import { describe, it, expect, vi } from 'vitest';
import { createNetworkViz } from '../createNetworkViz';
import { Canvas2DNetworkViz } from '../Canvas2DNetworkViz';

describe('createNetworkViz', () => {
  it('returns Canvas2D for canvas2d', () => {
    const v = createNetworkViz('canvas2d');
    expect(v).toBeInstanceOf(Canvas2DNetworkViz);
  });

  it('falls back to Canvas2D when WebGL is unavailable', () => {
    const v = createNetworkViz('webgl');
    expect(v).toBeInstanceOf(Canvas2DNetworkViz);
  });
});
```

- [ ] **Step 2: Run test to verify fail**

Run: `cd frontend && npm run test:article`
Expected: FAIL (createNetworkViz not found)

- [ ] **Step 3: Implement factory with WebGL availability check**

```ts
// frontend/article/viz/createNetworkViz.ts
import type { NetworkVisualization } from './NetworkVisualization';
import type { VizType } from './types';
import { Canvas2DNetworkViz } from './Canvas2DNetworkViz';

function isWebGLAvailable(): boolean {
  if (typeof document === 'undefined') return false;
  try {
    const canvas = document.createElement('canvas');
    return !!(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

export function createNetworkViz(type: VizType): NetworkVisualization {
  if (type === 'webgl' && isWebGLAvailable()) {
    // Lazy import to avoid loading three.js on canvas2d-only pages.
    const { WebGLNetworkViz } = require('./WebGLNetworkViz');
    return new WebGLNetworkViz();
  }
  return new Canvas2DNetworkViz();
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd frontend && npm run test:article`
Expected: all passing

- [ ] **Step 5: Commit**

```bash
git add frontend/article/viz/createNetworkViz.ts frontend/article/viz/__tests__/createNetworkViz.test.ts
git commit -m "feat(article): createNetworkViz factory with WebGL fallback"
```

---

### Task 9: NetworkAnatomy section

**Files:**
- Modify: `frontend/article/sections/NetworkAnatomy.svelte`

- [ ] **Step 1: Implement section with sticky Canvas2D viz**

```svelte
<!-- frontend/article/sections/NetworkAnatomy.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { createNetworkViz } from '../viz/createNetworkViz';
  import { scrollScrub } from '../lib/scrollProgress';
  import { loadNetworkSpec } from '../lib/data';
  import type { NetworkVisualization } from '../viz/NetworkVisualization';

  let stickyEl: HTMLElement;
  let containerEl: HTMLElement;
  let viz: NetworkVisualization | null = null;
  let cleanup: () => void = () => undefined;

  onMount(async () => {
    const spec = await loadNetworkSpec('v1-to-v7');
    viz = createNetworkViz('canvas2d');
    viz.mount(containerEl, {
      inputSize: spec.input_size,
      hiddenLayers: Array(spec.num_layers).fill(spec.hidden_size),
      outputSize: spec.output_size,
    });
    cleanup = scrollScrub(stickyEl, (t) => viz?.setScrollProgress(t), {
      pin: true, start: 'top top', end: '+=200%',
    });
  });

  onDestroy(() => {
    cleanup();
    viz?.dispose();
  });
</script>

<section class="network-anatomy" bind:this={stickyEl}>
  <div class="sticky-frame">
    <div class="viz" bind:this={containerEl}></div>
    <aside class="callouts">
      <h2>The shape of the network</h2>
      <p>
        Input: the entire visible game state, flattened to a 421-dimensional
        vector. Three hidden layers, 256 neurons each. Output: a 50-way
        choice over actions, plus a single value estimate.
      </p>
    </aside>
  </div>
</section>

<style>
  .network-anatomy {
    height: 300vh;
    position: relative;
  }
  .sticky-frame {
    position: sticky;
    top: 0;
    height: 100vh;
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 2rem;
    padding: 2rem;
  }
  .viz {
    width: 100%;
    height: 100%;
    background: rgba(255,255,255,0.02);
    border-radius: 12px;
  }
  .callouts h2 {
    font-size: clamp(1.75rem, 3vw, 2.5rem);
    letter-spacing: -0.02em;
  }
  .callouts p {
    color: #d6d3cb;
    font-size: 1.1rem;
  }
</style>
```

- [ ] **Step 2: Verify visually**

Run `npm run dev:article`. Scroll into section 4. Expected: sticky viewport with Canvas2D network rendering, edges and nodes appearing as you scroll.

- [ ] **Step 3: Commit**

```bash
git add frontend/article/sections/NetworkAnatomy.svelte
git commit -m "feat(article): NetworkAnatomy section with sticky Canvas2D viz"
```

---

### Task 10: NetworkInDepth section

**Files:**
- Modify: `frontend/article/sections/NetworkInDepth.svelte`

- [ ] **Step 1: Implement with WebGL viz**

```svelte
<!-- frontend/article/sections/NetworkInDepth.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { createNetworkViz } from '../viz/createNetworkViz';
  import { scrollScrub } from '../lib/scrollProgress';
  import { loadNetworkSpec } from '../lib/data';
  import type { NetworkVisualization } from '../viz/NetworkVisualization';

  let stickyEl: HTMLElement;
  let containerEl: HTMLElement;
  let viz: NetworkVisualization | null = null;
  let cleanup: () => void = () => undefined;

  onMount(async () => {
    const spec = await loadNetworkSpec('v1-to-v7');
    viz = createNetworkViz('webgl');
    viz.mount(containerEl, {
      inputSize: spec.input_size,
      hiddenLayers: Array(spec.num_layers).fill(spec.hidden_size),
      outputSize: spec.output_size,
    });
    cleanup = scrollScrub(stickyEl, (t) => viz?.setScrollProgress(t), {
      pin: true, start: 'top top', end: '+=200%',
    });
  });

  onDestroy(() => {
    cleanup();
    viz?.dispose();
  });
</script>

<section class="network-in-depth" bind:this={stickyEl}>
  <div class="sticky-frame">
    <div class="viz" bind:this={containerEl}></div>
    <aside class="callouts">
      <h2>Inside the same network, now in three dimensions.</h2>
      <p>
        Two heads fork from the last hidden layer: a policy head that
        chooses the next move, and a value head that asks "from here, am I
        winning?"
      </p>
    </aside>
  </div>
</section>

<style>
  .network-in-depth {
    height: 300vh;
    position: relative;
    background: linear-gradient(to bottom, transparent, rgba(255,61,138,0.04), transparent);
  }
  .sticky-frame {
    position: sticky;
    top: 0;
    height: 100vh;
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 2rem;
    padding: 2rem;
  }
  .viz {
    width: 100%;
    height: 100%;
    border-radius: 12px;
    overflow: hidden;
  }
  .callouts h2 {
    font-size: clamp(1.75rem, 3vw, 2.5rem);
    letter-spacing: -0.02em;
  }
  .callouts p { color: #d6d3cb; font-size: 1.1rem; }
</style>
```

- [ ] **Step 2: Verify visually**

In browser scroll into section 6. Expected: 3D nodes and edges visible, camera dolly responds to scroll.

- [ ] **Step 3: Commit**

```bash
git add frontend/article/sections/NetworkInDepth.svelte
git commit -m "feat(article): NetworkInDepth section with WebGL viz"
```

---

## Done

After this plan:
- The `NetworkVisualization` interface and both implementations are complete and tested.
- Section 4 (Network Anatomy) renders the 256×3 network with progressive scroll reveal via Canvas2D.
- Section 6 (Network In Depth) renders the same network in 3D via WebGL, with camera responding to scroll.
- Activation wiring is stubbed; Plan 5 connects ONNX-driven activations.
