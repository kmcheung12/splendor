<script lang="ts">
  import { gameState, isMyTurn, humanTurnActions, tokenSelectMode, stagedTokens, activePlayer, pendingActionEvent, mySlot, evolveFlash, catchFlash } from '../lib/gameStore'
  import { fly } from 'svelte/transition'
  import { cubicOut } from 'svelte/easing'
  import { tick } from 'svelte'
  import CardSlot from './CardSlot.svelte'
  import ActionMenu from './ActionMenu.svelte'
  import TokenStagingArea from './TokenStagingArea.svelte'
  import type { PokemonCard } from '../lib/types'
  import { BALL } from '../lib/tokens'
  import { flyArc, ARC_DURATION } from '../lib/arcAnimation'

  const TOKEN_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']

  const TIER_BALL: Record<string, string> = {
    common: BALL['red'], uncommon: BALL['blue'], rare: BALL['yellow'],
    epic: BALL['black'], legendary: BALL['master'],
  }

  // slot in catch_card is absolute (common 0-3, uncommon 4-7, rare 8-11, epic 12, legendary 13)
  const TIER_ABS_OFFSET: Record<string, number> = {
    common: 0, uncommon: 4, rare: 8, epic: 12, legendary: 13,
  }

  function findCardOnBoard(tier: string, absSlot: number): HTMLElement | null {
    const slotIdx = absSlot - (TIER_ABS_OFFSET[tier] ?? 0)
    return document.querySelector<HTMLElement>(`[data-tier="${tier}"][data-slot="${slotIdx}"]`)
  }

  // Player positions (clockwise): 0=top, 1=right, 2=bottom, 3=left
  $: activeIdx = $gameState?.players.findIndex(p => p.name === $activePlayer) ?? -1
  $: flyOut = (() => {
    switch (activeIdx) {
      case 0: return { x: -120, y: 0   }  // top-left → left
      case 1: return { x: 120,  y: 0   }  // top-right → right
      case 2: return { x: 120,  y: 120 }  // bottom-right → lower-right
      case 3: return { x: -120, y: 120 }  // bottom-left → lower-left
      default: return { x: 0,   y: 120 }
    }
  })()

  $: board = $gameState?.board
  $: boardTokens = $gameState?.board_tokens ?? {}
  $: stagedCounts = $stagedTokens.reduce<Record<string, number>>((acc, t) => {
    acc[t] = (acc[t] ?? 0) + 1
    return acc
  }, {})
  $: displayedTokens = TOKEN_ORDER.reduce<Record<string, number>>((acc, t) => {
    acc[t] = Math.max(0, (boardTokens[t] ?? 0) - (stagedCounts[t] ?? 0))
    return acc
  }, {})

  function canAddToken(t: string): boolean {
    if (!$isMyTurn) return false
    if (t === 'master') return false
    if (!$humanTurnActions.some(a => a < 30)) return false
    const staged = $stagedTokens
    const n = staged.length
    if (n >= 3) return false
    const types = new Set(staged)
    const hasDups = n > types.size
    if (hasDups) {
      // already in "take 2 same" mode — can't add more
      return false
    }
    if (n === 2) {
      // can only add a third different color
      return !types.has(t)
    }
    if (n === 1) {
      // can add same (start take-2) or different
      if (staged[0] === t) {
        // take 2 same — need ≥4 on board; check via humanTurnActions
        const TAKE_SAME_TYPES = ['red','yellow','blue','pink','black']
        const idx = TAKE_SAME_TYPES.indexOf(t)
        return idx >= 0 && $humanTurnActions.includes(25 + idx)
      }
      return true
    }
    // n === 0
    return true
  }

  // Rows 2–4 only (Epic+Legendary share row 1, handled separately in template)
  let lowerRows: Array<{ tier: string; deckCount: number; revealed: (PokemonCard | null)[] }> = []
  $: lowerRows = board ? [
    { tier: 'rare',     deckCount: board.rare_deck_count,     revealed: board.rare_revealed },
    { tier: 'uncommon', deckCount: board.uncommon_deck_count, revealed: board.uncommon_revealed },
    { tier: 'common',   deckCount: board.common_deck_count,   revealed: board.common_revealed },
  ] : []

  let popup: { x: number; y: number; actions: number[]; labels: string[]; cardRect: DOMRect } | null = null

  function handleCardClick(e: MouseEvent, slotIdx: number, tier: string) {
    if (!$isMyTurn) return
    if ($tokenSelectMode) {
      stagedTokens.set([])
      tokenSelectMode.set(false)
      return
    }
    const tierOffsets: Record<string, number> = {
      common: 0, uncommon: 4, rare: 8, epic: 12, legendary: 13,
    }
    const absSlot = (tierOffsets[tier] ?? 0) + slotIdx
    const valid = $humanTurnActions
    const candidates = absSlot < 12
      ? [30 + absSlot, 47 + absSlot, 59 + absSlot]
      : [30 + absSlot]
    const relevant = candidates.filter(a => valid.includes(a))
    if (relevant.length === 0) return
    const rect = (e.target as HTMLElement).getBoundingClientRect()
    popup = { x: rect.left, y: rect.bottom + 4, actions: relevant, labels: relevant.map(actionLabel), cardRect: rect }
  }

  function handleActionConfirmed(e: CustomEvent<{ actionId: number }>) {
    const { actionId } = e.detail
    if (actionId >= 47 && actionId < 59 && popup) {
      const masterBtn = document.querySelector<HTMLElement>('[data-token-type="master"]')
      const panelEl  = document.querySelector<HTMLElement>(`[data-player-name="${$activePlayer}"]`)
      if (masterBtn && panelEl)
        flyArc(masterBtn.getBoundingClientRect(), panelEl.getBoundingClientRect(), BALL['master'])
    }
  }

  $: if ($pendingActionEvent?.type === 'catch_card') {
    const evt = $pendingActionEvent
    if (evt.card) {
      catchFlash.set({ player: evt.player, card: evt.card })
      setTimeout(() => catchFlash.set(null), 1800)
    }
    if (!evt.from_reserve) {
      const panelEl = document.querySelector<HTMLElement>(`[data-player-name="${evt.player}"]`)
      const cardEl = evt.tier ? findCardOnBoard(evt.tier, evt.slot) : null
      if (panelEl && cardEl) {
        const panelRect = panelEl.getBoundingClientRect()
        const cardRect = cardEl.getBoundingClientRect()
        const ball = TIER_BALL[evt.tier ?? 'common'] ?? BALL['red']
        const slotIdx = evt.slot - (TIER_ABS_OFFSET[evt.tier ?? ''] ?? 0)
        if (recentCatchTimer) clearTimeout(recentCatchTimer)
        recentCatchKey = `${evt.tier}-${slotIdx}`
        recentCatchTimer = setTimeout(() => { recentCatchKey = null }, 500)
        flyArc(panelRect, cardRect, ball, ARC_DURATION, 0, () => {
          flyArc(cardRect, panelRect, ball)
        })
      }
    }
  }

  $: if ($pendingActionEvent?.type === 'evolve_card') {
    const evt = $pendingActionEvent
    const playerState = $gameState?.players.find(p => p.name === evt.player)
    const card = playerState?.cards[evt.card_index]
    const ball = TIER_BALL[card?.tier ?? 'common'] ?? BALL['red']
    const poolBtn = document.querySelector<HTMLElement>(`[data-token-type="${card?.bonus?.[0] ?? 'red'}"]`)
    const cardEl = document.querySelector<HTMLElement>(`[data-player-name="${evt.player}"] [data-card-index="${evt.card_index}"]`)
    if (poolBtn && cardEl) {
      flyArc(poolBtn.getBoundingClientRect(), cardEl.getBoundingClientRect(), ball, ARC_DURATION, 0, () => {
        evolveFlash.set({ player: evt.player, cardIndex: evt.card_index })
        setTimeout(() => evolveFlash.set(null), 700)
      })
    }
  }

  async function handleTokenClick(e: MouseEvent, tokenType: string) {
    if (!canAddToken(tokenType)) return
    popup = null
    stagedTokens.update(s => [...s, tokenType])
    tokenSelectMode.set(true)
    await tick()
    // After tick: button has shifted into its settled position, staging area is rendered.
    // Capture fromRect now so animation starts from where the button actually is.
    const btn = (e.currentTarget as HTMLElement)
    const fromRect = btn.getBoundingClientRect()
    const slots = document.querySelectorAll<HTMLElement>('.slot-filled')
    const dest = slots[slots.length - 1]
    if (dest) flyArc(fromRect, dest.getBoundingClientRect(), BALL[tokenType])
  }

  function slotHasValidAction(slotIdx: number, tier: string): boolean {
    const tierOffsets: Record<string, number> = {
      common: 0, uncommon: 4, rare: 8, epic: 12, legendary: 13,
    }
    const absSlot = (tierOffsets[tier] ?? 0) + slotIdx
    const valid = $humanTurnActions
    const candidates = absSlot < 12 ? [30 + absSlot, 47 + absSlot, 59 + absSlot] : [30 + absSlot]
    return candidates.some(a => valid.includes(a))
  }

  let recentCatchKey: string | null = null
  let recentCatchTimer: ReturnType<typeof setTimeout> | null = null

  function actionLabel(actionId: number): string {
    if (actionId >= 30 && actionId < 44) return 'Catch'
    if (actionId >= 44 && actionId < 47) return 'Catch (reserved)'
    if (actionId >= 47 && actionId < 59) return 'Reserve + Master ball'
    if (actionId >= 59 && actionId < 71) return 'Reserve'
    if (actionId >= 0  && actionId < 25) return 'Take tokens'
    if (actionId >= 25 && actionId < 30) return 'Take 2×'
    return 'Action'
  }
</script>

<div class="board">
  <div class="board-top">
    <div class="pool">
      <div class="token-buttons">
        {#each TOKEN_ORDER as t}
          {@const count = displayedTokens[t] ?? 0}
          <button
            class="token"
            class:pulse={$isMyTurn && canAddToken(t)}
            class:dimmed={$isMyTurn && !canAddToken(t)}
            class:empty={count === 0}
            data-token-type={t}
            title={t}
            disabled={count === 0}
            on:click={(e) => handleTokenClick(e, t)}
          >
            <img src={BALL[t]} alt={t} width="28" height="28" draggable="false">
            <span class="tok-count">{count}</span>
          </button>
        {/each}
      </div>
      {#if $tokenSelectMode || $stagedTokens.length > 0}
        <TokenStagingArea />
      {/if}
    </div>

    {#if board}
    <div class="top-cards">
      <div class="card-cell deck-back tier-epic">
        <div class="deck-label">Epic</div>
        <span class="deck-count">{board.epic_deck_count}</span>
      </div>
      {#each board.epic_revealed as card, slotIdx (`epic-${slotIdx}`)}
        <div class="card-cell" data-tier="epic" data-slot={slotIdx}>
          {#key card?.name}
            <div class="card-anim" in:fly={{ y: -30, duration: 800, delay: recentCatchKey === `epic-${slotIdx}` ? 200 : 0 }} out:fly={{ ...flyOut, duration: 520, easing: cubicOut }}>
              <CardSlot {card} tier="epic"
                highlight={$isMyTurn && card !== null && slotHasValidAction(slotIdx, 'epic')}
                on:click={(e) => handleCardClick(e, slotIdx, 'epic')}
              />
            </div>
          {/key}
        </div>
      {/each}
      <div class="card-cell deck-back tier-legendary">
        <div class="deck-label">Leg.</div>
        <span class="deck-count">{board.legendary_deck_count}</span>
      </div>
      {#each board.legendary_revealed as card, slotIdx (`legendary-${slotIdx}`)}
        <div class="card-cell" data-tier="legendary" data-slot={slotIdx}>
          {#key card?.name}
            <div class="card-anim" in:fly={{ y: -30, duration: 800, delay: recentCatchKey === `legendary-${slotIdx}` ? 200 : 0 }} out:fly={{ ...flyOut, duration: 520, easing: cubicOut }}>
              <CardSlot {card} tier="legendary"
                highlight={$isMyTurn && card !== null && slotHasValidAction(slotIdx, 'legendary')}
                on:click={(e) => handleCardClick(e, slotIdx, 'legendary')}
              />
            </div>
          {/key}
        </div>
      {/each}
    </div>
    {/if}
  </div>

  {#if board}
    <!-- Rows 2–4: Rare, Uncommon, Common (deck back + 4 revealed each) -->
    {#each lowerRows as row}
      <div class="card-row row-lower">
        <div class="card-cell deck-back tier-{row.tier}">
          <span class="deck-count">{row.deckCount}</span>
        </div>
        {#each row.revealed as card, slotIdx (`${row.tier}-${slotIdx}`)}
          <div class="card-cell" data-tier={row.tier} data-slot={slotIdx}>
            {#key card?.name}
              <div class="card-anim" in:fly={{ y: -30, duration: 800, delay: recentCatchKey === `${row.tier}-${slotIdx}` ? 200 : 0 }} out:fly={{ ...flyOut, duration: 520, easing: cubicOut }}>
                <CardSlot {card} tier={row.tier}
                  highlight={$isMyTurn && card !== null && slotHasValidAction(slotIdx, row.tier)}
                  on:click={(e) => handleCardClick(e, slotIdx, row.tier)}
                />
              </div>
            {/key}
          </div>
        {/each}
      </div>
    {/each}
  {/if}
</div>

{#if popup}
  <ActionMenu
    anchorX={popup.x} anchorY={popup.y}
    actions={popup.actions} labels={popup.labels}
    on:confirm={handleActionConfirmed}
    on:cancel={() => popup = null}
  />
{/if}

<style>
  .board { display: flex; flex-direction: column; gap: 6px; padding: 12px; }
  .board-top { display: flex; gap: 8px; align-items: flex-start; }
  .pool { flex: 0 0 160px; display: flex; flex-direction: column; gap: 8px; }
  .token-buttons { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
  .top-cards { flex: 1; display: flex; justify-content: flex-end; gap: 6px; }
  .top-cards .card-cell { flex: none; width: 158px; }
  .top-cards .deck-back { width: 52px; }
  .token {
    display: inline-flex; flex-direction: column; align-items: center; gap: 2px;
    background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12);
    border-radius: 8px; padding: 6px 10px; cursor: default; min-width: 44px;
  }
  .token img { image-rendering: pixelated; display: block; }
  .tok-count { font-size: .75rem; font-weight: bold; color: rgba(255,255,255,.85); line-height: 1; }
  .token.pulse { cursor: pointer; animation: tok-pulse 3.6s ease-in-out infinite; }
  .token.pulse:hover { background: rgba(255,255,255,.14); border-color: rgba(255,255,255,.3); }
  .token.dimmed { opacity: .35; cursor: not-allowed; }
  .token.empty { opacity: .2; cursor: not-allowed; }
  @keyframes tok-pulse {
    0%, 100% { filter: drop-shadow(0 0 0px rgba(255,255,255,0)); }
    50%       { filter: drop-shadow(0 0 6px rgba(255,255,255,.55)); }
  }
  .card-row { display: grid; gap: 6px; }
  .row-lower { grid-template-columns: 52px repeat(4, 158px); }
  .card-cell { height: 130px; position: relative; }
  .card-anim { position: absolute; inset: 0; }
  .deck-back { border-radius: 3px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; cursor: default; position: relative; overflow: hidden; }
  .deck-back::after {
    content: ''; position: absolute; inset: 0; pointer-events: none;
    background: linear-gradient(
      125deg,
      transparent            0%,
      rgba(140,190,255,.13) 28%,
      rgba(210,170,255,.11) 45%,
      rgba(130,230,200,.10) 62%,
      transparent           90%
    );
    background-size: 250% 250%;
    background-position: 0% 0%;
    opacity: 0; transition: opacity .4s ease;
    animation: holo-sweep-deck 2.6s ease-in-out infinite alternate; animation-play-state: paused;
  }
  .deck-back:hover::after { opacity: 1; animation-play-state: running; }
  @keyframes holo-sweep-deck {
    from { background-position:   0% 0%; }
    to   { background-position: 100% 100%; }
  }
  .deck-label { font-family: 'Press Start 2P', monospace; font-size: .5rem; color: rgba(255,255,255,.85); text-transform: uppercase; letter-spacing: .04em; }
  .deck-back.tier-common    { background: linear-gradient(135deg,#8B6914,#c9a64a); }
  .deck-back.tier-uncommon  { background: linear-gradient(135deg,#7f8c8d,#bdc3c7); }
  .deck-back.tier-rare      { background: linear-gradient(135deg,#c8a415,#f5d60a); }
  .deck-back.tier-epic      { background: linear-gradient(135deg,#6c3483,#a569bd); }
  .deck-back.tier-legendary { background: linear-gradient(135deg,#154360,#2e86c1,#e74c3c,#f39c12); }
  .deck-count { font-family: 'Press Start 2P', monospace; font-size: .9rem; color: white; text-shadow: 0 1px 3px rgba(0,0,0,.7); }
</style>
