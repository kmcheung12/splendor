<!-- frontend/src/App.svelte -->
<script lang="ts">
  import { onMount } from 'svelte'
  import { connect, claimSlot, startGame } from './lib/ws'
  import { gameState, gameOver, playerNames, lobbyState, mySlot } from './lib/gameStore'
  import { tutorialMode, initTutorial } from './lib/tutorialStore'
  import { BOARD_SELECTOR_MAP } from './lib/tutorial'
  import Lobby from './components/Lobby.svelte'
  import Board from './components/Board.svelte'
  import PlayerPanel from './components/PlayerPanel.svelte'
  import GameOver from './components/GameOver.svelte'
  import TutorialOverlay from './components/TutorialOverlay.svelte'
  import TutorialController from './components/TutorialController.svelte'
  import MobileLayout from './components/MobileLayout.svelte'

  let isMobile = false
  onMount(() => {
    const mq = window.matchMedia('(max-width: 768px)')
    isMobile = mq.matches
    const handler = (e: MediaQueryListEvent) => { isMobile = e.matches }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  })

  let view: 'setup' | 'lobby' | 'game' = 'setup'
  let gameId = ''

  let numPlayers = 4
  let agentTypes = ['mcts', 'mcts', 'mctsrl', 'mctsrl']
  let delayMs = 800

  const AGENT_OPTIONS = ['mcts', 'mctsrl', 'denial', 'evolution-chain', 'bonus-engine', 'high-point', 'early-capture', 'random']

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

  async function createTutorialGame() {
    error = null
    try {
      const res = await fetch('/game/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_players: 4,
          agent_types: ['human', 'random', 'random', 'random'],
          delay_ms: 1200,
          first_player_index: 0,
        }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      gameId = data.game_id
      initTutorial()
      connect(gameId)
      view = 'game'
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to create tutorial game'
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

  $: if ($tutorialMode && $lobbyState && $mySlot === null) {
    claimSlot(0, 'Player')
    mySlot.set(0)
    startGame()
  }
</script>

<div class="app">
  {#if view === 'setup'}
    <div class="setup">
      <h1>Pokemon Splendor</h1>
      {#if error}
        <div class="error">{error}</div>
      {/if}

      <section>
        <button class="btn-tutorial" on:click={createTutorialGame}>▶ Play Tutorial</button>
      </section>

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
    {#if isMobile}
      <div class="mobile-root">
        {#if $gameState}
          <MobileLayout />
        {/if}
        {#if $gameOver}
          <GameOver winner={$gameOver.winner} scores={$gameOver.scores} rounds={$gameOver.rounds} />
        {/if}
      </div>
    {:else}
      {#if $gameState}
        {@const players = $gameState.players}
        <div class="game-layout">
          <div class="row-1">
            {#if players[0]}<PlayerPanel player={players[0]} displayName={$playerNames[players[0].name] ?? players[0].name} position="top-left" />{/if}
            <div class="board-col">
<Board />
            </div>
            {#if players[1]}<PlayerPanel player={players[1]} displayName={$playerNames[players[1].name] ?? players[1].name} position="top-right" />{/if}
          </div>
          {#if players[2] || players[3]}
            <div class="row-2">
              {#if players[3]}<PlayerPanel player={players[3]} displayName={$playerNames[players[3].name] ?? players[3].name} position="bottom-left" />{/if}
              {#if players[2]}<PlayerPanel player={players[2]} displayName={$playerNames[players[2].name] ?? players[2].name} position="bottom-right" />{/if}
            </div>
          {/if}
        </div>
      {/if}

      {#if $tutorialMode}
        <TutorialController />
        <TutorialOverlay selectorMap={BOARD_SELECTOR_MAP} />
      {/if}

      {#if $gameOver}
        <GameOver winner={$gameOver.winner} scores={$gameOver.scores} rounds={$gameOver.rounds} />
      {/if}
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
  .btn-tutorial {
    background: #2c3e8c;
    font-size: 1rem;
    padding: 12px 20px;
    border-radius: 8px;
    letter-spacing: 0.03em;
  }
  .btn-tutorial:hover { background: #3a52b4; }
  .game-layout { display: flex; flex-direction: column; gap: 8px; padding: 8px; min-height: 100vh; }
  .row-1 {
    display: grid;
    grid-template-columns: minmax(0, 20%) minmax(60%, 1fr) minmax(0, 20%);
    gap: 8px; align-items: center;
  }
  .row-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .board-col { display: flex; flex-direction: column; align-items: center; gap: 8px; }

  /* ── Mobile root ── */
  .mobile-root {
    position: fixed; inset: 0;
    width: 100%; height: 100%;
    overflow: hidden;
  }

  /* Force landscape on portrait phones */
  @media screen and (max-width: 768px) and (orientation: portrait) {
    .mobile-root {
      position: fixed;
      top: 50%; left: 50%;
      width: 100svh;
      height: 100svw;
      transform: translate(-50%, -50%) rotate(90deg);
      transform-origin: center center;
    }
  }
</style>
