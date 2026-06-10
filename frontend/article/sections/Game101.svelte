<script lang="ts">
  import { onMount } from 'svelte';
  import { loadReplaySnapshots, type ReplaySnapshots } from '../replay/snapshot';
  import GameReplayPlayer from '../replay/GameReplayPlayer.svelte';

  let snapshots: ReplaySnapshots | null = null;
  // Pick a mid-game turn so the board has cards bought and tokens distributed —
  // a richer illustration than the empty opening state.
  $: midSnapshot = snapshots
    ? snapshots.turns[Math.min(snapshots.turns.length - 1, Math.floor(snapshots.turns.length * 0.4))]
    : null;

  onMount(async () => {
    try {
      snapshots = await loadReplaySnapshots('v6-seed42');
    } catch (e) {
      console.warn('Game101 snapshot load failed:', e);
    }
  });
</script>

<section class="game101">
  <div class="prose">
    <h2>Splendor in 90 seconds</h2>
    <p>
      Players take turns. Each turn you do one of three things: grab
      tokens, reserve a card for later, or buy a card you can afford.
      Cards give you points and bonuses that make future cards cheaper.
      The first player to fifteen points wins the round.
    </p>
    <p class="aside">
      This article is about a variant called Pokémon Splendor — same rules,
      but with Pokémon cards and a tier system that rewards building
      evolution chains.
    </p>
  </div>
  <aside class="board">
    {#if midSnapshot}
      <GameReplayPlayer
        snapshot={midSnapshot.snapshot}
        description={midSnapshot.description} />
    {/if}
  </aside>
</section>

<style>
  .game101 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4rem;
    padding: 8rem 4rem;
    max-width: 90rem;
    margin: 0 auto;
    align-items: center;
  }
  .prose h2 {
    font-size: clamp(2rem, 4vw, 3rem);
    margin: 0 0 1.5rem;
    letter-spacing: -0.02em;
  }
  .prose p { font-size: 1.15rem; color: #d6d3cb; }
  .aside { color: var(--muted); font-size: 1rem; }
  .board {
    padding: 1rem;
    background: rgba(255,255,255,0.02);
    border-radius: 12px;
    min-height: 24rem;
  }
  @media (max-width: 800px) {
    .game101 { grid-template-columns: 1fr; }
  }
</style>
