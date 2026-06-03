<script lang="ts">
  import type { PlayerState } from '../lib/types'
  import CardStack from './CardStack.svelte'
  import { activePlayer } from '../lib/gameStore'
  import { fly } from 'svelte/transition'
  import { cubicOut } from 'svelte/easing'

  export let player: PlayerState
  export let position: 'top' | 'bottom' | 'left' | 'right' = 'bottom'

  const TOKEN_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']
  const TOKEN_COLORS: Record<string, string> = {
    red: '#e74c3c', yellow: '#f1c40f', blue: '#3498db',
    pink: '#e91e96', black: '#555', master: '#f39c12',
  }

  // Tokens fly in from the direction of the board (which is toward the center)
  $: flyY = position === 'top' ? 60 : -60

  $: isActive = $activePlayer === player.name
  $: tokenIconsKeyed = (() => {
    return TOKEN_ORDER.flatMap(t => {
      const n = player.tokens[t] ?? 0
      return Array.from({ length: n }, (_, j) => ({ t, key: `${t}-${j}` }))
    })
  })()
</script>

<div class="panel" class:active={isActive} data-position={position}>
  <div class="identity">
    <span class="pname">{player.name}</span>
    <span class="pts">{player.points} pts</span>
  </div>
  <div class="tokens">
    {#each tokenIconsKeyed as {t, key} (key)}
      <span
        class="tok"
        style="background:{TOKEN_COLORS[t]}"
        title={t}
        in:fly={{ y: flyY, duration: 350, easing: cubicOut }}
      ></span>
    {/each}
    {#if tokenIconsKeyed.length === 0}<span class="none">no tokens</span>{/if}
  </div>
  <CardStack cards={player.cards} />
  {#if player.reserved_cards.length > 0}
    <div class="reserved-label">Reserved</div>
    <CardStack cards={player.reserved_cards} />
  {/if}
</div>

<style>
  .panel {
    display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
    padding: 8px 12px; border-radius: 10px;
    background: rgba(255,255,255,.06); border: 2px solid transparent;
    transition: border-color .3s, box-shadow .3s;
  }
  .panel.active { border-color: #f1c40f; box-shadow: 0 0 12px rgba(241,196,15,.4); }
  .identity { display: flex; flex-direction: column; gap: 2px; min-width: 70px; }
  .pname { font-weight: bold; color: white; font-size: .85rem; }
  .pts { font-size: 1.1rem; font-weight: bold; color: #f1c40f; }
  .tokens { display: flex; flex-wrap: wrap; gap: 3px; }
  .tok { width: 14px; height: 14px; border-radius: 50%; border: 1px solid rgba(255,255,255,.3); }
  .none { font-size: .7rem; color: rgba(255,255,255,.4); }
  .reserved-label { font-size: .6rem; color: rgba(255,255,255,.5); width: 100%; }
</style>
