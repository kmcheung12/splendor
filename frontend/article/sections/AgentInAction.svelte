<!-- frontend/article/sections/AgentInAction.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { scrollScrub, prefersReducedMotion } from '../lib/scrollProgress';
  import { loadReplay, loadNetworkSpec } from '../lib/data';
  import { loadReplaySnapshots, type ReplaySnapshots } from '../replay/snapshot';
  import { loadOnnxNetwork, runNetwork } from '../lib/onnxRunner';
  import { createNetworkViz, createNetworkVizAsync } from '../viz/createNetworkViz';
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
    const netSpec = {
      inputSize: spec.input_size,
      hiddenLayers: Array(spec.num_layers).fill(spec.hidden_size),
      outputSize: spec.output_size,
    };
    viz = await createNetworkVizAsync('webgl');
    try {
      viz.mount(vizContainer, netSpec);
    } catch (e) {
      console.warn('WebGL mount failed; using Canvas2D:', e);
      viz.dispose();
      viz = createNetworkViz('canvas2d');
      viz.mount(vizContainer, netSpec);
    }
    [replay, snapshots] = await Promise.all([
      loadReplay('v1-to-v7', 'v6-seed42'),
      loadReplaySnapshots('v6-seed42'),
    ]);
    try {
      await loadOnnxNetwork('v1-to-v7');
    } catch (e) {
      console.warn('ONNX load failed; activations will be skipped:', e);
    }

    if (prefersReducedMotion()) {
      viz?.setScrollProgress(0.5);
    } else {
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
    }
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
