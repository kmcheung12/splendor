<!-- frontend/src/components/MobileBoard.svelte -->
<script lang="ts">
  import {
    gameState, isMyTurn, humanTurnActions,
    tokenSelectMode, stagedTokens, catchFlash,
  } from '../lib/gameStore'
  import TokenStagingArea from './TokenStagingArea.svelte'
  import CardDetailModal from './CardDetailModal.svelte'
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

  const GEM_ORDER = ['red', 'yellow', 'blue', 'pink', 'black']
  function groupCost(gems: string[]): { c: string; n: number }[] {
    const counts: Record<string, number> = {}
    for (const g of gems) counts[g] = (counts[g] ?? 0) + 1
    return GEM_ORDER.filter(c => counts[c]).map(c => ({ c, n: counts[c] }))
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
    const relevant = $isMyTurn
      ? candidates.filter(a => $humanTurnActions.includes(a))
      : []
    cardDetail = { card, tier, actions: relevant.map(a => ({ id: a, label: actionLabel(a) })) }
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
        <div
          class="bcard"
          class:bcard-highlight={$isMyTurn && card !== null && slotHasValidAction(absSlot)}
          class:catch-reveal={$catchFlash?.card === card?.name}
          class:jumping={jumpingKey === `epic-${slotIdx}`}
          data-tier="epic" data-slot={slotIdx}
          style={card ? `background:${CARDBG[card.bonus[0]] ?? '#2a2a2a'}` : 'background:#1a1a2e'}
          role="button" tabindex="0"
          on:click={() => card && handleCardClick(card, 'epic', slotIdx)}
          on:keydown={(e) => e.key === 'Enter' && card && handleCardClick(card, 'epic', slotIdx)}
        >
          {#if card}
            <div class="bcard-bar" style="background:{TIER_BAR.epic}"></div>
            <div class="bcard-head">
              <div class="bcard-names">
                <span class="bcard-name">{card.name}</span>
                {#if card.evolve_into}
                  <span class="bcard-evo-row">
                    {#if card.evolve?.length}
                      {#each groupCost(card.evolve) as g}
                        <span class="cv-u cv-u-xs" style="--gc:{COL[g.c]}"><span class="cv-n cv-n-xs">{g.n}</span><img class="cv-mb cv-mb-xs" src={BALL[g.c]} alt={g.c} width="7" height="7" draggable="false"></span>
                      {/each}
                    {/if}
                    <span class="bcard-evo">▸ {card.evolve_into}</span>
                  </span>
                {/if}
              </div>
              <span class="bcard-bonus" style="background:{CARDBG[card.bonus[0]] ?? '#2a2a2a'}">
                <span class="bcard-bonus-bar" style="background:{COL[card.bonus[0]] ?? '#888'}"></span>
                <img src={BALL[card.bonus[0]]} alt={card.bonus[0]} width="10" height="10" draggable="false">
              </span>
            </div>
            <div class="bcard-art"><img src={spriteUrl(card.name)} alt={card.name} width="38" height="38" draggable="false"></div>
            <div class="bcard-cost">
              {#if card.cost.length}
                {@const grouped = groupCost(card.cost)}
                {#if grouped.length > 3}
                  <div class="cv cv-stack">
                    <div class="cv-row">
                      {#each grouped.slice(0, grouped.length - 3) as g}
                        <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} width="8" height="8" draggable="false"></span>
                      {/each}
                    </div>
                    <div class="cv-row">
                      {#each grouped.slice(-3) as g}
                        <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} width="8" height="8" draggable="false"></span>
                      {/each}
                    </div>
                  </div>
                {:else}
                  <div class="cv">
                    {#each grouped as g}
                      <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} width="8" height="8" draggable="false"></span>
                    {/each}
                  </div>
                {/if}
              {/if}
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
          class:jumping={jumpingKey === `legendary-${slotIdx}`}
          data-tier="legendary" data-slot={slotIdx}
          style={card ? `background:${CARDBG[card.bonus[0]] ?? '#2a2a2a'}` : 'background:#1a1a2e'}
          role="button" tabindex="0"
          on:click={() => card && handleCardClick(card, 'legendary', slotIdx)}
          on:keydown={(e) => e.key === 'Enter' && card && handleCardClick(card, 'legendary', slotIdx)}
        >
          {#if card}
            <div class="bcard-bar" style="background:{TIER_BAR.legendary}"></div>
            <div class="bcard-head">
              <div class="bcard-names">
                <span class="bcard-name">{card.name}</span>
                {#if card.evolve_into}
                  <span class="bcard-evo-row">
                    {#if card.evolve?.length}
                      {#each groupCost(card.evolve) as g}
                        <span class="cv-u cv-u-xs" style="--gc:{COL[g.c]}"><span class="cv-n cv-n-xs">{g.n}</span><img class="cv-mb cv-mb-xs" src={BALL[g.c]} alt={g.c} width="7" height="7" draggable="false"></span>
                      {/each}
                    {/if}
                    <span class="bcard-evo">▸ {card.evolve_into}</span>
                  </span>
                {/if}
              </div>
              <span class="bcard-bonus" style="background:{CARDBG[card.bonus[0]] ?? '#2a2a2a'}">
                <span class="bcard-bonus-bar" style="background:{COL[card.bonus[0]] ?? '#888'}"></span>
                <img src={BALL[card.bonus[0]]} alt={card.bonus[0]} width="10" height="10" draggable="false">
              </span>
            </div>
            <div class="bcard-art"><img src={spriteUrl(card.name)} alt={card.name} width="38" height="38" draggable="false"></div>
            <div class="bcard-cost">
              {#if card.cost.length}
                {@const grouped = groupCost(card.cost)}
                {#if grouped.length > 3}
                  <div class="cv cv-stack">
                    <div class="cv-row">
                      {#each grouped.slice(0, grouped.length - 3) as g}
                        <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} width="8" height="8" draggable="false"></span>
                      {/each}
                    </div>
                    <div class="cv-row">
                      {#each grouped.slice(-3) as g}
                        <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} width="8" height="8" draggable="false"></span>
                      {/each}
                    </div>
                  </div>
                {:else}
                  <div class="cv">
                    {#each grouped as g}
                      <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} width="8" height="8" draggable="false"></span>
                    {/each}
                  </div>
                {/if}
              {/if}
            </div>
            <div class="bcard-pts" style="box-shadow:inset 0 0 0 2px {COL[card.bonus[0]] ?? '#888'}">{card.point}</div>
          {/if}
        </div>
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
        <div
          class="bcard"
          class:bcard-highlight={$isMyTurn && card !== null && slotHasValidAction(absSlot)}
          class:catch-reveal={$catchFlash?.card === card?.name}
          class:jumping={jumpingKey === `${row.tier}-${slotIdx}`}
          data-tier={row.tier} data-slot={slotIdx}
          style={card ? `background:${CARDBG[card.bonus[0]] ?? '#2a2a2a'}` : 'background:#1a1a2e'}
          role="button" tabindex="0"
          on:click={() => card && handleCardClick(card, row.tier, slotIdx)}
          on:keydown={(e) => e.key === 'Enter' && card && handleCardClick(card, row.tier, slotIdx)}
        >
          {#if card}
            <div class="bcard-bar" style="background:{TIER_BAR[row.tier]}"></div>
            <div class="bcard-head">
              <div class="bcard-names">
                <span class="bcard-name">{card.name}</span>
                {#if card.evolve_into}
                  <span class="bcard-evo-row">
                    {#if card.evolve?.length}
                      {#each groupCost(card.evolve) as g}
                        <span class="cv-u cv-u-xs" style="--gc:{COL[g.c]}"><span class="cv-n cv-n-xs">{g.n}</span><img class="cv-mb cv-mb-xs" src={BALL[g.c]} alt={g.c} width="7" height="7" draggable="false"></span>
                      {/each}
                    {/if}
                    <span class="bcard-evo">▸ {card.evolve_into}</span>
                  </span>
                {/if}
              </div>
              <span class="bcard-bonus" style="background:{CARDBG[card.bonus[0]] ?? '#2a2a2a'}">
                <span class="bcard-bonus-bar" style="background:{COL[card.bonus[0]] ?? '#888'}"></span>
                <img src={BALL[card.bonus[0]]} alt={card.bonus[0]} width="10" height="10" draggable="false">
              </span>
            </div>
            <div class="bcard-art"><img src={spriteUrl(card.name)} alt={card.name} width="38" height="38" draggable="false"></div>
            <div class="bcard-cost">
              {#if card.cost.length}
                {@const grouped = groupCost(card.cost)}
                {#if grouped.length > 3}
                  <div class="cv cv-stack">
                    <div class="cv-row">
                      {#each grouped.slice(0, grouped.length - 3) as g}
                        <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} width="8" height="8" draggable="false"></span>
                      {/each}
                    </div>
                    <div class="cv-row">
                      {#each grouped.slice(-3) as g}
                        <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} width="8" height="8" draggable="false"></span>
                      {/each}
                    </div>
                  </div>
                {:else}
                  <div class="cv">
                    {#each grouped as g}
                      <span class="cv-u" style="--gc:{COL[g.c]}"><span class="cv-n">{g.n}</span><img class="cv-mb" src={BALL[g.c]} alt={g.c} width="8" height="8" draggable="false"></span>
                    {/each}
                  </div>
                {/if}
              {/if}
            </div>
            <div class="bcard-pts" style="box-shadow:inset 0 0 0 2px {COL[card.bonus[0]] ?? '#888'}">{card.point}</div>
          {/if}
        </div>
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

  .bcard {
    width: 100px; height: 80px; flex: none; position: relative; color: #fff;
    border: 2px solid #0c0d12; border-radius: 3px; overflow: hidden;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.10), 2px 2px 0 rgba(0,0,0,.42);
    display: flex; flex-direction: column; cursor: pointer;
    box-sizing: border-box;
  }
  .bcard img { image-rendering: pixelated; display: block; }
  .bcard.bcard-highlight { cursor: pointer; outline: 2px solid #ffd23f; }
  .bcard.bcard-highlight:hover { filter: brightness(1.1); }
  .bcard.jumping { overflow: visible; z-index: 10; }
  .bcard.jumping .bcard-art img {
    animation: poke-jump 480ms cubic-bezier(.23,.54,.46,.77) forwards;
  }
  @keyframes poke-jump {
    0%   { transform: translateY(0px); }
    50%  { transform: translateY(-18px); animation-timing-function: cubic-bezier(.54,.23,.77,.46); }
    100% { transform: translateY(0px); }
  }
  .bcard-bar { height: 3px; flex: none; }
  .bcard-head { display: flex; justify-content: space-between; align-items: flex-start; padding: 3px 4px 0; gap: 3px; }
  .bcard-names { min-width: 0; display: flex; flex-direction: column; }
  .bcard-name { font-family: 'Silkscreen', monospace; font-weight: 700; font-size: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bcard-evo { font-family: 'Silkscreen', monospace; font-size: 6px; color: rgba(255,255,255,.55); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bcard-evo-row { display: flex; gap: 3px; align-items: center; flex-wrap: nowrap; overflow: hidden; }
  .cv-u-xs { width: 12px; height: 12px; }
  .cv-n-xs { font-size: 5px; }
  .cv-mb-xs { width: 7px; height: 7px; }
  .bcard-bonus {
    position: relative; flex: none; width: 15px; height: 19px; border-radius: 3px; overflow: hidden;
    display: grid; place-items: center;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.18), 0 0 0 1px rgba(0,0,0,.55), 1px 1px 0 rgba(0,0,0,.4);
  }
  .bcard-bonus-bar { position: absolute; top: 0; left: 0; right: 0; height: 2px; }
  .bcard-art { flex: 1; display: grid; place-items: center; min-height: 0; }
  .bcard-cost { display: flex; align-items: flex-end; padding: 0 22px 3px 4px; }

  /* count-forward token (variant B) */
  .cv { display: flex; flex-wrap: wrap; gap: 2px; align-items: center; }
  .cv-stack { display: flex; flex-direction: column; gap: 2px; align-items: flex-start; }
  .cv-row { display: flex; gap: 2px; align-items: center; }
  .cv-u {
    position: relative; width: 16px; height: 16px; border-radius: 50%; flex: none;
    background: #0c0d12; display: grid; place-items: center;
    box-shadow: inset 0 0 0 2px var(--gc, #555);
  }
  .cv-n { font-family: 'Press Start 2P', monospace; font-size: 7px; color: #fff; text-shadow: 1px 1px 0 rgba(0,0,0,.6); }
  .cv-mb { position: absolute; right: -2px; bottom: -2px; image-rendering: pixelated; display: block; }
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
