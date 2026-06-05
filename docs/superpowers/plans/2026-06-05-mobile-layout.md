# Mobile Layout (Layout A + Hand Expand) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a mobile-only landscape layout (≤768px screens) with side-rail player panels, a scaled board, and a tap-to-expand hand modal with full action support; desktop layout is completely untouched.

**Architecture:** Five new/modified files, all additive. `App.svelte` detects `isMobile` and renders `MobileLayout` instead of the desktop grid. `MobileLayout` computes left/right player rail assignments, scales `MobileBoard` via `ResizeObserver`, and manages the expand/modal state. Portrait mode is forced to landscape via CSS `rotate(90deg)` on the mobile root element. All game state flows through existing stores — no server changes.

**Tech Stack:** Svelte 5 legacy reactive syntax (`$:`, `on:click`, writable stores), TypeScript, existing `gameStore`, `ws`, `types` — no new dependencies.

---

## File Structure

| File | Status | Responsibility |
|------|--------|----------------|
| `frontend/src/components/MobileBoard.svelte` | **Create** | 462 px board (100×80 cards), pool+epic+legendary top band, 3 lower rows, token staging strip, action menus |
| `frontend/src/components/MobilePlayerRail.svelte` | **Create** | Collapsed 150 px rail: avatar, name, score, token counts, reserved mini-list, expand-cue icon, own-player action hint |
| `frontend/src/components/PlayerHandModal.svelte` | **Create** | Centered pop modal: full lanes, token belt (discard), reserved (catch), pass-evolve; read-only for opponents |
| `frontend/src/components/MobileLayout.svelte` | **Create** | Orchestrates rails + scaled board + modal; player distribution; auto-open on discard phase |
| `frontend/src/App.svelte` | **Modify** | Add `isMobile` detection, conditional render of `MobileLayout`, portrait-→-landscape CSS |

**Do not modify** `Board.svelte`, `PlayerPanel.svelte`, `CardSlot.svelte`, or any server file.

---

## Key constants (used across multiple components, copy into each)

```typescript
const TOKEN_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']
const LANE_ORDER  = ['red', 'yellow', 'blue', 'pink', 'black']

const COL: Record<string, string> = {
  red: '#ff3434', yellow: '#f1c40f', blue: '#3498db',
  pink: '#ffa3da', black: '#9aa0a6', master: '#a569bd',
}
const CARDBG: Record<string, string> = {
  red: '#6b2a2a', yellow: '#5c5020', blue: '#1e3d5c',
  pink: '#a04f78', black: '#2a2a2a', master: '#4a3060',
}
const TIER_BAR: Record<string, string> = {
  common: '#b08d57', uncommon: '#c7ccd1', rare: '#e8b923',
  epic: '#a55fd0', legendary: 'linear-gradient(90deg,#3aa0e0,#f0852e)',
}
const TIER_DECK_GRAD: Record<string, string> = {
  common:    'linear-gradient(135deg,#8B6914,#c9a64a)',
  uncommon:  'linear-gradient(135deg,#7f8c8d,#bdc3c7)',
  rare:      'linear-gradient(135deg,#c8a415,#f5d60a)',
  epic:      'linear-gradient(135deg,#6c3483,#a569bd)',
  legendary: 'linear-gradient(135deg,#154360,#2e86c1,#e74c3c,#f39c12)',
}
const DEX: Record<string, number> = {
  abra:63, aerodactyl:142, alakazam:65, articuno:144, beedrill:15,
  bellsprout:69, blastoise:9, bulbasaur:1, butterfree:12, caterpie:10,
  charizard:6, charmander:4, charmeleon:5, ditto:132, dragonair:148,
  dragonite:149, dratini:147, eevee:133, gastly:92, gengar:94,
  geodude:74, gloom:44, golem:76, graveler:75, haunter:93,
  ivysaur:2, kadabra:64, kakuna:14, lapras:131, machamp:68,
  machoke:67, machop:66, metapod:11, mew:151, mewtwo:150,
  moltres:146, nidoqueen:31, nidoran:29, nidorina:30, oddish:43,
  pidgeot:18, pidgeotto:17, pidgey:16, poliwag:60, poliwhirl:61,
  poliwrath:62, snorlax:143, squirtle:7, venusaur:3, victreebel:71,
  vileplume:45, wartortle:8, weedle:13, weepinbell:70, zapdos:145,
}
function spriteUrl(name: string): string {
  const id = DEX[name.toLowerCase()]
  return id ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${id}.png` : ''
}
```

---

## Action ID reference (from existing engine)

| Range | Action |
|-------|--------|
| 0–24 | Take ≤3 different tokens (combo index) |
| 25–29 | Take 2 same tokens (by color index red/yel/blue/pink/black) |
| 30–43 | Catch from board (absolute slot index) |
| 44–46 | Catch from reserve (reserve index 0/1/2) |
| 47–58 | Reserve + take master ball (board slot, reservable tiers only) |
| 59–70 | Reserve, no master ball |
| 71–76 | Discard token (red/yel/blue/pink/black/master) |
| 77–106 | Evolve card at hand index (77 + origIdx) |
| 107 | Pass evolution |

---

### Task 1: MobileBoard.svelte

**Files:**
- Create: `frontend/src/components/MobileBoard.svelte`

The mobile board follows `design/mobile/components.jsx` `Board()`:
- Top band (462 px wide flex row): token pool (3-col grid, flex:1) + epic deck+card + legendary deck+card
- Three lower rows (462 px): rare, uncommon, common — each deck-back (38 px) + 4 cards (100×80 px)
- Token staging strip: shown inline below all rows when `tokenSelectMode` is active — reuses `TokenStagingArea.svelte`

**Important:** Add `data-token-type={t}` to each pool button so `TokenStagingArea`'s return-animation can query it. Cards must have `data-tier` and `data-slot` attributes (same as desktop) so `catchFlash` reveal works.

- [ ] **Step 1: Create the file with script and all constants**

```svelte
<!-- frontend/src/components/MobileBoard.svelte -->
<script lang="ts">
  import {
    gameState, isMyTurn, humanTurnActions,
    tokenSelectMode, stagedTokens, catchFlash,
  } from '../lib/gameStore'
  import TokenStagingArea from './TokenStagingArea.svelte'
  import ActionMenu from './ActionMenu.svelte'
  import type { PokemonCard } from '../lib/types'
  import { BALL } from '../lib/tokens'
  import { sendAction } from '../lib/ws'

  const TOKEN_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']
  const COL: Record<string, string> = {
    red: '#ff3434', yellow: '#f1c40f', blue: '#3498db',
    pink: '#ffa3da', black: '#9aa0a6', master: '#a569bd',
  }
  const CARDBG: Record<string, string> = {
    red: '#6b2a2a', yellow: '#5c5020', blue: '#1e3d5c',
    pink: '#a04f78', black: '#2a2a2a', master: '#4a3060',
  }
  const TIER_BAR: Record<string, string> = {
    common: '#b08d57', uncommon: '#c7ccd1', rare: '#e8b923',
    epic: '#a55fd0', legendary: 'linear-gradient(90deg,#3aa0e0,#f0852e)',
  }
  const TIER_DECK_GRAD: Record<string, string> = {
    common:    'linear-gradient(135deg,#8B6914,#c9a64a)',
    uncommon:  'linear-gradient(135deg,#7f8c8d,#bdc3c7)',
    rare:      'linear-gradient(135deg,#c8a415,#f5d60a)',
    epic:      'linear-gradient(135deg,#6c3483,#a569bd)',
    legendary: 'linear-gradient(135deg,#154360,#2e86c1,#e74c3c,#f39c12)',
  }
  const DEX: Record<string, number> = {
    abra:63, aerodactyl:142, alakazam:65, articuno:144, beedrill:15,
    bellsprout:69, blastoise:9, bulbasaur:1, butterfree:12, caterpie:10,
    charizard:6, charmander:4, charmeleon:5, ditto:132, dragonair:148,
    dragonite:149, dratini:147, eevee:133, gastly:92, gengar:94,
    geodude:74, gloom:44, golem:76, graveler:75, haunter:93,
    ivysaur:2, kadabra:64, kakuna:14, lapras:131, machamp:68,
    machoke:67, machop:66, metapod:11, mew:151, mewtwo:150,
    moltres:146, nidoqueen:31, nidoran:29, nidorina:30, oddish:43,
    pidgeot:18, pidgeotto:17, pidgey:16, poliwag:60, poliwhirl:61,
    poliwrath:62, snorlax:143, squirtle:7, venusaur:3, victreebel:71,
    vileplume:45, wartortle:8, weedle:13, weepinbell:70, zapdos:145,
  }
  function spriteUrl(name: string): string {
    const id = DEX[name.toLowerCase()]
    return id ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${id}.png` : ''
  }

  const TIER_ABS_OFFSET: Record<string, number> = {
    common: 0, uncommon: 4, rare: 8, epic: 12, legendary: 13,
  }

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
    if (n > types.size) return false   // already take-2-same mode
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

  let popup: { x: number; y: number; actions: number[]; labels: string[] } | null = null

  function handleTokenClick(t: string) {
    if (!canAddToken(t)) return
    popup = null
    stagedTokens.update(s => [...s, t])
    tokenSelectMode.set(true)
  }

  function handleCardClick(e: MouseEvent, tier: string, slotIdx: number) {
    if (!$isMyTurn) return
    if ($tokenSelectMode) { stagedTokens.set([]); tokenSelectMode.set(false); return }
    const absSlot = (TIER_ABS_OFFSET[tier] ?? 0) + slotIdx
    const candidates = absSlot < 12
      ? [30 + absSlot, 47 + absSlot, 59 + absSlot]
      : [30 + absSlot]
    const relevant = candidates.filter(a => $humanTurnActions.includes(a))
    if (!relevant.length) return
    const rect = (e.target as HTMLElement).getBoundingClientRect()
    popup = { x: rect.left, y: rect.bottom + 4, actions: relevant, labels: relevant.map(actionLabel) }
  }

  function actionLabel(id: number): string {
    if (id >= 30 && id < 44) return 'Catch'
    if (id >= 47 && id < 59) return 'Reserve + Master ball'
    if (id >= 59 && id < 71) return 'Reserve'
    return 'Action'
  }

  $: lowerRows = board ? [
    { tier: 'rare',     deckCount: board.rare_deck_count,     revealed: board.rare_revealed },
    { tier: 'uncommon', deckCount: board.uncommon_deck_count, revealed: board.uncommon_revealed },
    { tier: 'common',   deckCount: board.common_deck_count,   revealed: board.common_revealed },
  ] : []
</script>
```

- [ ] **Step 2: Add the template**

Add below the `</script>` tag:

```svelte
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
          disabled={count === 0 && !canAddToken(t)}
          on:click={() => handleTokenClick(t)}
        >
          <img src={BALL[t]} alt={t} width="20" height="20" draggable="false">
          <span class="pool-n">{count}</span>
        </button>
      {/each}
    </div>

    <div class="top-cards">
      <!-- Epic -->
      <div class="deck" style="background:{TIER_DECK_GRAD.epic}">
        <span class="deck-label">Epic</span>
        <span class="deck-count">{board.epic_deck_count}</span>
      </div>
      {#each board.epic_revealed as card, slotIdx}
        {@const absSlot = 12 + slotIdx}
        <div
          class="bcard"
          class:bcard-highlight={$isMyTurn && card !== null && slotHasValidAction(absSlot)}
          class:catch-reveal={$catchFlash?.card === card?.name}
          data-tier="epic" data-slot={slotIdx}
          style={card ? `background:${CARDBG[card.bonus[0]] ?? '#2a2a2a'}` : 'background:#1a1a2e'}
          role="button" tabindex="0"
          on:click={(e) => card && handleCardClick(e, 'epic', slotIdx)}
          on:keydown={(e) => e.key === 'Enter' && card && handleCardClick(e as unknown as MouseEvent, 'epic', slotIdx)}
        >
          {#if card}
            <div class="bcard-bar" style="background:{TIER_BAR.epic}"></div>
            <div class="bcard-head">
              <div class="bcard-names">
                <span class="bcard-name">{card.name}</span>
                {#if card.evolve_into}<span class="bcard-evo">▸ {card.evolve_into}</span>{/if}
              </div>
              <span class="bcard-bonus" style="background:radial-gradient({COL[card.bonus[0]] ?? '#888'}44 0%,transparent 70%)">
                <img src={BALL[card.bonus[0]]} alt={card.bonus[0]} width="13" height="13" draggable="false">
              </span>
            </div>
            <div class="bcard-art"><img src={spriteUrl(card.name)} alt={card.name} width="38" height="38" draggable="false"></div>
            <div class="bcard-cost">
              {#each card.cost as gem}<img src={BALL[gem]} alt={gem} width="11" height="11" draggable="false">{/each}
            </div>
            <div class="bcard-pts" style="box-shadow:inset 0 0 0 2px {COL[card.bonus[0]] ?? '#888'}">{card.point}</div>
          {/if}
        </div>
      {/each}

      <!-- Legendary -->
      <div class="deck" style="background:{TIER_DECK_GRAD.legendary}">
        <span class="deck-label">Leg.</span>
        <span class="deck-count">{board.legendary_deck_count}</span>
      </div>
      {#each board.legendary_revealed as card, slotIdx}
        {@const absSlot = 13 + slotIdx}
        <div
          class="bcard"
          class:bcard-highlight={$isMyTurn && card !== null && slotHasValidAction(absSlot)}
          class:catch-reveal={$catchFlash?.card === card?.name}
          data-tier="legendary" data-slot={slotIdx}
          style={card ? `background:${CARDBG[card.bonus[0]] ?? '#2a2a2a'}` : 'background:#1a1a2e'}
          role="button" tabindex="0"
          on:click={(e) => card && handleCardClick(e, 'legendary', slotIdx)}
          on:keydown={(e) => e.key === 'Enter' && card && handleCardClick(e as unknown as MouseEvent, 'legendary', slotIdx)}
        >
          {#if card}
            <div class="bcard-bar" style="background:{TIER_BAR.legendary}"></div>
            <div class="bcard-head">
              <div class="bcard-names">
                <span class="bcard-name">{card.name}</span>
                {#if card.evolve_into}<span class="bcard-evo">▸ {card.evolve_into}</span>{/if}
              </div>
              <span class="bcard-bonus" style="background:radial-gradient({COL[card.bonus[0]] ?? '#888'}44 0%,transparent 70%)">
                <img src={BALL[card.bonus[0]]} alt={card.bonus[0]} width="13" height="13" draggable="false">
              </span>
            </div>
            <div class="bcard-art"><img src={spriteUrl(card.name)} alt={card.name} width="38" height="38" draggable="false"></div>
            <div class="bcard-cost">
              {#each card.cost as gem}<img src={BALL[gem]} alt={gem} width="11" height="11" draggable="false">{/each}
            </div>
            <div class="bcard-pts" style="box-shadow:inset 0 0 0 2px {COL[card.bonus[0]] ?? '#888'}">{card.point}</div>
          {/if}
        </div>
      {/each}
    </div>
  </div>

  <!-- ── Token staging strip (when active) ── -->
  {#if $tokenSelectMode || $stagedTokens.length > 0}
    <div class="staging-wrap">
      <TokenStagingArea />
    </div>
  {/if}

  <!-- ── Lower rows: rare, uncommon, common ── -->
  {#each lowerRows as row}
    <div class="card-row">
      <div class="deck" style="background:{TIER_DECK_GRAD[row.tier]}">
        <span class="deck-count">{row.deckCount}</span>
      </div>
      {#each row.revealed as card, slotIdx}
        {@const absSlot = (TIER_ABS_OFFSET[row.tier] ?? 0) + slotIdx}
        <div
          class="bcard"
          class:bcard-highlight={$isMyTurn && card !== null && slotHasValidAction(absSlot)}
          class:catch-reveal={$catchFlash?.card === card?.name}
          data-tier={row.tier} data-slot={slotIdx}
          style={card ? `background:${CARDBG[card.bonus[0]] ?? '#2a2a2a'}` : 'background:#1a1a2e'}
          role="button" tabindex="0"
          on:click={(e) => card && handleCardClick(e, row.tier, slotIdx)}
          on:keydown={(e) => e.key === 'Enter' && card && handleCardClick(e as unknown as MouseEvent, row.tier, slotIdx)}
        >
          {#if card}
            <div class="bcard-bar" style="background:{TIER_BAR[row.tier]}"></div>
            <div class="bcard-head">
              <div class="bcard-names">
                <span class="bcard-name">{card.name}</span>
                {#if card.evolve_into}<span class="bcard-evo">▸ {card.evolve_into}</span>{/if}
              </div>
              <span class="bcard-bonus" style="background:radial-gradient({COL[card.bonus[0]] ?? '#888'}44 0%,transparent 70%)">
                <img src={BALL[card.bonus[0]]} alt={card.bonus[0]} width="13" height="13" draggable="false">
              </span>
            </div>
            <div class="bcard-art"><img src={spriteUrl(card.name)} alt={card.name} width="38" height="38" draggable="false"></div>
            <div class="bcard-cost">
              {#each card.cost as gem}<img src={BALL[gem]} alt={gem} width="11" height="11" draggable="false">{/each}
            </div>
            <div class="bcard-pts" style="box-shadow:inset 0 0 0 2px {COL[card.bonus[0]] ?? '#888'}">{card.point}</div>
          {/if}
        </div>
      {/each}
    </div>
  {/each}
</div>
{/if}

{#if popup}
  <ActionMenu
    anchorX={popup.x} anchorY={popup.y}
    actions={popup.actions} labels={popup.labels}
    on:cancel={() => popup = null}
  />
{/if}
```

- [ ] **Step 3: Add the styles**

```svelte
<style>
  .board { display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }
  .board-top { display: flex; gap: 8px; width: 462px; align-items: stretch; }
  .pool { flex: 1; display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; align-content: center; }
  .top-cards { display: flex; gap: 6px; flex: none; }
  .card-row { display: flex; gap: 6px; width: 462px; }
  .staging-wrap { width: 462px; padding: 4px 0; box-sizing: border-box; }

  .pool-tok {
    background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12);
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

  .bcard {
    width: 100px; height: 80px; flex: none; position: relative; color: #fff;
    border: 2px solid #0c0d12; border-radius: 3px; overflow: hidden;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.10), 2px 2px 0 rgba(0,0,0,.42);
    display: flex; flex-direction: column; cursor: default;
  }
  .bcard img { image-rendering: pixelated; display: block; }
  .bcard.bcard-highlight { cursor: pointer; outline: 2px solid #ffd23f; }
  .bcard.bcard-highlight:hover { filter: brightness(1.1); }
  .bcard-bar { height: 3px; flex: none; }
  .bcard-head { display: flex; justify-content: space-between; align-items: flex-start; padding: 3px 4px 0; gap: 3px; }
  .bcard-names { min-width: 0; display: flex; flex-direction: column; }
  .bcard-name { font-family: 'Silkscreen', monospace; font-weight: 700; font-size: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bcard-evo { font-family: 'Silkscreen', monospace; font-size: 6px; color: rgba(255,255,255,.55); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bcard-bonus { flex: none; width: 18px; height: 18px; border-radius: 10px; display: grid; place-items: center; }
  .bcard-art { flex: 1; display: grid; place-items: center; min-height: 0; }
  .bcard-cost { display: flex; flex-wrap: wrap; gap: 1px; padding: 0 22px 3px 4px; align-content: flex-end; }
  .bcard-pts {
    position: absolute; right: 3px; bottom: 3px; width: 18px; height: 18px;
    display: grid; place-items: center; border-radius: 3px;
    background: #0c0d12; font-family: 'Press Start 2P', monospace; font-size: 8px; color: #fff;
  }

  .catch-reveal { animation: catch-reveal 550ms ease-out both; }
  @keyframes catch-reveal {
    0%   { opacity: 0; transform: translateY(6px); }
    100% { opacity: 1; transform: translateY(0); }
  }
</style>
```

- [ ] **Step 4: Verify the file compiles**

```bash
cd /Users/alan/code/splendor/frontend
npm run check 2>&1 | head -40
```
Expected: no errors in `MobileBoard.svelte`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/MobileBoard.svelte
git commit -m "feat: add MobileBoard component for mobile layout"
```

---

### Task 2: MobilePlayerRail.svelte

**Files:**
- Create: `frontend/src/components/MobilePlayerRail.svelte`

This is the collapsed rail shown in the 150 px side columns. It wraps `PlayerRail` from the design:
- Avatar (24×24, gold when active), player name + last-action, score LCD
- Token mini-counts (all 6 types, dimmed when 0)
- Reserved mini-list (stacked: tier-bar strip + sprite + pts)
- `⤢` expand-cue icon (top-right absolute)
- When `isOwnPlayer && isMyTurn`: a pulsing "tap to act" badge when there are pending actions in the current phase (discard or evolve)

Props: `player: PlayerState`, `displayName: string`, `isOwnPlayer: boolean`  
Events: dispatches `expand` when tapped.

- [ ] **Step 1: Create the file**

```svelte
<!-- frontend/src/components/MobilePlayerRail.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import { isMyTurn, humanTurnActions, phase, activePlayer } from '../lib/gameStore'
  import { BALL } from '../lib/tokens'
  import type { PlayerState } from '../lib/types'

  export let player: PlayerState
  export let displayName: string
  export let isOwnPlayer: boolean

  const dispatch = createEventDispatcher<{ expand: void }>()

  const TOKEN_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']
  const TIER_BAR: Record<string, string> = {
    common: '#b08d57', uncommon: '#c7ccd1', rare: '#e8b923',
    epic: '#a55fd0', legendary: 'linear-gradient(90deg,#3aa0e0,#f0852e)',
  }
  const DEX: Record<string, number> = {
    abra:63, aerodactyl:142, alakazam:65, articuno:144, beedrill:15,
    bellsprout:69, blastoise:9, bulbasaur:1, butterfree:12, caterpie:10,
    charizard:6, charmander:4, charmeleon:5, ditto:132, dragonair:148,
    dragonite:149, dratini:147, eevee:133, gastly:92, gengar:94,
    geodude:74, gloom:44, golem:76, graveler:75, haunter:93,
    ivysaur:2, kadabra:64, kakuna:14, lapras:131, machamp:68,
    machoke:67, machop:66, metapod:11, mew:151, mewtwo:150,
    moltres:146, nidoqueen:31, nidoran:29, nidorina:30, oddish:43,
    pidgeot:18, pidgeotto:17, pidgey:16, poliwag:60, poliwhirl:61,
    poliwrath:62, snorlax:143, squirtle:7, venusaur:3, victreebel:71,
    vileplume:45, wartortle:8, weedle:13, weepinbell:70, zapdos:145,
  }
  function spriteUrl(name: string): string {
    const id = DEX[name.toLowerCase()]
    return id ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${id}.png` : ''
  }

  $: isActive = $activePlayer === player.name
  $: avatarNum = (player.name.match(/\d+/) ?? ['?'])[0]
  // Show action-required hint when it's our turn in a phase that needs panel interaction
  $: needsAction = isOwnPlayer && $isMyTurn && isActive &&
    ($phase === 'discard' || $phase === 'evolve')
</script>

<button class="railbtn" on:click={() => dispatch('expand')}>
  <div class="prail" class:active={isActive}>
    <div class="prail-head">
      <div class="avatar" class:avatar-on={isActive}>{avatarNum}</div>
      <div class="meta">
        <span class="pname">{displayName}{#if isActive}<em class="turn">● TURN</em>{/if}</span>
      </div>
      <div class="lcd">{player.points}</div>
    </div>

    <div class="field-label">Pokéballs</div>
    <div class="tmini">
      {#each TOKEN_ORDER as t}
        {@const n = player.tokens[t] ?? 0}
        <span class="tm" class:tz={n === 0}>
          <img src={BALL[t]} alt={t} width="13" height="13" draggable="false">
          <i>{n}</i>
        </span>
      {/each}
    </div>

    {#if player.reserved_cards.length > 0}
      <div class="field-label">Reserved</div>
      <div class="rmini">
        {#each player.reserved_cards as card}
          <span class="rm">
            <span class="rm-bar" style="background:{TIER_BAR[card.tier] ?? '#888'}"></span>
            <img src={spriteUrl(card.name)} alt={card.name} width="16" height="16" draggable="false">
            <span class="rm-name">{card.name}</span>
            <span class="rm-pts">{card.point}</span>
          </span>
        {/each}
      </div>
    {/if}
  </div>

  <span class="expand-cue">⤢</span>
  {#if needsAction}
    <span class="action-badge" aria-label="Action required">!</span>
  {/if}
</button>

<style>
  .railbtn {
    all: unset; box-sizing: border-box;
    display: flex; flex: 1; min-height: 0; cursor: pointer; position: relative;
    width: 100%;
  }
  .prail {
    flex: 1; min-height: 0; padding: 8px;
    background: linear-gradient(180deg, #23252e, #16171d);
    border: 2px solid #0c0d12; border-radius: 8px;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.05), 3px 3px 0 rgba(0,0,0,.35);
    overflow: hidden; display: flex; flex-direction: column; gap: 5px;
    transition: transform .12s ease, filter .12s ease;
  }
  .railbtn:hover .prail { filter: brightness(1.12); }
  .railbtn:active .prail { transform: scale(.985); }
  .prail.active {
    box-shadow: inset 0 0 0 2px rgba(255,210,63,.5), 0 0 0 2px rgba(255,210,63,.5), 3px 3px 0 rgba(0,0,0,.35);
  }
  .prail-head { display: flex; align-items: center; gap: 6px; }

  .avatar {
    width: 24px; height: 24px; flex: none; border-radius: 5px;
    display: grid; place-items: center;
    font-family: 'Press Start 2P', monospace; font-size: 10px;
    color: #0c0d12; background: #6b7280;
    box-shadow: 2px 2px 0 rgba(0,0,0,.4);
  }
  .avatar.avatar-on { background: #ffd23f; }
  .lcd {
    flex: none; min-width: 26px; height: 26px; padding: 0 4px;
    display: grid; place-items: center; border-radius: 5px;
    font-family: 'Press Start 2P', monospace; font-size: 12px; color: #fff;
    background: #0c0d12; box-shadow: inset 0 0 0 2px #ffd23f, 2px 2px 0 rgba(0,0,0,.4);
  }
  .meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
  .pname { font-family: 'Silkscreen', monospace; font-size: 10px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  em.turn { color: #ffd23f; font-style: normal; font-size: 7px; margin-left: 4px; }
  .field-label { font-family: 'Silkscreen', monospace; font-size: 7px; letter-spacing: .8px; text-transform: uppercase; color: rgba(255,255,255,.5); }

  .tmini { display: flex; flex-wrap: wrap; gap: 3px 7px; }
  .tmini img { image-rendering: pixelated; display: block; }
  .tm { display: inline-flex; align-items: center; gap: 2px; }
  .tm i { font-family: 'Press Start 2P', monospace; font-size: 8px; color: #fff; font-style: normal; }
  .tz { opacity: .28; }

  .rmini { display: flex; flex-direction: column; gap: 4px; }
  .rm {
    display: inline-flex; align-items: center; gap: 3px;
    background: rgba(255,255,255,.06); border-radius: 4px;
    padding: 3px 5px 3px 0; overflow: hidden;
  }
  .rm img { image-rendering: pixelated; display: block; }
  .rm-bar { width: 2px; align-self: stretch; flex: none; }
  .rm-name { font-family: 'Silkscreen', monospace; font-size: 8px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; min-width: 0; }
  .rm-pts { font-family: 'Press Start 2P', monospace; font-size: 8px; color: #fff; background: #0c0d12; border-radius: 3px; padding: 2px 3px; flex: none; }

  .expand-cue {
    position: absolute; top: 6px; right: 8px;
    font-size: 12px; color: rgba(255,255,255,.45); pointer-events: none; line-height: 1;
  }
  .railbtn:hover .expand-cue { color: #ffd23f; }

  .action-badge {
    position: absolute; top: 4px; left: 4px;
    width: 16px; height: 16px; border-radius: 50%;
    background: #e74c3c; color: #fff;
    font-family: 'Press Start 2P', monospace; font-size: 8px;
    display: grid; place-items: center; pointer-events: none;
    animation: badge-pulse 1s ease-in-out infinite;
  }
  @keyframes badge-pulse {
    0%,100% { box-shadow: 0 0 0px rgba(231,76,60,0); }
    50%      { box-shadow: 0 0 6px rgba(231,76,60,.8); }
  }
</style>
```

- [ ] **Step 2: Verify compilation**

```bash
cd /Users/alan/code/splendor/frontend
npm run check 2>&1 | head -40
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MobilePlayerRail.svelte
git commit -m "feat: add MobilePlayerRail collapsed rail component"
```

---

### Task 3: PlayerHandModal.svelte

**Files:**
- Create: `frontend/src/components/PlayerHandModal.svelte`

The modal follows `design/mobile/expand.jsx` `PlayerExpanded` + `design/mobile/styles.css` `.xpanel` styles:
- `.xbackdrop` — full-screen dimmed overlay, click to close
- `.xmodal` — centered container, click stops propagation, pop-in animation
- `.xpanel` — two-column: `.xinfo` (210 px fixed, left) + divider + `.xlanes` (flex 1, right)

**xinfo column (own player — interactive; opponent — read-only):**
- Header: avatar (32 px), name + last-action, score LCD (44 px)
- "Pokéballs held" + token list; in discard phase + own player: each token is a tappable discard button with pulsing glow
- "Reserved · N/3" + stacked reserved list; own player + catchable: each card has a "Catch" button
- Pass evolution button (own player only, evolve phase, action 107 in valid actions)
- "✕ Close" button

**xlanes column (both players):**
- Field label "Pokémon caught · N · bonus ball & ▸ evolve"
- `xlane-list`: one row per color lane
  - `poke-rail`: color-tinted ball icon + count badge
  - `lane-cards`: `otile` (48×48) per card; own player + evolvable = tappable with gold outline

Props: `player: PlayerState`, `displayName: string`, `isOwnPlayer: boolean`  
Events: dispatches `close`

Action IDs used here:
- Discard: `{ red:71, yellow:72, blue:73, pink:74, black:75, master:76 }`
- Catch reserved: `44 + idx`
- Evolve: `77 + origIdx` (where `origIdx` is index in `player.cards`)
- Pass evolve: `107`

- [ ] **Step 1: Create the file**

```svelte
<!-- frontend/src/components/PlayerHandModal.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import { isMyTurn, humanTurnActions, phase } from '../lib/gameStore'
  import { sendAction } from '../lib/ws'
  import { BALL } from '../lib/tokens'
  import type { PlayerState, PokemonCard } from '../lib/types'

  export let player: PlayerState
  export let displayName: string
  export let isOwnPlayer: boolean

  const dispatch = createEventDispatcher<{ close: void }>()

  const TOKEN_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']
  const LANE_ORDER  = ['red', 'yellow', 'blue', 'pink', 'black']
  const COL: Record<string, string> = {
    red: '#ff3434', yellow: '#f1c40f', blue: '#3498db',
    pink: '#ffa3da', black: '#9aa0a6', master: '#a569bd',
  }
  const CARDBG: Record<string, string> = {
    red: '#6b2a2a', yellow: '#5c5020', blue: '#1e3d5c',
    pink: '#a04f78', black: '#2a2a2a', master: '#4a3060',
  }
  const TIER_BAR: Record<string, string> = {
    common: '#b08d57', uncommon: '#c7ccd1', rare: '#e8b923',
    epic: '#a55fd0', legendary: 'linear-gradient(90deg,#3aa0e0,#f0852e)',
  }
  const DISCARD_ACTION: Record<string, number> = {
    red: 71, yellow: 72, blue: 73, pink: 74, black: 75, master: 76,
  }
  const DEX: Record<string, number> = {
    abra:63, aerodactyl:142, alakazam:65, articuno:144, beedrill:15,
    bellsprout:69, blastoise:9, bulbasaur:1, butterfree:12, caterpie:10,
    charizard:6, charmander:4, charmeleon:5, ditto:132, dragonair:148,
    dragonite:149, dratini:147, eevee:133, gastly:92, gengar:94,
    geodude:74, gloom:44, golem:76, graveler:75, haunter:93,
    ivysaur:2, kadabra:64, kakuna:14, lapras:131, machamp:68,
    machoke:67, machop:66, metapod:11, mew:151, mewtwo:150,
    moltres:146, nidoqueen:31, nidoran:29, nidorina:30, oddish:43,
    pidgeot:18, pidgeotto:17, pidgey:16, poliwag:60, poliwhirl:61,
    poliwrath:62, snorlax:143, squirtle:7, venusaur:3, victreebel:71,
    vileplume:45, wartortle:8, weedle:13, weepinbell:70, zapdos:145,
  }
  function spriteUrl(name: string): string {
    const id = DEX[name.toLowerCase()]
    return id ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${id}.png` : ''
  }

  $: avatarNum = (player.name.match(/\d+/) ?? ['?'])[0]
  $: totalCards = player.cards.length
  $: totalTokens = Object.values(player.tokens).reduce((a, b) => a + b, 0)
  $: discardMode = isOwnPlayer && $isMyTurn && $phase === 'discard'
  $: evolveMode  = isOwnPlayer && $isMyTurn && $phase === 'evolve'
  $: passEvolve  = evolveMode && $humanTurnActions.includes(107)

  $: lanes = (() => {
    const groups: Record<string, { card: PokemonCard; origIdx: number }[]> = {}
    for (let i = 0; i < player.cards.length; i++) {
      const card = player.cards[i]
      const color = card.bonus[0] ?? 'black'
      ;(groups[color] ??= []).push({ card, origIdx: i })
    }
    return LANE_ORDER
      .map(c => ({ color: c, items: groups[c] ?? [] }))
  })()

  function canDiscard(t: string): boolean {
    return discardMode && $humanTurnActions.includes(DISCARD_ACTION[t] ?? -1)
  }
  function canCatch(idx: number): boolean {
    return isOwnPlayer && $isMyTurn && $humanTurnActions.includes(44 + idx)
  }
  function canEvolve(origIdx: number): boolean {
    return evolveMode && $humanTurnActions.includes(77 + origIdx)
  }

  function handleDiscard(t: string) {
    if (!canDiscard(t)) return
    sendAction(DISCARD_ACTION[t])
    dispatch('close')
  }
  function handleCatch(idx: number) {
    if (!canCatch(idx)) return
    sendAction(44 + idx)
    dispatch('close')
  }
  function handleEvolve(origIdx: number) {
    if (!canEvolve(origIdx)) return
    sendAction(77 + origIdx)
    dispatch('close')
  }
  function handlePassEvolve() {
    sendAction(107)
    dispatch('close')
  }
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="xbackdrop" on:click={() => dispatch('close')}>
  <div class="xmodal" on:click|stopPropagation>
    <div class="xpanel">

      <!-- Left column: info + actions -->
      <div class="xinfo">
        <div class="xhead">
          <div class="xavatar">{avatarNum}</div>
          <div class="meta">
            <span class="pname">{displayName}</span>
          </div>
          <div class="xlcd">{player.points}</div>
        </div>

        <div class="field-label">Pokéballs held · {totalTokens}/10</div>
        {#if discardMode}
          <div class="discard-hint">Too many — tap one to discard</div>
        {/if}
        <div class="xtokens">
          {#each TOKEN_ORDER as t}
            {@const n = player.tokens[t] ?? 0}
            {@const discardable = canDiscard(t)}
            <button
              class="tok-btn"
              class:tok-zero={n === 0}
              class:tok-discardable={discardable}
              disabled={!discardable && !isOwnPlayer}
              on:click={() => handleDiscard(t)}
            >
              <img src={BALL[t]} alt={t} width="16" height="16" draggable="false">
              <i>{n}</i>
            </button>
          {/each}
        </div>

        <div class="field-label">Reserved · {player.reserved_cards.length}/3</div>
        <div class="xreserved">
          {#each player.reserved_cards as card, idx}
            {@const catchable = canCatch(idx)}
            <div class="xrm" class:xrm-catchable={catchable} on:click={() => handleCatch(idx)}>
              <span class="rm-bar" style="background:{TIER_BAR[card.tier] ?? '#888'}"></span>
              <img src={spriteUrl(card.name)} alt={card.name} width="18" height="18" draggable="false">
              <span class="rm-name">{card.name}</span>
              <span class="rm-pts">{card.point}</span>
              {#if catchable}<span class="catch-tag">Catch</span>{/if}
            </div>
          {/each}
          {#if player.reserved_cards.length === 0}
            <span class="none-text">— none —</span>
          {/if}
        </div>

        {#if passEvolve}
          <button class="pass-btn" on:click={handlePassEvolve}>Pass evolution</button>
        {/if}

        <button class="xclose" on:click={() => dispatch('close')}>✕ Close</button>
      </div>

      <div class="xdiv"></div>

      <!-- Right column: lanes -->
      <div class="xlanes">
        <div class="field-label">Pokémon caught · {totalCards} · bonus ball &amp; ▸ evolve</div>
        <div class="xlane-list">
          {#each lanes as { color, items }}
            {@const bonusCount = items.reduce((s, { card }) => card.evolved ? s : s + card.bonus.length, 0)}
            <div class="xlane" class:empty={items.length === 0}>
              <div class="poke-rail" style="background:linear-gradient(180deg,{COL[color]}26,{COL[color]}0a); box-shadow:inset 0 0 0 1px {COL[color]}55">
                <img src={BALL[color]} alt={color} width="16" height="16" draggable="false">
                <span class="rail-count">{bonusCount}</span>
              </div>
              <div class="lane-cards">
                {#if items.length}
                  {#each items as { card, origIdx }}
                    {@const evolvable = canEvolve(origIdx)}
                    <button
                      class="otile"
                      class:evolvable
                      class:evo-consumed={card.evolved}
                      style="background:{CARDBG[color] ?? '#2a2a2a'}"
                      on:click={() => handleEvolve(origIdx)}
                      title="{card.name}{card.evolve_into ? ' ▸ ' + card.evolve_into : ' · MAX'}"
                    >
                      <span class="otile-bar" style="background:{TIER_BAR[card.tier] ?? '#888'}"></span>
                      <img src={spriteUrl(card.name)} alt={card.name} width="30" height="30" draggable="false">
                      <span class="otile-name">{card.name}</span>
                      {#if card.point > 0}<span class="otile-pts">{card.point}</span>{/if}
                    </button>
                  {/each}
                {:else}
                  <span class="lane-empty">— none yet —</span>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>

    </div>
  </div>
</div>

<style>
  /* ── Backdrop + modal ── */
  .xbackdrop {
    position: absolute; inset: 0;
    background: rgba(5,5,12,.72);
    display: grid; place-items: center; z-index: 50;
    animation: xfade .14s ease;
  }
  @keyframes xfade { from { opacity: 0; } to { opacity: 1; } }
  .xmodal {
    width: 850px; max-width: 95%; height: auto; max-height: 95%;
    animation: xpop .2s cubic-bezier(.34,1.4,.64,1);
  }
  @keyframes xpop {
    from { opacity: 0; transform: scale(.93) translateY(6px); }
    to   { opacity: 1; transform: scale(1) translateY(0); }
  }
  .xpanel {
    width: 100%; max-height: 100%; display: flex; gap: 12px;
    padding: 13px; box-sizing: border-box; overflow: hidden;
    background: linear-gradient(180deg, #23252e, #16171d);
    border: 3px solid #0c0d12; border-radius: 12px;
    box-shadow: inset 0 0 0 2px rgba(255,255,255,.05), 0 18px 50px rgba(0,0,0,.6);
    color: #fff;
  }

  /* ── Left column ── */
  .xinfo { width: 210px; flex: none; display: flex; flex-direction: column; gap: 8px; min-height: 0; }
  .xhead { display: flex; align-items: center; gap: 9px; }
  .xavatar {
    width: 32px; height: 32px; flex: none; border-radius: 5px;
    display: grid; place-items: center;
    font-family: 'Press Start 2P', monospace; font-size: 13px;
    color: #0c0d12; background: #6b7280;
    box-shadow: 2px 2px 0 rgba(0,0,0,.4);
  }
  .xlcd {
    flex: none; min-width: 44px; height: 44px; padding: 0 5px;
    display: grid; place-items: center; border-radius: 5px;
    font-family: 'Press Start 2P', monospace; font-size: 21px; color: #fff;
    background: #0c0d12; box-shadow: inset 0 0 0 2px #ffd23f, 2px 2px 0 rgba(0,0,0,.4);
  }
  .meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .pname { font-family: 'Silkscreen', monospace; font-size: 10px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .field-label { font-family: 'Silkscreen', monospace; font-size: 7px; letter-spacing: .8px; text-transform: uppercase; color: rgba(255,255,255,.5); }
  .discard-hint { font-family: 'Silkscreen', monospace; font-size: 8px; color: #e74c3c; }

  /* Tokens */
  .xtokens { display: flex; flex-wrap: wrap; gap: 6px 12px; }
  .tok-btn {
    background: none; border: none; padding: 0; cursor: default;
    display: inline-flex; align-items: center; gap: 3px;
  }
  .tok-btn img { image-rendering: pixelated; display: block; }
  .tok-btn i { font-family: 'Press Start 2P', monospace; font-size: 10px; color: #fff; font-style: normal; }
  .tok-zero i { opacity: .28; }
  .tok-discardable { cursor: pointer; animation: discard-pulse 1s ease-in-out infinite; }
  .tok-discardable:hover { filter: brightness(1.3); transform: scale(1.15); }
  @keyframes discard-pulse {
    0%,100% { filter: drop-shadow(0 0 0px rgba(231,76,60,0)); }
    50%     { filter: drop-shadow(0 0 5px rgba(231,76,60,.9)); }
  }

  /* Reserved */
  .xreserved { display: flex; flex-direction: column; gap: 6px; }
  .xrm {
    display: flex; align-items: center; gap: 4px;
    background: rgba(255,255,255,.06); border-radius: 4px;
    padding: 4px 7px 4px 0; overflow: hidden; cursor: default;
  }
  .xrm img { image-rendering: pixelated; display: block; }
  .xrm.xrm-catchable { cursor: pointer; outline: 1.5px solid #ffd23f; animation: catch-pulse 1s ease-in-out infinite; }
  @keyframes catch-pulse {
    0%,100% { filter: drop-shadow(0 0 0px rgba(255,210,63,0)); }
    50%     { filter: drop-shadow(0 0 5px rgba(255,210,63,.8)); }
  }
  .rm-bar { width: 2px; align-self: stretch; flex: none; }
  .rm-name { font-family: 'Silkscreen', monospace; font-size: 9px; color: #fff; flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .rm-pts { font-family: 'Press Start 2P', monospace; font-size: 8px; color: #fff; background: #0c0d12; border-radius: 3px; padding: 2px 3px; flex: none; }
  .catch-tag { font-family: 'Silkscreen', monospace; font-size: 7px; background: #27ae60; color: #fff; border-radius: 3px; padding: 1px 4px; flex: none; }
  .none-text { font-family: 'Silkscreen', monospace; font-size: 9px; color: rgba(255,255,255,.3); }

  /* Buttons */
  .pass-btn {
    background: transparent; color: rgba(255,255,255,.5);
    border: 1px solid rgba(255,255,255,.15); border-radius: 5px;
    font-family: 'Silkscreen', monospace; font-size: 9px;
    padding: 7px 14px; cursor: pointer; align-self: flex-start;
  }
  .pass-btn:hover { background: rgba(255,255,255,.08); color: #fff; }
  .xclose {
    margin-top: auto; align-self: flex-start;
    background: rgba(255,255,255,.08); color: #fff;
    border: 1px solid rgba(255,255,255,.2); border-radius: 6px;
    font-family: 'Silkscreen', monospace; font-size: 9px;
    padding: 7px 14px; cursor: pointer;
  }
  .xclose:hover { background: rgba(255,255,255,.16); }

  /* ── Divider ── */
  .xdiv { width: 2px; align-self: stretch; background: rgba(255,255,255,.08); flex: none; }

  /* ── Lanes ── */
  .xlanes { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 7px; min-height: 0; }
  .xlane-list { display: flex; flex-direction: column; gap: 5px; min-height: 0; overflow-y: auto; }
  .xlane { display: flex; gap: 7px; align-items: stretch; flex: none; min-height: 50px; }
  .xlane.empty { opacity: .5; }
  .poke-rail {
    width: 34px; flex: none; border-radius: 4px;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
  }
  .poke-rail img { image-rendering: pixelated; display: block; }
  .rail-count { font-family: 'Press Start 2P', monospace; font-size: 9px; color: #fff; }
  .lane-cards {
    flex: 1; min-width: 0; display: flex; gap: 5px;
    align-items: center; flex-wrap: wrap; align-content: center;
    background: rgba(255,255,255,.03); border-radius: 4px; padding: 3px 6px;
  }
  .lane-empty { font-family: 'Silkscreen', monospace; font-size: 9px; color: rgba(255,255,255,.25); letter-spacing: 1px; }

  /* OwnedTile */
  .otile {
    width: 48px; height: 48px; flex: none; position: relative;
    border: 2px solid #0c0d12; border-radius: 3px; overflow: hidden;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.1);
    display: flex; flex-direction: column; align-items: center;
    color: #fff; cursor: default; padding: 0;
  }
  .otile img { image-rendering: pixelated; display: block; margin-top: 3px; }
  .otile.evolvable { cursor: pointer; outline: 1.5px solid #ffd23f; }
  .otile.evolvable:hover { filter: brightness(1.15); }
  .otile.evo-consumed { opacity: .4; cursor: default; outline: none; }
  .otile-bar { position: absolute; top: 0; left: 0; right: 0; height: 3px; }
  .otile-name { font-family: 'Silkscreen', monospace; font-size: 6px; line-height: 1; max-width: 44px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 1px; color: rgba(255,255,255,.82); }
  .otile-pts { position: absolute; bottom: 1px; right: 1px; font-family: 'Press Start 2P', monospace; font-size: 6px; background: #0c0d12; border-radius: 2px; padding: 1px 2px; }
</style>
```

- [ ] **Step 2: Verify compilation**

```bash
cd /Users/alan/code/splendor/frontend
npm run check 2>&1 | head -40
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PlayerHandModal.svelte
git commit -m "feat: add PlayerHandModal expanded player hand with actions"
```

---

### Task 4: MobileLayout.svelte

**Files:**
- Create: `frontend/src/components/MobileLayout.svelte`

Responsibilities:
1. Compute `leftPlayers` and `rightPlayers` from `$gameState.players` + `$mySlot`
2. Wrap board in a `ResizeObserver`-driven scaler (same as `FitBoard` from `design/mobile/expand.jsx`)
3. Render two `.railcol` divs wrapping `MobilePlayerRail` components
4. Manage `expandedPlayerName: string | null`
5. Auto-open modal when `$phase === 'discard' && $isMyTurn`
6. Render `PlayerHandModal` when expanded

**Player distribution logic:**
- 2p: left = [human], right = [other]
- 3p: left = [human], right = [other1, other2]
- 4p: left = [human, players[(humanIdx+3)%4]], right = remaining two

The board scaler: a wrapper div (`boardArea`) measured by `ResizeObserver`; the inner `.board-scale` div gets `transform: translate(-50%,-50%) scale(s)` where `s = min(areaW/462, areaH/boardH)`. The board's natural height is approximately 346 px (top band ~88 px + staging ~0 + 3 rows × (80+6 gap) = 258 px + outer gap 6×3).

- [ ] **Step 1: Create the file**

```svelte
<!-- frontend/src/components/MobileLayout.svelte -->
<script lang="ts">
  import { onMount } from 'svelte'
  import {
    gameState, mySlot, isMyTurn, phase, playerNames, lastActions,
  } from '../lib/gameStore'
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
    const hi = slot ?? 0  // human index
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

  // Auto-open own panel when discard phase requires action
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
  <div class="railcol">
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
  <div class="boardArea" bind:this={boardArea}>
    <div class="board-scale" style="transform: translate(-50%,-50%) scale({scale})">
      <MobileBoard />
    </div>
  </div>

  <!-- Right rail column -->
  <div class="railcol">
    {#each rails.right as p (p.name)}
      <MobilePlayerRail
        player={p}
        displayName={displayName(p)}
        isOwnPlayer={p.name === myPlayerName}
        on:expand={() => expandedPlayerName = p.name}
      />
    {/each}
  </div>

  <!-- Hint pill (when no modal is open) -->
  {#if !expandedPlayerName}
    <div class="hint">Tap a player to open their hand</div>
  {/if}

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
    width: 150px; flex: none;
    display: flex; flex-direction: column;
    gap: 8px; min-height: 0;
  }

  .boardArea {
    position: relative; overflow: hidden;
    flex: 1; min-width: 0;
  }
  .board-scale {
    position: absolute; top: 50%; left: 50%;
  }

  .hint {
    position: absolute; bottom: 9px; left: 50%;
    transform: translateX(-50%); z-index: 40;
    font-family: 'Silkscreen', monospace;
    font-size: 9px; color: rgba(255,255,255,.55);
    background: rgba(0,0,0,.45); padding: 4px 12px;
    border-radius: 20px; pointer-events: none;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
  }
</style>
```

- [ ] **Step 2: Verify compilation**

```bash
cd /Users/alan/code/splendor/frontend
npm run check 2>&1 | head -40
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MobileLayout.svelte
git commit -m "feat: add MobileLayout with scaled board, rails, and hand modal"
```

---

### Task 5: App.svelte integration + portrait CSS

**Files:**
- Modify: `frontend/src/App.svelte`

Two changes:
1. Add `isMobile` detection via `window.matchMedia('(max-width: 768px)')` in `onMount`; update on `change` events
2. In the game view, render `<div class="mobile-root"><MobileLayout /></div>` when `isMobile`, existing grid otherwise
3. Add CSS: `.mobile-root` fills screen in landscape; in portrait on phones rotate 90° so content always appears landscape

The portrait CSS forces landscape visually:
```
portrait transform: translate(-50%, -50%) rotate(90deg)
with width = 100svh, height = 100svw, position fixed centered
```
This works because after rotating 90°, what was `100svh` wide and `100svw` tall now fills the screen rotated.

- [ ] **Step 1: Add imports and isMobile state to `App.svelte` script**

Open `frontend/src/App.svelte`. At the top of the `<script>` block, add after the existing imports:

```svelte
  import { onMount } from 'svelte'
  import MobileLayout from './components/MobileLayout.svelte'
  // ... (keep all existing imports)

  let isMobile = false
  onMount(() => {
    const mq = window.matchMedia('(max-width: 768px)')
    isMobile = mq.matches
    const handler = (e: MediaQueryListEvent) => { isMobile = e.matches }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  })
```

- [ ] **Step 2: Wrap the game view in a mobile-root div and conditionally render MobileLayout**

In the `{:else if view === 'game'}` block, replace the existing content with:

```svelte
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
```

Note: tutorial overlay is desktop-only for now (mobile tutorial can be a follow-up).

- [ ] **Step 3: Add mobile-root CSS and portrait rotation to the `<style>` block**

Add at the bottom of the existing `<style>` block in `App.svelte`:

```css
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
```

- [ ] **Step 4: Verify compilation**

```bash
cd /Users/alan/code/splendor/frontend
npm run check 2>&1 | head -40
```
Expected: no type errors.

- [ ] **Step 5: Run dev server and manually test**

```bash
cd /Users/alan/code/splendor/frontend
npm run dev
```

Open `http://localhost:5173` in a browser. In DevTools, enable mobile device simulation (iPhone 14 landscape: 844×390).

Check:
- Desktop (>768px): existing layout renders normally, no regressions
- Mobile (≤768px landscape): two side rails visible, board scaled in center
- Tapping a rail: modal pops open with full hand
- Tapping backdrop: modal closes
- Tapping own tokens (discard phase): discard action fires, modal closes
- Tapping reserved card (catchable): catch fires, modal closes
- Tapping evolvable tile: evolve fires, modal closes
- Portrait mode (phone rotated): content rotates to appear landscape

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.svelte
git commit -m "feat: integrate MobileLayout into App.svelte with portrait-to-landscape CSS"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Layout A (side rails 150px + scaled board) — MobileLayout, MobileBoard
- ✅ Board: pool+epic+legendary top band, 3 lower rows, 100×80 cards — MobileBoard
- ✅ Board scales to fit via ResizeObserver — MobileLayout boardArea + board-scale
- ✅ Tap-to-expand centered modal pop — MobilePlayerRail dispatches `expand`, PlayerHandModal with xbackdrop/xmodal
- ✅ All 4 human actions in expanded modal: discard token, catch reserved, evolve, pass-evolve — PlayerHandModal
- ✅ Auto-open on discard phase — MobileLayout reactive `$: if ($phase === 'discard' && $isMyTurn)`
- ✅ Expand-cue `⤢` icon — MobilePlayerRail
- ✅ Action hint badge on own rail — MobilePlayerRail `needsAction` + `.action-badge`
- ✅ Any player expandable (read-only opponents) — PlayerHandModal `isOwnPlayer` flag
- ✅ Player distribution: 2p/3p/4p — computeRails()
- ✅ Force landscape in portrait — App.svelte portrait CSS
- ✅ Desktop untouched — all changes additive, no existing component modified except App.svelte
- ✅ Mobile only at ≤768px — `isMobile` matchMedia gate + CSS media query

**2. Placeholder scan:** No TODOs, TBDs, or vague instructions. All code fully written.

**3. Type consistency:**
- `player: PlayerState` — consistent across all components
- `PokemonCard.bonus[0]` — primary color, used for CARDBG/COL lookups consistently
- `PokemonCard.evolve_into` — string (empty string = no evolution), checked as truthy
- Action IDs (discard 71-76, catch 44+idx, evolve 77+origIdx, pass 107) — consistent across PlayerHandModal and the action ID reference table
- `computeRails` returns `{ left: PlayerState[], right: PlayerState[] }` — consumed directly in MobileLayout template

**Known limitation:** `TokenStagingArea`'s fly-arc animation targets `[data-player-name]` on confirm, which won't exist in mobile layout (no PlayerPanel). The animation is guarded by `if (panelEl)` so it silently skips — functionality is unaffected.
