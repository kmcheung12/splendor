<script lang="ts">
  import { fly } from 'svelte/transition'
  import { sendAction } from '../lib/ws'
  import { createEventDispatcher } from 'svelte'

  export let anchorX = 0
  export let anchorY = 0
  export let actions: number[] = []
  export let labels: string[] = []

  const dispatch = createEventDispatcher<{ cancel: void; confirm: { actionId: number } }>()

  function confirm(actionId: number) {
    sendAction(actionId)
    dispatch('confirm', { actionId })
    dispatch('cancel')
  }
</script>

{#if actions.length > 0}
  <div
    class="popup"
    style="left:{anchorX}px; top:{anchorY}px"
    transition:fly={{ y: -8, duration: 150 }}
  >
    {#each actions as id, i}
      <button class="action-btn" on:click={() => confirm(id)}>{labels[i] ?? id}</button>
    {/each}
    <button class="cancel-btn" on:click={() => dispatch('cancel')}>Cancel</button>
  </div>
{/if}

<style>
  .popup {
    position: fixed; z-index: 1030;
    background: #1a1a2e; border: 1px solid rgba(255,255,255,.2);
    border-radius: 8px; padding: 8px;
    display: flex; flex-direction: column; gap: 4px;
    box-shadow: 0 4px 20px rgba(0,0,0,.6);
    min-width: 160px;
  }
  .action-btn, .cancel-btn {
    padding: 6px 10px; border-radius: 5px; border: none; cursor: pointer;
    font-size: .8rem; text-align: left;
  }
  .action-btn { background: rgba(255,255,255,.1); color: white; }
  .action-btn:hover { background: rgba(241,196,15,.3); }
  .cancel-btn { background: transparent; color: rgba(255,255,255,.5); border: 1px solid rgba(255,255,255,.15); margin-top: 4px; }
  .cancel-btn:hover { background: rgba(255,255,255,.08); color: white; }
</style>
