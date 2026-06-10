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
