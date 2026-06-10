<!-- frontend/article/sections/TrainingStory.svelte -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { scrollScrub } from '../lib/scrollProgress';
  import { loadCurves, loadRunSummary } from '../lib/data';
  import { loadReplaySnapshots, type ReplaySnapshots } from '../replay/snapshot';
  import { mapScrollToBatchTurn } from '../replay/useReplayScrubber';
  import TrainingCurve from '../charts/TrainingCurve.svelte';
  import BenchmarkBars from '../charts/BenchmarkBars.svelte';
  import GameReplayPlayer from '../replay/GameReplayPlayer.svelte';
  import type { BatchResult, CurvesPerBatch } from '../lib/types';

  let stickyEl: HTMLElement;
  let curves: CurvesPerBatch[] = [];
  let batches: BatchResult[] = [];
  let storyBatches = ['v1', 'v3', 'v6']; // batches with snapshot files
  let snapshotsByBatch: Record<string, ReplaySnapshots> = {};
  let currentBatchIdx = 0;
  let currentTurnIdx = 0;
  let cleanup: () => void = () => undefined;

  $: currentBatchId = storyBatches[currentBatchIdx];
  $: currentSnapshots = snapshotsByBatch[currentBatchId];
  $: currentSnapshot = currentSnapshots?.turns[currentTurnIdx]?.snapshot
                       ?? currentSnapshots?.initial;
  $: currentDescription = currentSnapshots?.turns[currentTurnIdx]?.description ?? '';
  $: currentBatchInfo = batches.find((b) => b.id === currentBatchId);

  onMount(async () => {
    const [summaryRes, curvesRes] = await Promise.all([
      loadRunSummary('v1-to-v7'),
      loadCurves('v1-to-v7'),
    ]);
    batches = summaryRes.batches;
    curves = curvesRes.batches;
    const snaps = await Promise.all(
      storyBatches.map((id) => loadReplaySnapshots(`${id}-seed42`)),
    );
    snapshotsByBatch = Object.fromEntries(
      storyBatches.map((id, i) => [id, snaps[i]]),
    );
    const batchTurnCounts = storyBatches.map(
      (id) => snapshotsByBatch[id]?.turns.length ?? 0,
    );
    cleanup = scrollScrub(stickyEl, (t) => {
      const [b, tu] = mapScrollToBatchTurn(t, batchTurnCounts);
      currentBatchIdx = b;
      currentTurnIdx = tu;
    }, { pin: true, start: 'top top', end: '+=400%' });
  });

  onDestroy(() => cleanup());
</script>

<section class="training-story" bind:this={stickyEl}>
  <div class="sticky-frame">
    <div class="story-text">
      {#if currentBatchInfo}
        <h2>Batch {currentBatchInfo.id}</h2>
        <p class="narrative">{currentBatchInfo.narrative}</p>
        <div class="stats">
          <div><strong>Opponents:</strong> {currentBatchInfo.opponents.join(', ')}</div>
          <div><strong>Episodes:</strong> {currentBatchInfo.episodes.toLocaleString()}</div>
          <div><strong>LR:</strong> {currentBatchInfo.lr}</div>
        </div>
        {#if currentBatchInfo.benchmarks.length}
          <h3>Benchmark</h3>
          <BenchmarkBars
            benchmark={currentBatchInfo.benchmarks[0]}
            agentIndex={0} />
        {/if}
      {/if}
    </div>
    <div class="visuals">
      <TrainingCurve
        batches={curves}
        metric="explained_variance"
        currentIndex={curves.findIndex((c) => c.id === currentBatchId)} />
      {#if currentSnapshot}
        <GameReplayPlayer
          snapshot={currentSnapshot}
          description={currentDescription} />
      {/if}
    </div>
  </div>
</section>

<style>
  .training-story {
    height: 500vh;
    position: relative;
  }
  .sticky-frame {
    position: sticky;
    top: 0;
    height: 100vh;
    display: grid;
    grid-template-columns: 1fr 1.4fr;
    gap: 3rem;
    padding: 3rem;
    align-items: center;
  }
  .story-text h2 {
    font-size: clamp(1.75rem, 3vw, 2.5rem);
    margin: 0 0 1rem;
    letter-spacing: -0.02em;
  }
  .story-text h3 {
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent);
    margin: 2rem 0 0.75rem;
  }
  .narrative { font-size: 1.1rem; color: #d6d3cb; }
  .stats {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    font-size: 0.9rem;
    color: var(--muted);
    margin: 1.5rem 0;
  }
  .visuals {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }
</style>
