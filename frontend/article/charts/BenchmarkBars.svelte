<!-- frontend/article/charts/BenchmarkBars.svelte -->
<script lang="ts">
  import type { BenchmarkResult } from '../lib/types';
  export let benchmark: BenchmarkResult;
  export let agentIndex: number = 0;
</script>

<div class="bars">
  {#each benchmark.opponents as opp, i}
    <div class="row">
      <div class="label" class:agent={i === agentIndex}>{opp}</div>
      <div class="track">
        <div class="bar"
             class:agent={i === agentIndex}
             style="width: {benchmark.win_rates[i] * 100}%">
        </div>
      </div>
      <div class="value">{Math.round(benchmark.win_rates[i] * 100)}%</div>
    </div>
  {/each}
</div>

<style>
  .bars {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-size: 0.9rem;
  }
  .row {
    display: grid;
    grid-template-columns: 8rem 1fr 3rem;
    gap: 0.75rem;
    align-items: center;
  }
  .label { color: var(--muted); }
  .label.agent { color: var(--fg); font-weight: 600; }
  .track {
    background: rgba(255,255,255,0.05);
    height: 0.5rem;
    border-radius: 3px;
    overflow: hidden;
  }
  .bar { background: rgba(243,241,236,0.5); height: 100%; }
  .bar.agent { background: var(--accent); }
  .value { text-align: right; font-variant-numeric: tabular-nums; }
</style>
