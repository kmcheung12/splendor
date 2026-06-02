<script lang="ts">
  let view: 'setup' | 'lobby' | 'game' = 'setup'
</script>

<main>
  {#if view === 'setup'}
    <p>Setup (coming soon)</p>
  {:else if view === 'lobby'}
    <p>Lobby (coming soon)</p>
  {:else}
    <p>Game (coming soon)</p>
  {/if}
</main>
