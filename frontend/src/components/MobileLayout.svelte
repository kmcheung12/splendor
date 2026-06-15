<!-- frontend/src/components/MobileLayout.svelte -->
<script lang="ts">
  import { onMount } from 'svelte'
  import {
    gameState, mySlot, isMyTurn, phase, playerNames,
  } from '../lib/gameStore'
  import { activeTutorialItem } from '../lib/tutorialStore'
  import MobileBoard from './MobileBoard.svelte'
  import MobilePlayerRail from './MobilePlayerRail.svelte'
  import PlayerHandModal from './PlayerHandModal.svelte'
  import type { PlayerState } from '../lib/types'

  // ── Board scaling ──────────────────────────────────────────────────────
  let boardArea: HTMLElement
  let scale = 1
  const BOARD_W = 462   // natural board width (px)
  const BOARD_H = 346   // natural board height estimate (px)

  onMount(() => {
    const ro = new ResizeObserver(() => {
      if (!boardArea) return
      const s = Math.min(
        (boardArea.clientWidth  - 2) / BOARD_W,
        (boardArea.clientHeight - 2) / BOARD_H,
      )
      scale = Math.max(0.3, s)
    })
    ro.observe(boardArea)
    return () => ro.disconnect()
  })

  // ── Player rail assignment ─────────────────────────────────────────────
  function computeRails(players: PlayerState[], slot: number | null): {
    left: PlayerState[]; right: PlayerState[]
  } {
    if (!players.length) return { left: [], right: [] }
    const n = players.length
    const hi = slot ?? 0
    if (n === 2) {
      return { left: [players[hi]], right: [players[1 - hi]] }
    }
    if (n === 3) {
      const others = players.filter((_, i) => i !== hi)
      return { left: [players[hi]], right: others }
    }
    // 4 players: human + prev-in-order on left, other two on right
    const partnerIdx = (hi + 3) % 4
    const rightIdxs = [0, 1, 2, 3].filter(i => i !== hi && i !== partnerIdx)
    return {
      left:  [players[hi], players[partnerIdx]],
      right: [players[rightIdxs[0]], players[rightIdxs[1]]],
    }
  }

  $: rails = $gameState
    ? computeRails($gameState.players, $mySlot)
    : { left: [], right: [] }

  $: myPlayerName = $gameState && $mySlot !== null
    ? $gameState.players[$mySlot]?.name ?? null
    : null

  // ── Expand / modal state ───────────────────────────────────────────────
  let expandedPlayerName: string | null = null

  $: if ($isMyTurn && $phase === 'discard' && myPlayerName) {
    expandedPlayerName = myPlayerName
  }

  $: expandedPlayer = expandedPlayerName && $gameState
    ? $gameState.players.find(p => p.name === expandedPlayerName) ?? null
    : null

  function displayName(p: PlayerState): string {
    return $playerNames[p.name] ?? p.name
  }
</script>

<div class="mobile-screen">
  <!-- Left rail column -->
  <div class="railcol" class:tut-lift={!!$activeTutorialItem}>
    {#each rails.left as p (p.name)}
      <MobilePlayerRail
        player={p}
        displayName={displayName(p)}
        isOwnPlayer={p.name === myPlayerName}
        on:expand={() => expandedPlayerName = p.name}
      />
    {/each}
  </div>

  <!-- Board (scaled) -->
  <div class="boardArea" class:tut-lift={!!$activeTutorialItem} bind:this={boardArea}>
    <div class="board-scale" style="transform: translate(-50%,-50%) scale({scale})">
      <MobileBoard />
    </div>
  </div>

  <!-- Right rail column -->
  <div class="railcol" class:tut-lift={!!$activeTutorialItem}>
    {#each rails.right as p (p.name)}
      <MobilePlayerRail
        player={p}
        displayName={displayName(p)}
        isOwnPlayer={p.name === myPlayerName}
        on:expand={() => expandedPlayerName = p.name}
      />
    {/each}
  </div>

  <!-- Expanded hand modal -->
  {#if expandedPlayer}
    <PlayerHandModal
      player={expandedPlayer}
      displayName={displayName(expandedPlayer)}
      isOwnPlayer={expandedPlayer.name === myPlayerName}
      on:close={() => expandedPlayerName = null}
    />
  {/if}
</div>

<style>
  .mobile-screen {
    position: relative;
    width: 100%; height: 100%;
    background: #0d0d1a;
    display: flex; flex-direction: row;
    align-items: stretch; gap: 8px;
    padding: 8px; box-sizing: border-box;
    overflow: hidden;
  }

  .railcol {
    width: 110px; flex: none;
    display: flex; flex-direction: column;
    gap: 8px; min-height: 0;
  }

  .boardArea {
    position: relative; overflow: hidden;
    flex: 1; min-width: 0;
  }

  /* Lift game containers above the tutorial dim overlay (z-index 1000) so
     tutorial-highlight (z-index 1010) is visible even inside CSS transforms. */
  .tut-lift {
    position: relative;
    z-index: 1001;
  }
  .board-scale {
    position: absolute; top: 50%; left: 50%;
  }

</style>
