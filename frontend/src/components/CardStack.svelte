<script lang="ts">
  import type { PokemonCard } from '../lib/types'

  export let cards: PokemonCard[]

  const TOKEN_COLORS: Record<string, string> = {
    red: '#e74c3c', yellow: '#f1c40f', blue: '#3498db',
    pink: '#e91e96', black: '#555', master: '#f39c12',
  }
  const TIER_GRAD: Record<string, string> = {
    common:    'linear-gradient(135deg,#8B6914,#c9a64a)',
    uncommon:  'linear-gradient(135deg,#7f8c8d,#bdc3c7)',
    rare:      'linear-gradient(135deg,#c8a415,#f5d60a)',
    epic:      'linear-gradient(135deg,#6c3483,#a569bd)',
    legendary: 'linear-gradient(135deg,#154360,#2e86c1,#e74c3c,#f39c12)',
  }

  $: groups = (() => {
    const map: Record<string, PokemonCard[]> = {}
    for (const c of cards) {
      const key = c.bonus[0] ?? 'none'
      ;(map[key] ??= []).push(c)
    }
    return Object.entries(map)
  })()
</script>

<div class="card-stacks">
  {#each groups as [color, stack]}
    <div class="stack">
      {#each stack as card, i}
        <div
          class="strip"
          class:face-down={card.evolved}
          style="background:{card.evolved ? '#333' : (TIER_GRAD[card.tier] ?? TIER_GRAD.common)}; top:{i * 18}px; z-index:{i};"
        >
          {#if !card.evolved}
            <span class="strip-name">{card.name}</span>
            {#if card.evolve_into}
              <span class="strip-arrow">→ {card.evolve_into}</span>
            {/if}
            {#each card.bonus as b}
              <span class="strip-pip" style="background:{TOKEN_COLORS[b]}"></span>
            {/each}
          {/if}
        </div>
      {/each}
    </div>
  {/each}
</div>

<style>
  .card-stacks { display: flex; gap: 8px; flex-wrap: wrap; }
  .stack { position: relative; width: 90px; height: calc(18px * 4 + 32px); }
  .strip {
    position: absolute; left: 0; right: 0; height: 32px;
    border-radius: 6px 6px 0 0; padding: 4px 6px;
    display: flex; align-items: center; gap: 3px;
    box-shadow: 0 2px 3px rgba(0,0,0,.3); overflow: hidden;
  }
  .strip.face-down { opacity: .5; }
  .strip-name { font-size: .6rem; font-weight: bold; color: white; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .strip-arrow { font-size: .5rem; color: rgba(255,255,255,.7); white-space: nowrap; }
  .strip-pip { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; border: 1px solid rgba(255,255,255,.4); }
</style>
