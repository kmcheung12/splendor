<!-- frontend/src/components/BoardCard.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import { BALL } from '../lib/tokens'
  import type { PokemonCard } from '../lib/types'
  import { COL, CARDBG, TIER_BAR, spriteUrl, groupCost } from '../lib/gameData'

  export let card: PokemonCard
  export let tier: string
  export let size: 'sm' | 'lg' = 'sm'
  export let jumping = false
  export let highlighted = false
  export let catchReveal = false

  const dispatch = createEventDispatcher<{ artclick: void }>()

  $: color = card.bonus[0] ?? 'black'
  $: lg = size === 'lg'
  $: groupedCost = groupCost(card.cost)
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
  class="bcard"
  class:lg
  class:bcard-highlight={highlighted}
  class:catch-reveal={catchReveal}
  class:jumping
  style="background:{CARDBG[color] ?? '#2a2a2a'}"
  on:click
  on:keydown
  role="button"
  tabindex="0"
>
  <div class="bcard-bar" style="background:{TIER_BAR[tier] ?? '#888'}"></div>
  <div class="bcard-head">
    <div class="bcard-names">
      <span class="bcard-name">{card.name}</span>
      {#if card.evolve_into}
        <span class="bcard-evo-row">
          <span class="bcard-evo">{card.evolve_into}</span>
          {#if card.evolve?.length}
            <span class="bcard-evo-sep">‹</span>
            {#each groupCost(card.evolve) as g}
              <span class="cv-u cv-u-xs" style="--gc:{COL[g.c]}">
                <span class="cv-n cv-n-xs">{g.n}</span>
                <img class="cv-mb cv-mb-xs" src={BALL[g.c]} alt={g.c} width="8" height="8" draggable="false">
              </span>
            {/each}
          {/if}
        </span>
      {/if}
    </div>
    <span class="bcard-bonus" style="background:{CARDBG[color] ?? '#2a2a2a'}">
      <span class="bcard-bonus-bar" style="background:{COL[color] ?? '#888'}"></span>
      {#each card.bonus as b}
        <img src={BALL[b]} alt={b} draggable="false">
      {/each}
    </span>
  </div>
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="bcard-art" on:click={() => dispatch('artclick')}>
    <img src={spriteUrl(card.name)} alt={card.name} draggable="false">
  </div>
  {#if groupedCost.length}
    <div class="bcard-cost">
      {#if groupedCost.length > 3}
        <div class="cv cv-stack">
          <div class="cv-row">
            {#each groupedCost.slice(0, groupedCost.length - 3) as g}
              <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} draggable="false"></span>
            {/each}
          </div>
          <div class="cv-row">
            {#each groupedCost.slice(-3) as g}
              <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} draggable="false"></span>
            {/each}
          </div>
        </div>
      {:else}
        <div class="cv">
          {#each groupedCost as g}
            <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} draggable="false"></span>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
  <div class="bcard-pts" style="box-shadow:inset 0 0 0 2px {COL[color] ?? '#888'}">{card.point}</div>
</div>

<style>
  /* ── Base (sm: 100×80) ── */
  .bcard {
    width: 100px; height: 80px; flex: none; position: relative; color: #fff;
    border: 2px solid #0c0d12; border-radius: 3px; overflow: hidden;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.10), 2px 2px 0 rgba(0,0,0,.42);
    display: flex; flex-direction: column; cursor: pointer; box-sizing: border-box;
  }
  .bcard img { image-rendering: pixelated; display: block; }
  .bcard.bcard-highlight { outline: 2px solid #ffd23f; }
  .bcard.bcard-highlight:hover { filter: brightness(1.1); }
  .bcard.jumping { overflow: visible; z-index: 10; }
  .bcard.jumping .bcard-art img { animation: poke-jump-sm 480ms cubic-bezier(.23,.54,.46,.77) forwards; }
  @keyframes poke-jump-sm {
    0%   { transform: translateY(0); }
    50%  { transform: translateY(-18px); animation-timing-function: cubic-bezier(.54,.23,.77,.46); }
    100% { transform: translateY(0); }
  }

  .bcard-bar { height: 3px; flex: none; }
  .bcard-head { display: flex; justify-content: space-between; align-items: flex-start; padding: 3px 4px 0; gap: 3px; }
  .bcard-names { min-width: 0; display: flex; flex-direction: column; }
  .bcard-name { font-family: 'Silkscreen', monospace; font-weight: 700; font-size: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bcard-evo-row { display: flex; gap: 3px; align-items: center; flex-wrap: nowrap; overflow: hidden; }
  .bcard-evo { font-family: 'Silkscreen', monospace; font-size: 6px; color: rgba(255,255,255,.55); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 1; min-width: 0; }
  .bcard-evo-sep { font-size: 6px; color: rgba(255,255,255,.3); flex: none; }

  .bcard-bonus {
    position: relative; flex: none; width: 15px; height: 19px; border-radius: 3px; overflow: hidden;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.18), 0 0 0 1px rgba(0,0,0,.55), 1px 1px 0 rgba(0,0,0,.4);
  }
  .bcard-bonus-bar { position: absolute; top: 0; left: 0; right: 0; height: 2px; }
  .bcard-bonus img { width: 10px; height: 10px; }
  .bcard-bonus img + img { margin-top: -2px; }

  .bcard-art { flex: 1; display: grid; place-items: center; min-height: 0; cursor: pointer; }
  .bcard-art img { width: 38px; height: 38px; }

  .bcard-cost { display: flex; align-items: flex-end; padding: 0 22px 3px 4px; }
  .bcard-pts {
    position: absolute; right: 3px; bottom: 3px; width: 18px; height: 18px;
    display: grid; place-items: center; border-radius: 3px;
    background: #0c0d12; font-family: 'Press Start 2P', monospace; font-size: 8px; color: #fff;
  }

  /* ── Catch cost tokens (sm: 16px) ── */
  .cv { display: flex; flex-wrap: wrap; gap: 2px; align-items: center; }
  .cv-stack { display: flex; flex-direction: column; gap: 2px; align-items: flex-start; }
  .cv-row { display: flex; gap: 2px; align-items: center; }
  .cv-u {
    position: relative; width: 20px; height: 20px; border-radius: 50%; flex: none;
    background: #0c0d12; display: grid; place-items: center;
    box-shadow: inset 0 0 0 2px var(--gc, #555);
  }
  .cv-n { font-family: 'Press Start 2P', monospace; font-size: 7px; color: #fff; text-shadow: 1px 1px 0 rgba(0,0,0,.6); }
  .cv-mb { position: absolute; right: -3px; bottom: -3px; image-rendering: pixelated; display: block; width: 10px; height: 10px; }

  /* ── Evolve cost tokens (sm: 14px = catch-2) ── */
  .cv-u-xs { width: 16px; height: 16px; }
  .cv-n-xs { font-size: 5px; }
  .cv-mb-xs { width: 8px; height: 8px; right: -2px; bottom: -2px; }

  .catch-reveal { animation: catch-reveal 550ms ease-out both; }
  @keyframes catch-reveal {
    0%   { opacity: 0; transform: translateY(6px); }
    100% { opacity: 1; transform: translateY(0); }
  }

  /* ── Large (300×240) ── */
  .bcard.lg {
    width: 300px; height: 240px;
    border: 3px solid #0c0d12; border-radius: 3px;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.12), 4px 4px 0 rgba(0,0,0,.5);
  }
  .bcard.lg.jumping .bcard-art img { animation: poke-jump-lg 480ms cubic-bezier(.23,.54,.46,.77) forwards; }
  @keyframes poke-jump-lg {
    0%   { transform: translateY(0); }
    50%  { transform: translateY(-22px); animation-timing-function: cubic-bezier(.54,.23,.77,.46); }
    100% { transform: translateY(0); }
  }
  .bcard.lg .bcard-bar { height: 7px; }
  .bcard.lg .bcard-head { padding: 7px 9px 0; gap: 6px; }
  .bcard.lg .bcard-names { gap: 3px; }
  .bcard.lg .bcard-name { font-size: 16px; }
  .bcard.lg .bcard-evo { font-size: 12px; color: rgba(255,255,255,.6); }
  .bcard.lg .bcard-evo-sep { font-size: 10px; }
  .bcard.lg .bcard-bonus { width: 24px; height: 30px; border-radius: 4px; }
  .bcard.lg .bcard-bonus-bar { height: 3px; }
  .bcard.lg .bcard-bonus img { width: 13px; height: 13px; }
  .bcard.lg .bcard-bonus img + img { margin-top: -3px; }
  .bcard.lg .bcard-art img { width: 114px; height: 114px; }
  .bcard.lg .bcard-cost { padding: 0 60px 6px 9px; }
  .bcard.lg .bcard-pts { right: 7px; bottom: 7px; width: 39px; height: 39px; border-radius: 6px; font-size: 16px; }
  /* catch cost tokens lg: 26px */
  .bcard.lg .cv { gap: 4px; }
  .bcard.lg .cv-stack { gap: 3px; }
  .bcard.lg .cv-row { gap: 4px; }
  .bcard.lg .cv-u { width: 30px; height: 30px; }
  .bcard.lg .cv-n { font-size: 11px; }
  .bcard.lg .cv-mb { width: 13px; height: 13px; right: -3px; bottom: -3px; }
  /* evolve cost tokens lg: 24px = catch-2 */
  .bcard.lg .cv-u-xs { width: 24px; height: 24px; }
  .bcard.lg .cv-n-xs { font-size: 10px; }
  .bcard.lg .cv-mb-xs { width: 12px; height: 12px; right: -3px; bottom: -3px; }
</style>
