<script lang="ts">
  import type { PokemonCard } from '../lib/types'

  export let card: PokemonCard | null
  export let tier: string
  export let highlight = false

  const TIER_GRAD: Record<string, string> = {
    common:    'linear-gradient(135deg,#8B6914,#c9a64a)',
    uncommon:  'linear-gradient(135deg,#7f8c8d,#bdc3c7)',
    rare:      'linear-gradient(135deg,#c8a415,#f5d60a)',
    epic:      'linear-gradient(135deg,#6c3483,#a569bd)',
    legendary: 'linear-gradient(135deg,#154360,#2e86c1,#e74c3c,#f39c12)',
  }

  const TOKEN_COLORS: Record<string, string> = {
    red: '#e74c3c', yellow: '#f1c40f', blue: '#3498db',
    pink: '#e91e96', black: '#555', master: '#f39c12',
  }
</script>

{#if card}
  <div
    class="card"
    class:highlight
    style="background:{TIER_GRAD[tier] ?? TIER_GRAD.common}"
    on:click
  >
    <div class="header">
      <span class="name">{card.name}</span>
      <span class="points">{card.point}</span>
    </div>

    <div class="row label">Cost</div>
    <div class="row icons">
      {#each card.cost as t}
        <span class="pip" style="background:{TOKEN_COLORS[t]}"></span>
      {/each}
      {#if card.cost.length === 0}<span class="none">—</span>{/if}
    </div>

    <div class="row label">Bonus</div>
    <div class="row icons">
      {#each card.bonus as b}
        <span class="pip" style="background:{TOKEN_COLORS[b]}"></span>
      {/each}
      {#if card.bonus.length === 0}<span class="none">—</span>{/if}
    </div>

    {#if card.evolve.length > 0}
      <div class="row label">Evolves →</div>
      <div class="row icons">
        <span class="evolve-name">{card.evolve_into}</span>
        {#each card.evolve as b}
          <span class="pip" style="background:{TOKEN_COLORS[b]}"></span>
        {/each}
      </div>
    {/if}
  </div>
{:else}
  <div class="card empty"></div>
{/if}

<style>
  .card {
    border-radius: 8px; padding: 6px 8px; min-height: 100px;
    display: flex; flex-direction: column; gap: 2px;
    box-shadow: 0 2px 4px rgba(0,0,0,.3);
    cursor: pointer; transition: transform .15s, filter .15s;
    user-select: none;
  }
  .card:hover { transform: translateY(-2px); }
  .card.empty { background: rgba(255,255,255,.05); border: 1px dashed rgba(255,255,255,.2); cursor: default; }
  .card.highlight { filter: drop-shadow(0 0 6px #f1c40f); animation: pulse 1s ease-in-out infinite; }
  @keyframes pulse {
    0%, 100% { filter: drop-shadow(0 0 4px #f1c40f); }
    50%       { filter: drop-shadow(0 0 12px #f1c40f); }
  }
  .header { display: flex; justify-content: space-between; align-items: flex-start; }
  .name { font-size: .75rem; font-weight: bold; color: white; text-shadow: 0 1px 2px rgba(0,0,0,.6); flex:1; }
  .points {
    font-size: .9rem; font-weight: bold; color: white;
    background: rgba(0,0,0,.35); border-radius: 50%;
    width: 22px; height: 22px; display: flex; align-items: center; justify-content: center;
  }
  .row.label { font-size: .55rem; color: rgba(255,255,255,.7); text-transform: uppercase; margin-top: 2px; }
  .row.icons { display: flex; flex-wrap: wrap; gap: 2px; }
  .pip { width: 10px; height: 10px; border-radius: 50%; border: 1px solid rgba(255,255,255,.4); }
  .none { font-size: .6rem; color: rgba(255,255,255,.5); }
  .evolve-name { font-size: .6rem; color: rgba(255,255,255,.8); margin-right: 2px; }
</style>
