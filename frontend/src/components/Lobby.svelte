<!-- frontend/src/components/Lobby.svelte -->
<script lang="ts">
  import { lobbyState, mySlot, isHost } from '../lib/gameStore'
  import { claimSlot, releaseSlot, renameSlot, startGame, setDelay } from '../lib/ws'
  import { createEventDispatcher } from 'svelte'

  const dispatch = createEventDispatcher<{ started: void }>()

  let playerName = 'Player'
  let copied = false

  function handleNameInput() {
    if ($mySlot !== null) renameSlot(playerName)
  }

  function claim(idx: number) {
    claimSlot(idx, playerName)
    mySlot.set(idx)
  }
  function release() {
    releaseSlot()
  }
  // Auto-sit in seat 0 when host first enters the lobby
  let didAutoClaim = false
  $: if ($isHost && $mySlot === null && !didAutoClaim && $lobbyState) {
    didAutoClaim = true
    claim(0)
  }

  function handleStart() {
    startGame()
    dispatch('started')
  }
  async function copyCode() {
    if (!$lobbyState) return
    await navigator.clipboard.writeText($lobbyState.join_code)
    copied = true
    setTimeout(() => { copied = false }, 1500)
  }
</script>

{#if $lobbyState}
  <div class="lobby">
    <div class="code-row">
      <div>
        <div class="code-label">Join code</div>
        <span class="code">{$lobbyState.join_code}</span>
      </div>
      <button class="copy-btn" on:click={copyCode} title="Copy code">
        {copied ? '✓ Copied' : '⎘ Copy'}
      </button>
    </div>

    <label class="name-row">
      Your name: <input bind:value={playerName} maxlength={16} on:input={handleNameInput} />
    </label>

    <div class="slots">
      {#each $lobbyState.slots as slot}
        <div class="slot" class:claimed={slot.claimed_by !== null}>
          <span class="slot-idx">Seat {slot.index + 1}</span>
          <span class="agent">{slot.claimed_by ? '' : slot.agent_type}</span>
          {#if slot.claimed_by}
            <span class="claimer">👤 {slot.claimed_by}</span>
            {#if $mySlot === slot.index}
              <button class="release-btn" on:click={release}>Leave</button>
            {/if}
          {:else}
            <button on:click={() => claim(slot.index)} disabled={$mySlot !== null}>Sit</button>
          {/if}
        </div>
      {/each}
    </div>

    {#if $isHost}
      <label class="delay-row">
        Turn delay: <strong>{$lobbyState.delay_ms}ms</strong>
        <input type="range" min="0" max="3000" step="100"
          value={$lobbyState.delay_ms}
          on:change={(e) => setDelay(+(e.target as HTMLInputElement).value)}
        />
      </label>
    {/if}

    <div class="footer">
      <span class="spectators">{$lobbyState.spectators} spectator(s)</span>
      {#if $isHost}
        <button class="start-btn" on:click={handleStart}>▶ Start Game</button>
      {:else}
        <span class="waiting">Waiting for host to start…</span>
      {/if}
    </div>
  </div>
{/if}

<style>
  .lobby { max-width: 480px; margin: 60px auto; padding: 24px; background: rgba(255,255,255,.07); border-radius: 12px; color: white; display: flex; flex-direction: column; gap: 16px; }

  .code-row { display: flex; align-items: center; justify-content: space-between; background: rgba(241,196,15,.08); border: 1px solid rgba(241,196,15,.25); border-radius: 8px; padding: 12px 16px; }
  .code-label { font-size: .7rem; color: rgba(255,255,255,.5); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 2px; }
  .code { font-family: monospace; font-size: 1.8rem; font-weight: bold; color: #f1c40f; letter-spacing: .2em; }
  .copy-btn { background: rgba(241,196,15,.15); color: #f1c40f; border: 1px solid rgba(241,196,15,.3); border-radius: 6px; padding: 6px 12px; cursor: pointer; font-size: .8rem; white-space: nowrap; }
  .copy-btn:hover { background: rgba(241,196,15,.3); }

  .name-row { display: flex; gap: 8px; align-items: center; }
  .name-row input { background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2); border-radius: 4px; color: white; padding: 4px 8px; flex: 1; }

  .slots { display: flex; flex-direction: column; gap: 6px; }
  .slot { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: rgba(255,255,255,.05); border-radius: 8px; }
  .slot.claimed { background: rgba(52,199,89,.08); border: 1px solid rgba(52,199,89,.2); }
  .slot-idx { font-weight: bold; min-width: 50px; font-size: .9rem; }
  .agent { color: rgba(255,255,255,.4); font-size: .75rem; flex: 1; }
  .claimer { color: #2ecc71; font-size: .85rem; flex: 1; }

  button { background: rgba(255,255,255,.1); color: white; border: 1px solid rgba(255,255,255,.2); border-radius: 5px; padding: 4px 10px; cursor: pointer; font-size: .85rem; }
  button:hover { background: rgba(255,255,255,.2); }
  button:disabled { opacity: .35; cursor: not-allowed; }
  .release-btn { background: rgba(231,76,60,.12); border-color: rgba(231,76,60,.3); color: #e74c3c; }
  .release-btn:hover { background: rgba(231,76,60,.25); }

  .delay-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-size: .85rem; }
  .delay-row input[type=range] { flex: 1; }

  .footer { display: flex; justify-content: space-between; align-items: center; padding-top: 4px; border-top: 1px solid rgba(255,255,255,.08); }
  .spectators { color: rgba(255,255,255,.4); font-size: .8rem; }
  .waiting { color: rgba(255,255,255,.4); font-size: .85rem; font-style: italic; }
  .start-btn { background: #27ae60; border-color: #27ae60; color: white; font-weight: bold; padding: 10px 24px; font-size: .95rem; }
  .start-btn:hover { background: #2ecc71; }
</style>
