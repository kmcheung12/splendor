<!-- frontend/src/components/MobileBoard.svelte -->
<script lang="ts">
  import {
    gameState, isMyTurn, humanTurnActions,
    tokenSelectMode, stagedTokens, catchFlash,
  } from '../lib/gameStore'
  import TokenStagingArea from './TokenStagingArea.svelte'
  import CardDetailModal from './CardDetailModal.svelte'
  import BoardCard from './BoardCard.svelte'
  import type { PokemonCard } from '../lib/types'
  import { BALL } from '../lib/tokens'
  import { sendAction } from '../lib/ws'

  import { COL, TOKEN_ORDER, TIER_ABS_OFFSET, TIER_DECK_GRAD } from '../lib/gameData'

  $: board = $gameState?.board
  $: boardTokens = $gameState?.board_tokens ?? {}
  $: stagedCounts = $stagedTokens.reduce<Record<string, number>>((acc, t) => {
    acc[t] = (acc[t] ?? 0) + 1; return acc
  }, {})
  $: displayedTokens = TOKEN_ORDER.reduce<Record<string, number>>((acc, t) => {
    acc[t] = Math.max(0, (boardTokens[t] ?? 0) - (stagedCounts[t] ?? 0)); return acc
  }, {})

  function canAddToken(t: string): boolean {
    if (!$isMyTurn || t === 'master') return false
    if (!$humanTurnActions.some(a => a < 30)) return false
    const staged = $stagedTokens
    const n = staged.length
    if (n >= 3) return false
    const types = new Set(staged)
    if (n > types.size) return false
    if (n === 2) return !types.has(t)
    if (n === 1 && staged[0] === t) {
      const idx = ['red','yellow','blue','pink','black'].indexOf(t)
      return idx >= 0 && $humanTurnActions.includes(25 + idx)
    }
    return true
  }

  function slotHasValidAction(absSlot: number): boolean {
    const candidates = absSlot < 12
      ? [30 + absSlot, 47 + absSlot, 59 + absSlot]
      : [30 + absSlot]
    return candidates.some(a => $humanTurnActions.includes(a))
  }

  let cardDetail: { card: PokemonCard; tier: string; actions: { id: number; label: string }[] } | null = null
  let jumpingKey: string | null = null

  function triggerJump(key: string) {
    jumpingKey = key
    setTimeout(() => { jumpingKey = null }, 480)
  }

  function handleTokenClick(t: string) {
    if (!canAddToken(t)) return
    cardDetail = null
    stagedTokens.update(s => [...s, t])
    tokenSelectMode.set(true)
  }

  function handleCardClick(card: PokemonCard, tier: string, slotIdx: number) {
    if ($tokenSelectMode) { stagedTokens.set([]); tokenSelectMode.set(false); return }
    triggerJump(`${tier}-${slotIdx}`)
    const absSlot = (TIER_ABS_OFFSET[tier] ?? 0) + slotIdx
    const candidates = absSlot < 12
      ? [30 + absSlot, 47 + absSlot, 59 + absSlot]
      : [30 + absSlot]
    let relevant = $isMyTurn
      ? candidates.filter(a => $humanTurnActions.includes(a))
      : []
    if (relevant.some(a => a >= 47 && a < 59)) {
      relevant = relevant.filter(a => !(a >= 59 && a < 71))
    }
    cardDetail = { card, tier, actions: relevant.map(a => ({ id: a, label: actionLabel(a) })) }
  }

  function actionLabel(id: number): string {
    if (id >= 30 && id < 44) return 'Catch'
    if (id >= 47 && id < 59) return 'Reserve'
    if (id >= 59 && id < 71) return 'Reserve'
    return 'Action'
  }

  $: lowerRows = board ? [
    { tier: 'rare',     deckCount: board.rare_deck_count,     revealed: board.rare_revealed },
    { tier: 'uncommon', deckCount: board.uncommon_deck_count, revealed: board.uncommon_revealed },
    { tier: 'common',   deckCount: board.common_deck_count,   revealed: board.common_revealed },
  ] : []
</script>

{#if board}
<div class="board">
  <!-- ── Top band: pool + epic + legendary ── -->
  <div class="board-top">
    <div class="pool">
      {#each TOKEN_ORDER as t}
        {@const count = displayedTokens[t] ?? 0}
        <button
          class="pool-tok"
          class:empty={count === 0}
          class:pulse={$isMyTurn && canAddToken(t)}
          data-token-type={t}
          disabled={count === 0}
          style="--gc:{COL[t]}"
          on:click={() => handleTokenClick(t)}
        >
          <img src={BALL[t]} alt={t} width="20" height="20" draggable="false">
          <span class="pool-n">{count}</span>
        </button>
      {/each}
    </div>

    {#if $tokenSelectMode || $stagedTokens.length > 0}
    <div class="top-staging">
      <TokenStagingArea />
    </div>
    {:else}
    <div class="top-cards">
      <!-- Epic -->
      <div class="deck" style="background:{TIER_DECK_GRAD.epic}">
        <span class="deck-label">Epic</span>
        <span class="deck-count">{board.epic_deck_count}</span>
      </div>
      {#each board.epic_revealed as card, slotIdx}
        {@const absSlot = 12 + slotIdx}
        {#if card}
          <BoardCard
            {card}
            tier="epic"
            jumping={jumpingKey === `epic-${slotIdx}`}
            highlighted={$isMyTurn && slotHasValidAction(absSlot)}
            catchReveal={$catchFlash?.card === card.name}
            on:click={() => handleCardClick(card, 'epic', slotIdx)}
            on:keydown={(e) => e.key === 'Enter' && handleCardClick(card, 'epic', slotIdx)}
          />
        {:else}
          <div class="bcard-empty"></div>
        {/if}
      {/each}

      <!-- Legendary -->
      <div class="deck" style="background:{TIER_DECK_GRAD.legendary}">
        <span class="deck-label">Leg.</span>
        <span class="deck-count">{board.legendary_deck_count}</span>
      </div>
      {#each board.legendary_revealed as card, slotIdx}
        {@const absSlot = 13 + slotIdx}
        {#if card}
          <BoardCard
            {card}
            tier="legendary"
            jumping={jumpingKey === `legendary-${slotIdx}`}
            highlighted={$isMyTurn && slotHasValidAction(absSlot)}
            catchReveal={$catchFlash?.card === card.name}
            on:click={() => handleCardClick(card, 'legendary', slotIdx)}
            on:keydown={(e) => e.key === 'Enter' && handleCardClick(card, 'legendary', slotIdx)}
          />
        {:else}
          <div class="bcard-empty"></div>
        {/if}
      {/each}
    </div>
    {/if}
  </div>

  <!-- ── Lower rows: rare, uncommon, common ── -->
  {#each lowerRows as row}
    <div class="card-row">
      <div class="deck" style="background:{TIER_DECK_GRAD[row.tier]}">
        <span class="deck-count">{row.deckCount}</span>
      </div>
      {#each row.revealed as card, slotIdx}
        {@const absSlot = (TIER_ABS_OFFSET[row.tier] ?? 0) + slotIdx}
        {#if card}
          <BoardCard
            {card}
            tier={row.tier}
            jumping={jumpingKey === `${row.tier}-${slotIdx}`}
            highlighted={$isMyTurn && slotHasValidAction(absSlot)}
            catchReveal={$catchFlash?.card === card.name}
            on:click={() => handleCardClick(card, row.tier, slotIdx)}
            on:keydown={(e) => e.key === 'Enter' && handleCardClick(card, row.tier, slotIdx)}
          />
        {:else}
          <div class="bcard-empty"></div>
        {/if}
      {/each}
    </div>
  {/each}
</div>
{/if}

{#if cardDetail}
  <CardDetailModal
    card={cardDetail.card}
    tier={cardDetail.tier}
    actions={cardDetail.actions}
    on:action={(e) => { sendAction(e.detail); cardDetail = null }}
    on:close={() => cardDetail = null}
  />
{/if}

<style>
  .board { display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }
  .board-top { display: flex; gap: 8px; width: 462px; align-items: stretch; }
  .pool { flex: 0 0 160px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; align-content: center; }
  .top-cards { flex: 1; display: flex; gap: 6px; }
  .top-staging { flex: 1; min-width: 0; display: flex; align-items: stretch; }
  .card-row { display: flex; gap: 6px; width: 462px; }

  .pool-tok {
    background: rgba(255,255,255,.07); border: 1px solid var(--gc, rgba(255,255,255,.12));
    border-radius: 7px; display: flex; flex-direction: column;
    align-items: center; gap: 1px; padding: 4px 0; cursor: default;
  }
  .pool-tok img { image-rendering: pixelated; display: block; }
  .pool-tok.pulse { cursor: pointer; animation: tok-pulse 3.6s ease-in-out infinite; }
  .pool-tok.empty { opacity: .3; cursor: not-allowed; }
  .pool-n { font-family: 'Press Start 2P', monospace; font-size: 9px; color: #fff; }
  @keyframes tok-pulse {
    0%,100% { filter: drop-shadow(0 0 0px rgba(255,255,255,0)); }
    50%     { filter: drop-shadow(0 0 6px rgba(255,255,255,.55)); }
  }

  .deck {
    width: 38px; flex: none; border-radius: 3px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 3px;
  }
  .deck-label { font-family: 'Press Start 2P', monospace; font-size: 6px; color: rgba(255,255,255,.9); text-transform: uppercase; }
  .deck-count { font-family: 'Press Start 2P', monospace; font-size: 11px; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.7); }

  .bcard-empty {
    width: 100px; height: 80px; flex: none;
    background: #1a1a2e; border: 2px solid #0c0d12; border-radius: 3px;
    box-sizing: border-box;
  }
</style>
