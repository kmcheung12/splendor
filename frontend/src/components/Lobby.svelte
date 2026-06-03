<!-- frontend/src/components/Lobby.svelte -->
<script lang="ts">
  import { lobbyState, mySlot, isHost } from '../lib/gameStore'
  import { claimSlot, releaseSlot, startGame, setDelay } from '../lib/ws'
  import { createEventDispatcher } from 'svelte'

  const dispatch = createEventDispatcher<{ started: void }>()

  let playerName = 'Player'

  function claim(idx: number) {
    claimSlot(idx, playerName)
    mySlot.set(idx)
  }
  function release() {
    releaseSlot()
  }
  function handleStart() {
    startGame()
    dispatch('started')
  }
</script>

{#if $lobbyState}
  <div class="lobby">
    <h2>Game: <span class="code">{$lobbyState.join_code}</span></h2>
    <p>Share this code with friends to join.</p>

    <label class="name-row">
      Your name: <input bind:value={playerName} maxlength={16} />
    </label>

    <div class="slots">
      {#each $lobbyState.slots as slot}
        <div class="slot" class:claimed={slot.claimed_by !== null}>
          <span class="slot-idx">Slot {slot.index + 1}</span>
          <span class="agent">default: {slot.agent_type}</span>
          {#if slot.claimed_by}
            <span class="claimer">{slot.claimed_by}</span>
            {#if $mySlot === slot.index}
              <button on:click={release}>Release</button>
            {/if}
          {:else}
            <button on:click={() => claim(slot.index)} disabled={$mySlot !== null}>Claim</button>
          {/if}
        </div>
      {/each}
    </div>

    <label class="delay-row">
      Turn delay: {$lobbyState.delay_ms}ms
      <input type="range" min="0" max="3000" step="100"
        value={$lobbyState.delay_ms}
        on:input={(e) => setDelay(+(e.target as HTMLInputElement).value)}
        disabled={!$isHost}
      />
    </label>

    <div class="footer">
      <span class="spectators">{$lobbyState.spectators} spectator(s)</span>
      {#if $isHost}
        <button class="start-btn" on:click={handleStart}>Start Game</button>
      {/if}
    </div>
  </div>
{/if}

<style>
  .lobby { max-width: 480px; margin: 60px auto; padding: 24px; background: rgba(255,255,255,.07); border-radius: 12px; color: white; }
  h2 { margin-bottom: 4px; }
  .code { font-family: monospace; font-size: 1.4rem; color: #f1c40f; letter-spacing: .15em; }
  .name-row { display: flex; gap: 8px; align-items: center; margin: 12px 0; }
  .name-row input { background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2); border-radius: 4px; color: white; padding: 4px 8px; }
  .slots { display: flex; flex-direction: column; gap: 6px; margin: 16px 0; }
  .slot { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: rgba(255,255,255,.05); border-radius: 8px; }
  .slot.claimed { background: rgba(241,196,15,.1); }
  .slot-idx { font-weight: bold; min-width: 50px; }
  .agent { color: rgba(255,255,255,.5); font-size: .8rem; flex: 1; }
  .claimer { color: #2ecc71; font-size: .85rem; }
  button { background: rgba(255,255,255,.1); color: white; border: 1px solid rgba(255,255,255,.2); border-radius: 5px; padding: 4px 10px; cursor: pointer; }
  button:hover { background: rgba(255,255,255,.2); }
  button:disabled { opacity: .4; cursor: not-allowed; }
  .delay-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .delay-row input { flex: 1; }
  .footer { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; }
  .spectators { color: rgba(255,255,255,.5); font-size: .8rem; }
  .start-btn { background: #27ae60; border-color: #27ae60; font-weight: bold; padding: 8px 20px; }
  .start-btn:hover { background: #2ecc71; }
</style>
