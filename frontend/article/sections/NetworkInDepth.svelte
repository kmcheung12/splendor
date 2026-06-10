<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { createNetworkViz, createNetworkVizAsync } from '../viz/createNetworkViz';
  import { scrollScrub, prefersReducedMotion } from '../lib/scrollProgress';
  import { loadNetworkSpec } from '../lib/data';
  import type { NetworkVisualization } from '../viz/NetworkVisualization';

  let stickyEl: HTMLElement;
  let containerEl: HTMLElement;
  let viz: NetworkVisualization | null = null;
  let cleanup: () => void = () => undefined;

  onMount(async () => {
    const spec = await loadNetworkSpec('v1-to-v7');
    const netSpec = {
      inputSize: spec.input_size,
      hiddenLayers: Array(spec.num_layers).fill(spec.hidden_size),
      outputSize: spec.output_size,
    };
    viz = await createNetworkVizAsync('webgl');
    try {
      viz.mount(containerEl, netSpec);
    } catch (e) {
      console.warn('WebGL mount failed; using Canvas2D:', e);
      viz.dispose();
      viz = createNetworkViz('canvas2d');
      viz.mount(containerEl, netSpec);
    }
    if (prefersReducedMotion()) {
      viz?.setScrollProgress(0.5);
    } else {
      cleanup = scrollScrub(stickyEl, (t) => viz?.setScrollProgress(t), {
        pin: true, start: 'top top', end: '+=200%',
      });
    }
  });

  onDestroy(() => {
    cleanup();
    viz?.dispose();
  });
</script>

<section id="in-depth" class="network-in-depth" bind:this={stickyEl}>
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
