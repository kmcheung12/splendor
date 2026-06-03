<!-- frontend/src/App.svelte -->
<script lang="ts">
  import { connect } from './lib/ws'
  import { gameState, lobbyState, gameOver } from './lib/gameStore'
  import Lobby from './components/Lobby.svelte'
  import Board from './components/Board.svelte'
  import PlayerPanel from './components/PlayerPanel.svelte'
  import StatusChip from './components/StatusChip.svelte'
  import GameOver from './components/GameOver.svelte'

  let view: 'setup' | 'lobby' | 'game' = 'setup'
  let gameId = ''

  let numPlayers = 2
  let agentTypes = ['random', 'random', 'random', 'random']
  let delayMs = 800

  const AGENT_OPTIONS = ['random', 'early-capture', 'high-point', 'bonus-engine', 'evolution-chain', 'denial', 'mcts']

  let error: string | null = null

  async function createGame() {
    error = null
    try {
      const res = await fetch('/game/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_players: numPlayers,
          agent_types: agentTypes.slice(0, numPlayers),
          delay_ms: delayMs,
        }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      gameId = data.game_id
      connect(gameId)
      view = 'lobby'
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to create game'
    }
  }

  async function joinGame(code: string) {
    if (!code.trim()) return
    error = null
    try {
      const res = await fetch(`/join/${code.toUpperCase()}`)
      if (!res.ok) throw new Error('Invalid code or game not found')
      const data = await res.json()
      if (!data.game_id) throw new Error('Invalid code or game not found')
      gameId = data.game_id
      connect(gameId)
      view = 'lobby'
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to join game'
    }
  }

  let joinCode = ''
</script>

<div class="app">
  {#if view === 'setup'}
    <div class="setup">
      <h1>Pokemon Splendor</h1>
      {#if error}
        <div class="error">{error}</div>
      {/if}

      <section>
        <h2>Create Game</h2>
        <label>Players: <input type="number" min="2" max="4" bind:value={numPlayers} /></label>
        {#each Array(numPlayers) as _, i}
          <label>Slot {i+1}:
            <select bind:value={agentTypes[i]}>
              {#each AGENT_OPTIONS as opt}<option>{opt}</option>{/each}
            </select>
          </label>
        {/each}
        <label>Delay (ms): <input type="number" min="0" max="3000" step="100" bind:value={delayMs} /></label>
        <button on:click={createGame}>Create &amp; Host</button>
      </section>

      <section>
        <h2>Join Game</h2>
        <input placeholder="Join code" bind:value={joinCode} maxlength={4} style="text-transform:uppercase" />
        <button on:click={() => joinGame(joinCode)} disabled={!joinCode.trim()}>Join</button>
      </section>
    </div>

  {:else if view === 'lobby'}
    <Lobby on:started={() => { view = 'game' }} />

  {:else if view === 'game'}
    {#if $gameState}
      <div class="game-layout">
        {#each $gameState.players.slice(0, Math.floor($gameState.players.length / 2)) as player}
          <PlayerPanel {player} position="top" />
        {/each}

        <div class="center">
          <StatusChip />
          <Board />
        </div>

        {#each $gameState.players.slice(Math.floor($gameState.players.length / 2)) as player}
          <PlayerPanel {player} position="bottom" />
        {/each}
      </div>
    {/if}

    {#if $gameOver}
      <GameOver winner={$gameOver.winner} scores={$gameOver.scores} />
    {/if}
  {/if}
</div>

<style>
  :global(body) { margin: 0; background: #0d0d1a; font-family: sans-serif; }
  .app { min-height: 100vh; color: white; }
  .setup {
    max-width: 400px; margin: 60px auto; padding: 24px;
    background: rgba(255,255,255,.07); border-radius: 12px;
    display: flex; flex-direction: column; gap: 24px;
  }
  h1 { text-align: center; color: #f1c40f; }
  section { display: flex; flex-direction: column; gap: 8px; }
  label { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-size: .9rem; }
  input, select { background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2); border-radius: 4px; color: white; padding: 4px 8px; }
  button { background: #27ae60; color: white; border: none; border-radius: 6px; padding: 8px 16px; cursor: pointer; font-size: .9rem; }
  button:hover { background: #2ecc71; }
  button:disabled { background: #555; cursor: not-allowed; }
  .error { background: rgba(231,76,60,.2); border: 1px solid rgba(231,76,60,.4); color: #e74c3c; border-radius: 6px; padding: 8px 12px; font-size: .85rem; }
  .game-layout { display: flex; flex-direction: column; min-height: 100vh; padding: 8px; gap: 8px; }
  .center { display: flex; flex-direction: column; align-items: center; gap: 8px; flex: 1; }
</style>
