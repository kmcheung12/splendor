<script lang="ts">
  import { gameState, sendToken, isMyTurn, humanTurnActions } from '../lib/gameStore'
  import { fly } from 'svelte/transition'
  import CardSlot from './CardSlot.svelte'
  import ActionMenu from './ActionMenu.svelte'
  import type { PokemonCard } from '../lib/types'

  const TOKEN_COLORS: Record<string, string> = {
    red: '#e74c3c', yellow: '#f1c40f', blue: '#3498db',
    pink: '#e91e96', black: '#555', master: '#f39c12',
  }
  const TOKEN_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']

  $: board = $gameState?.board
  $: boardTokens = $gameState?.board_tokens ?? {}
  $: tokenIcons = TOKEN_ORDER.flatMap(t => Array<string>(boardTokens[t] ?? 0).fill(t))

  let rows: Array<{ tier: string; deckCount: number; revealed: (PokemonCard | null)[] }> = []
  $: rows = board ? [
    { tier: 'legendary', deckCount: board.legendary_deck_count, revealed: board.legendary_revealed },
    { tier: 'epic',      deckCount: board.epic_deck_count,      revealed: board.epic_revealed },
    { tier: 'rare',      deckCount: board.rare_deck_count,      revealed: board.rare_revealed },
    { tier: 'uncommon',  deckCount: board.uncommon_deck_count,  revealed: board.uncommon_revealed },
    { tier: 'common',    deckCount: board.common_deck_count,    revealed: board.common_revealed },
  ] : []

  let popup: { x: number; y: number; actions: number[]; labels: string[] } | null = null

  function handleCardClick(e: MouseEvent, slotIdx: number, tier: string) {
    if (!$isMyTurn) return
    const tierOffsets: Record<string, number> = {
      common: 0, uncommon: 4, rare: 8, epic: 12, legendary: 13,
    }
    const absSlot = (tierOffsets[tier] ?? 0) + slotIdx
    const valid = $humanTurnActions
    const relevant = [30 + absSlot, 47 + absSlot, 59 + absSlot].filter(a => valid.includes(a))
    if (relevant.length === 0) return
    const rect = (e.target as HTMLElement).getBoundingClientRect()
    popup = { x: rect.left, y: rect.bottom + 4, actions: relevant, labels: relevant.map(actionLabel) }
  }

  function handleTokenClick(e: MouseEvent, tokenType: string) {
    if (!$isMyTurn) return
    const TAKE_DIFF_COMBOS = [
      ['red'],['yellow'],['blue'],['pink'],['black'],
      ['red','yellow'],['red','blue'],['red','pink'],['red','black'],
      ['yellow','blue'],['yellow','pink'],['yellow','black'],
      ['blue','pink'],['blue','black'],['pink','black'],
      ['red','yellow','blue'],['red','yellow','pink'],['red','yellow','black'],
      ['red','blue','pink'],['red','blue','black'],['red','pink','black'],
      ['yellow','blue','pink'],['yellow','blue','black'],['yellow','pink','black'],
      ['blue','pink','black'],
    ]
    const TAKE_SAME_TYPES = ['red','yellow','blue','pink','black']
    const valid = $humanTurnActions
    const singleIdx = TAKE_DIFF_COMBOS.findIndex(c => c.length === 1 && c[0] === tokenType)
    const sameIdx = TAKE_SAME_TYPES.indexOf(tokenType)
    const relevant: number[] = []
    if (singleIdx >= 0 && valid.includes(singleIdx)) relevant.push(singleIdx)
    if (sameIdx >= 0 && valid.includes(25 + sameIdx)) relevant.push(25 + sameIdx)
    if (relevant.length === 0) return
    const rect = (e.target as HTMLElement).getBoundingClientRect()
    popup = { x: rect.left, y: rect.bottom + 4, actions: relevant, labels: relevant.map(actionLabel) }
  }

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
  <div class="token-pool">
    {#each tokenIcons as t, i (t + '-board-' + i)}
      <span
        class="token"
        class:pulse={$isMyTurn}
        style="background:{TOKEN_COLORS[t]}"
        title={t}
        out:sendToken={{ key: t + '-' + i }}
        on:click={(e) => handleTokenClick(e, t)}
      ></span>
    {/each}
  </div>

  {#each rows as row, rowIdx}
    <div class="card-row tier-{row.tier}">
      {#if rowIdx === 0}
        <div class="card-cell empty"></div>
      {:else}
        <div class="card-cell deck-back tier-{row.tier}">
          <span class="deck-count">{row.deckCount}</span>
        </div>
      {/if}
      {#each row.revealed as card, slotIdx (card?.name ?? `empty-${row.tier}-${slotIdx}`)}
        <div class="card-cell" in:fly={{ y: -30, duration: 400 }}>
          <CardSlot
            {card} tier={row.tier}
            highlight={$isMyTurn && card !== null}
            on:click={(e) => handleCardClick(e, slotIdx, row.tier)}
          />
        </div>
      {/each}
    </div>
  {/each}
</div>

{#if popup}
  <ActionMenu
    anchorX={popup.x} anchorY={popup.y}
    actions={popup.actions} labels={popup.labels}
    on:cancel={() => popup = null}
  />
{/if}

<style>
  .board { display: flex; flex-direction: column; gap: 6px; padding: 12px; }
  .token-pool { display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; padding: 8px 0; }
  .token { display: inline-block; width: 18px; height: 18px; border-radius: 50%; border: 1px solid rgba(0,0,0,.25); }
  .token.pulse { cursor: pointer; animation: tok-pulse 1.2s ease-in-out infinite; }
  @keyframes tok-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,255,255,.4); }
    50%       { box-shadow: 0 0 0 5px rgba(255,255,255,0); }
  }
  .card-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; }
  .card-cell { min-height: 110px; }
  .deck-back { border-radius: 8px; display: flex; align-items: center; justify-content: center; cursor: default; position: relative; }
  .deck-back.tier-common    { background: linear-gradient(135deg,#8B6914,#c9a64a); }
  .deck-back.tier-uncommon  { background: linear-gradient(135deg,#7f8c8d,#bdc3c7); }
  .deck-back.tier-rare      { background: linear-gradient(135deg,#c8a415,#f5d60a); }
  .deck-back.tier-epic      { background: linear-gradient(135deg,#6c3483,#a569bd); }
  .deck-back.tier-legendary { background: linear-gradient(135deg,#154360,#2e86c1,#e74c3c,#f39c12); }
  .deck-count { font-size: 1.1rem; font-weight: bold; color: white; text-shadow: 0 1px 2px rgba(0,0,0,.6); }
</style>
