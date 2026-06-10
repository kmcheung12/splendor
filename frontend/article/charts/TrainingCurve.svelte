<!-- frontend/article/charts/TrainingCurve.svelte -->
<script lang="ts">
  import type { CurvesPerBatch } from '../lib/types';

  export let batches: CurvesPerBatch[];
  export let metric: 'explained_variance' | 'entropy_loss' | 'value_loss';
  export let currentIndex: number;

  const padding = { top: 24, right: 24, bottom: 32, left: 40 };
  const width = 600;
  const height = 300;
  $: innerW = width - padding.left - padding.right;
  $: innerH = height - padding.top - padding.bottom;

  $: ys = batches.map((b) => b[metric]);
  $: yMin = Math.min(...ys, 0);
  $: yMax = Math.max(...ys, 0.1);
  $: yScale = (v: number) =>
    padding.top + innerH - ((v - yMin) / (yMax - yMin)) * innerH;
  $: xScale = (i: number) =>
    padding.left + (batches.length === 1 ? innerW / 2 : (i / (batches.length - 1)) * innerW);

  $: points = batches.map((b, i) => `${xScale(i)},${yScale(b[metric])}`).join(' ');
</script>

<svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
  <line x1={padding.left} x2={width - padding.right}
        y1={yScale(0)} y2={yScale(0)}
        stroke="rgba(255,255,255,0.15)" stroke-dasharray="4 4" />
  <polyline fill="none" stroke="#ff3d8a" stroke-width="2" points={points} />
  {#each batches as b, i}
    <circle
      cx={xScale(i)}
      cy={yScale(b[metric])}
      r={i === currentIndex ? 6 : 3}
      fill={i === currentIndex ? '#ff3d8a' : 'rgba(243,241,236,0.4)'} />
    <text x={xScale(i)} y={height - 8} fill="rgba(243,241,236,0.5)"
          text-anchor="middle" font-size="11">{b.id}</text>
  {/each}
  <text x={8} y={padding.top - 4} fill="rgba(243,241,236,0.7)" font-size="11">
    {metric}
  </text>
</svg>

<style>
  svg { width: 100%; height: auto; display: block; }
</style>
