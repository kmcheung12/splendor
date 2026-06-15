<!-- frontend/src/App.svelte -->
<script lang="ts">
  import { onMount } from 'svelte'
  import { connect, claimSlot, startGame } from './lib/ws'
  import { gameState, gameOver, playerNames, lobbyState, mySlot } from './lib/gameStore'
  import { tutorialMode, initTutorial } from './lib/tutorialStore'
  import { BOARD_SELECTOR_MAP, MOBILE_SELECTOR_MAP } from './lib/tutorial'
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
  let delayMs = 800

  let error: string | null = null

  async function createGame() {
    error = null
    try {
      const res = await fetch('/game/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_players: numPlayers,
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

  $: if (view === 'lobby' && $gameState) {
    view = 'game'
  }

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

      <button class="btn-tutorial" on:click={createTutorialGame}>▶ Play Tutorial</button>

      <div class="divider"></div>

      <section class="create-section">
        <div class="player-row">
          <span class="player-row-label">Players</span>
          <div class="player-btns">
            {#each [2, 3, 4] as n}
              <button class="player-btn" class:selected={numPlayers === n} on:click={() => numPlayers = n}>
                <span class="player-icons">{#each Array(n) as _}&#9679;{/each}</span>
                <span class="player-num">{n}</span>
              </button>
            {/each}
          </div>
        </div>

        <button class="btn-create" on:click={createGame}>Create &amp; Host</button>
      </section>

      <div class="divider"></div>

      <section class="join-section">
        <input class="join-input" placeholder="Join Code" bind:value={joinCode} maxlength={4} style="text-transform:uppercase" />
        <button class="btn-join" on:click={() => joinGame(joinCode)} disabled={!joinCode.trim()}>Join Game</button>
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
        {#if $tutorialMode}
          <TutorialController />
          <TutorialOverlay selectorMap={MOBILE_SELECTOR_MAP} noDim={true} />
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
    max-width: 360px; margin: 60px auto; padding: 28px 24px;
    background: rgba(255,255,255,.07); border-radius: 14px;
    display: flex; flex-direction: column; gap: 20px;
  }
  h1 { text-align: center; color: #f1c40f; margin: 0 0 4px; font-size: 1.5rem; }
  .divider { height: 1px; background: rgba(255,255,255,.1); }
  .error { background: rgba(231,76,60,.2); border: 1px solid rgba(231,76,60,.4); color: #e74c3c; border-radius: 6px; padding: 8px 12px; font-size: .85rem; }

  .btn-tutorial {
    width: 100%; background: #2c3e8c; color: #fff; border: none; border-radius: 10px;
    font-size: 1.05rem; padding: 14px 20px; cursor: pointer; letter-spacing: 0.03em;
  }
  .btn-tutorial:hover { background: #3a52b4; }

  .create-section { display: flex; flex-direction: column; gap: 14px; }
  .player-row { display: flex; align-items: center; gap: 12px; }
  .player-row-label { font-size: .8rem; color: rgba(255,255,255,.55); white-space: nowrap; }
  .player-btns { display: flex; gap: 8px; flex: 1; }
  .player-btn {
    flex: 1; display: flex; flex-direction: column; align-items: center; gap: 5px;
    background: rgba(255,255,255,.08); border: 2px solid transparent; border-radius: 10px;
    color: #fff; cursor: pointer; padding: 10px 6px;
  }
  .player-btn:hover { background: rgba(255,255,255,.14); }
  .player-btn.selected { border-color: #f1c40f; background: rgba(241,196,15,.12); }
  .player-icons { font-size: 8px; color: rgba(255,255,255,.55); letter-spacing: 3px; line-height: 1; }
  .player-btn.selected .player-icons { color: #f1c40f; }
  .player-num { font-family: 'Press Start 2P', monospace; font-size: 14px; line-height: 1; }
  .btn-create {
    width: 100%; background: #27ae60; color: #fff; border: none; border-radius: 10px;
    font-size: .95rem; padding: 13px; cursor: pointer;
  }
  .btn-create:hover { background: #2ecc71; }

  .join-section { display: flex; flex-direction: column; gap: 10px; }
  .join-input {
    width: 100%; box-sizing: border-box;
    background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.2);
    border-radius: 8px; color: white; padding: 12px 14px;
    font-size: 1.1rem; letter-spacing: 0.15em; text-align: center;
  }
  .join-input::placeholder { color: rgba(255,255,255,.3); letter-spacing: 0.05em; font-size: .9rem; }
  .btn-join {
    width: 100%; background: rgba(255,255,255,.1); color: #fff;
    border: 1px solid rgba(255,255,255,.2); border-radius: 10px;
    font-size: .95rem; padding: 13px; cursor: pointer;
  }
  .btn-join:hover:not(:disabled) { background: rgba(255,255,255,.18); }
  .btn-join:disabled { opacity: .4; cursor: not-allowed; }
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
