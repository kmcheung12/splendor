<!-- frontend/src/components/CardDetailModal.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import BoardCard from './BoardCard.svelte'
  import type { PokemonCard } from '../lib/types'

  export let card: PokemonCard
  export let tier: string
  export let actions: { id: number; label: string }[] = []

  const dispatch = createEventDispatcher<{ close: void; action: number }>()

  let jumping = false
  function startJump() {
    if (jumping) return
    jumping = true
    setTimeout(() => { jumping = false }, 480)
  }
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="backdrop" on:click={() => dispatch('close')}>
  <div class="container" on:click|stopPropagation>
    <BoardCard {card} {tier} size="lg" {jumping} on:artclick={startJump} />

    <div class="btns">
      {#each actions as { id, label }}
        <button class="action-btn" on:click={() => dispatch('action', id)}>{label}</button>
      {/each}
      <button class="close-btn" on:click={() => dispatch('close')}>Close</button>
    </div>
  </div>
</div>

<style>
  .backdrop {
    position: fixed; inset: 0;
    background: rgba(5,5,12,.72);
    display: grid; place-items: center; z-index: 60;
    animation: fade .14s ease;
  }
  @keyframes fade { from { opacity: 0; } to { opacity: 1; } }

  .container {
    display: flex; flex-direction: column; align-items: center; gap: 10px;
    animation: pop .2s cubic-bezier(.34,1.4,.64,1);
  }
  @keyframes pop {
    from { opacity: 0; transform: scale(.88) translateY(8px); }
    to   { opacity: 1; transform: scale(1) translateY(0); }
  }

  .btns { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
  .action-btn {
    background: #27ae60; color: #fff; border: none; border-radius: 6px;
    font-family: 'Silkscreen', monospace; font-size: 10px;
    padding: 8px 18px; cursor: pointer;
  }
  .action-btn:hover { filter: brightness(1.15); }
  .close-btn {
    background: rgba(255,255,255,.1); color: rgba(255,255,255,.7);
    border: 1px solid rgba(255,255,255,.2); border-radius: 6px;
    font-family: 'Silkscreen', monospace; font-size: 10px;
    padding: 8px 18px; cursor: pointer;
  }
  .close-btn:hover { background: rgba(255,255,255,.18); color: #fff; }
</style>
