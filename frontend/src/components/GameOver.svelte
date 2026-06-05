<!-- frontend/src/components/GameOver.svelte -->
<script lang="ts">
  import { fly } from 'svelte/transition'
  import { onMount } from 'svelte'

  export let winner: string
  export let scores: Record<string, number>
  export let rounds: number

  onMount(() => {
    const fn = (window as any).confetti
    if (fn) {
      fn({ particleCount: 120, spread: 80, origin: { y: 0.7 } })
      setTimeout(() => fn({ particleCount: 80, spread: 60, origin: { y: 0.6 } }), 400)
    }
  })
</script>

<div class="overlay" transition:fly={{ y: -40, duration: 400 }}>
  <div class="banner">
    <span class="crown">👑</span>
    <h2>{winner} wins!</h2>
    <div class="rounds">{rounds} rounds</div>
    <div class="scores">
      {#each Object.entries(scores).sort((a,b) => b[1]-a[1]) as [name, pts]}
        <div class="score-row" class:winner={name === winner}>
          <span>{name}</span><span>{pts} pts</span>
        </div>
      {/each}
    </div>
    <button on:click={() => location.reload()}>New Game</button>
  </div>
</div>

<style>
  .overlay {
    position: fixed; top: 0; left: 0; right: 0;
    display: flex; justify-content: center;
    z-index: 200; pointer-events: none;
  }
  .banner {
    pointer-events: all;
    margin-top: 24px; padding: 20px 32px;
    background: rgba(10,10,30,.95); border: 1px solid rgba(241,196,15,.4);
    border-radius: 12px; text-align: center; color: white;
    box-shadow: 0 8px 32px rgba(0,0,0,.6);
    min-width: 240px;
  }
  .crown { font-size: 2rem; }
  h2 { margin: 8px 0; color: #f1c40f; font-size: 1.4rem; }
  .rounds { font-size: .8rem; color: rgba(255,255,255,.5); margin-bottom: 4px; }
  .scores { margin: 12px 0; display: flex; flex-direction: column; gap: 4px; }
  .score-row { display: flex; justify-content: space-between; gap: 24px; font-size: .9rem; }
  .score-row.winner { color: #f1c40f; font-weight: bold; }
  button { background: #27ae60; color: white; border: none; border-radius: 6px; padding: 8px 20px; cursor: pointer; margin-top: 8px; }
  button:hover { background: #2ecc71; }
</style>
