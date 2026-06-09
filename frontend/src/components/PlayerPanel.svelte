<script lang="ts">
  import type { PlayerState, PokemonCard } from '../lib/types'
  import CardSlot from './CardSlot.svelte'
  import ActionMenu from './ActionMenu.svelte'
  import { activePlayer, lastActions, phase, isMyTurn, humanTurnActions, evolveFlash, catchFlash } from '../lib/gameStore'
  import { sendAction } from '../lib/ws'
  import { BALL } from '../lib/tokens'

  export let player: PlayerState
  export let position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' = 'bottom-left'
  export let displayName: string = player.name

  import { TIER_BAR, TOKEN_ORDER, LANE_ORDER, DISCARD_ACTION, spriteUrl, groupCost } from '../lib/gameData'

  const GEMS: Record<string, { accent: string; bg: string }> = {
    red:    { accent: '#ff3434', bg: '#6b2a2a' },
    yellow: { accent: '#f1c40f', bg: '#5c5020' },
    blue:   { accent: '#3498db', bg: '#1e3d5c' },
    pink:   { accent: '#ffa3da', bg: '#a04f78' },
    black:  { accent: '#9aa0a6', bg: '#2a2a2a' },
    master: { accent: '#f39c12', bg: '#6e5212' },
  }

  function costTitle(cost: string[]): string {
    return groupCost(cost).map(({ c, n }) => `${n}${c[0].toUpperCase()}`).join(' ')
  }

  $: orient = (position === 'top-left' || position === 'top-right') ? 'v' : 'h'
  $: microW = orient === 'v' ? 24 : 30
  $: isActive = $activePlayer === player.name
  $: discardMode = $isMyTurn && $phase === 'discard' && isActive
  $: evolveMode = $isMyTurn && $phase === 'evolve' && isActive
  $: passEvolve = $isMyTurn && $phase === 'evolve' && $humanTurnActions.includes(107)
  $: avatarNum = (player.name.match(/\d+/) ?? ['?'])[0]
  $: totalTokens = Object.values(player.tokens).reduce((a, b) => a + b, 0)
  $: heldTypes = TOKEN_ORDER.filter(t => (player.tokens[t] ?? 0) > 0)

  $: lanes = (() => {
    const groups: Record<string, { card: PokemonCard; origIdx: number }[]> = {}
    for (let i = 0; i < player.cards.length; i++) {
      const card = player.cards[i]
      const color = card.bonus[0] ?? 'black'
      ;(groups[color] ??= []).push({ card, origIdx: i })
    }
    return LANE_ORDER
      .filter(c => (groups[c]?.length ?? 0) > 0)
      .map(c => ({ color: c, items: groups[c] }))
  })()

  $: totalCards = player.cards.length
  $: density = totalCards > 18 ? 'ultra' : totalCards > 9 ? 'dense' : 'roomy'

  function canEvolve(origIdx: number): boolean {
    return evolveMode && $humanTurnActions.includes(77 + origIdx)
  }

  function handleEvolve(origIdx: number) {
    if (canEvolve(origIdx)) sendAction(77 + origIdx)
  }

  function handleTokenDiscard(t: string) {
    if (!discardMode) return
    const actionId = DISCARD_ACTION[t]
    if (actionId !== undefined && $humanTurnActions.includes(actionId)) sendAction(actionId)
  }

  let reservedPopup: { x: number; y: number; actions: number[]; labels: string[] } | null = null

  function handleReservedClick(e: MouseEvent, idx: number) {
    if (!$isMyTurn) return
    const actionId = 44 + idx
    if (!$humanTurnActions.includes(actionId)) return
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    reservedPopup = { x: rect.left, y: rect.bottom + 4, actions: [actionId], labels: ['Catch'] }
  }

  let hoverCard: PokemonCard | null = null
  let hoverX = 0
  let hoverY = 0
  let hoverBelow = false

  function showHover(e: MouseEvent, card: PokemonCard) {
    hoverCard = card
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    // scale(2) visual size: 316×260. With transform-origin bottom-center,
    // visual left = hoverX - 79, right = hoverX + 237
    hoverX = Math.max(83, Math.min(window.innerWidth - 241, rect.left + rect.width / 2 - 79))
    hoverY = rect.top - 138
    hoverBelow = hoverY < 4
    if (hoverBelow) hoverY = rect.bottom + 4
  }

  function hideHover() { hoverCard = null }
</script>

<!-- ── HOVER CARD POPUP ─────────────────────────────── -->
{#if hoverCard}
  <div class="hover-popup" class:below={hoverBelow} style="left:{hoverX}px; top:{hoverY}px">
    <CardSlot card={hoverCard} tier={hoverCard.tier} noPop />
  </div>
{/if}

<!-- ── PANEL ────────────────────────────────────────── -->
<div class="panel" class:active={isActive} class:orient-v={orient==='v'} class:orient-h={orient==='h'} data-player-name={player.name}>

  {#if orient === 'v'}
    <!-- ── VERTICAL (side docks) ── -->
    <div class="header">
      <div class="avatar pp-num" class:avatar-active={isActive}>{avatarNum}</div>
      <div class="header-info">
        <div class="pp-name player-name">
          {displayName}{#if isActive}<span class="turn-tag">● TURN</span>{/if}
        </div>
        {#if $lastActions[player.name]}
          <div class="pp-name last-action">{$lastActions[player.name]}</div>
        {/if}
      </div>
      <div class="score-lcd pp-num">{player.points}</div>
    </div>
    <div class="divider-h"></div>

    <div class="lanes-wrap">
      <div class="field-label">Bonus Poké ball · ▸ evolve</div>
      <div class="lanes" class:gap-ultra={density==='ultra'}>
        {#each lanes as { color, items }}
          {@const gem = GEMS[color] ?? GEMS.black}
          <div class="lane">
            <div class="poke-rail" style="background:{gem.bg}; box-shadow:inset 0 0 0 2px {gem.accent}">
              <img src={BALL[color]} alt={color} width="15" height="15" draggable="false">
              <span class="pp-num rail-count">{items.reduce((s, {card}) => card.evolved ? s : s + card.bonus.length, 0)}</span>
            </div>
            <div class="lane-cards">
              {#each items as { card, origIdx }}
                {@const hasEvo = !!card.evolve_into}
                {@const evolvable = canEvolve(origIdx)}
                {#if card.evolved}
                  {#if density === 'roomy'}
                    <div class="evo-strip evo-consumed" title="{card.name} (evolved ↑)"></div>
                  {:else if density === 'dense'}
                    <div class="evo-tile-mini evo-consumed" title="{card.name} (evolved ↑)"></div>
                  {:else}
                    <div class="evo-tile-micro evo-consumed" style="width:{microW}px; height:{microW}px" title="{card.name} (evolved ↑)"></div>
                  {/if}
                {:else}
                {#if density === 'roomy'}
                  <button class="evo-strip" class:evolvable
                    class:evo-flash={$evolveFlash?.player === player.name && $evolveFlash?.cardIndex === origIdx}
                    class:catch-reveal={$catchFlash?.player === player.name && $catchFlash?.card === card.name}
                    data-card-index={origIdx}
                    style="background:{gem.bg}; box-shadow:inset 0 0 0 2px rgba(0,0,0,.4)"
                    title="{card.name}{hasEvo ? ' ▸ '+card.evolve_into : ' · MAX'}"
                    on:click={() => handleEvolve(origIdx)}
                    on:mouseenter={(e) => showHover(e, card)}
                    on:mouseleave={hideHover}
                  >
                    <div class="tier-bar" style="background:{TIER_BAR[card.tier] ?? '#888'}"></div>
                    <img src={spriteUrl(card.name)} alt={card.name} width="22" height="22" draggable="false">
                    {#if hasEvo}
                      <span class="evo-arrow" style="color:{gem.accent}">▸</span>
                      <img src={spriteUrl(card.evolve_into)} alt={card.evolve_into} width="18" height="18" draggable="false">
                      <span class="strip-name pp-name">{card.evolve_into}</span>
                      <div class="cost-chips">
                        {#each groupCost(card.evolve) as { c: g, n: count }}
                          <span class="chip">
                            <img src={BALL[g]} alt={g} width="10" height="10" draggable="false">
                            <span class="pp-num" style="font-size:8px">{count}</span>
                          </span>
                        {/each}
                      </div>
                    {:else}
                      <span class="strip-name pp-name">{card.name}</span>
                      <span class="max-tag" style="color:{gem.accent}">★ MAX</span>
                    {/if}
                  </button>
                {:else if density === 'dense'}
                  <button class="evo-tile-mini" class:evolvable
                    class:evo-flash={$evolveFlash?.player === player.name && $evolveFlash?.cardIndex === origIdx}
                    class:catch-reveal={$catchFlash?.player === player.name && $catchFlash?.card === card.name}
                    data-card-index={origIdx}
                    style="background:{gem.bg}; box-shadow:inset 0 0 0 2px {gem.accent}99"
                    title="{card.name}{hasEvo ? ' ▸ '+card.evolve_into : ' · MAX'}"
                    on:click={() => handleEvolve(origIdx)}
                    on:mouseenter={(e) => showHover(e, card)}
                    on:mouseleave={hideHover}
                  >
                    <div class="tile-top">
                      <img src={spriteUrl(card.name)} alt={card.name} width="18" height="18" draggable="false">
                      {#if hasEvo}
                        <span class="evo-arrow-sm" style="color:{gem.accent}">▸</span>
                        <img src={spriteUrl(card.evolve_into)} alt={card.evolve_into} width="15" height="15" draggable="false">
                      {:else}
                        <span style="color:{gem.accent}; font-size:8px; margin-left:2px">★</span>
                      {/if}
                    </div>
                    <div class="tile-cost">
                      {#if hasEvo}
                        {#each groupCost(card.evolve) as { c: g, n: count }}
                          <span class="chip">
                            <img src={BALL[g]} alt={g} width="9" height="9" draggable="false">
                            <span class="pp-num" style="font-size:7px">{count}</span>
                          </span>
                        {/each}
                      {:else}
                        <span class="pp-name" style="font-size:6.5px; color:rgba(255,255,255,.55)">final</span>
                      {/if}
                    </div>
                  </button>
                {:else}
                  <button class="evo-tile-micro" class:evolvable
                    class:evo-flash={$evolveFlash?.player === player.name && $evolveFlash?.cardIndex === origIdx}
                    class:catch-reveal={$catchFlash?.player === player.name && $catchFlash?.card === card.name}
                    data-card-index={origIdx}
                    style="width:{microW}px; height:{microW}px; background:{gem.bg}; box-shadow:inset 0 0 0 2px {gem.accent}99"
                    title="{hasEvo ? card.name+' ▸ '+card.evolve_into+'  (cost '+costTitle(card.evolve)+')' : card.name+' · MAX'}"
                    on:click={() => handleEvolve(origIdx)}
                    on:mouseenter={(e) => showHover(e, card)}
                    on:mouseleave={hideHover}
                  >
                    <img src={spriteUrl(card.name)} alt={card.name} width={microW-9} height={microW-9} draggable="false">
                    {#if hasEvo}
                      <span class="micro-badge" style="box-shadow:0 0 0 1.5px {gem.accent}">
                        <img src={spriteUrl(card.evolve_into)} alt={card.evolve_into} width="12" height="12" draggable="false">
                      </span>
                    {:else}
                      <span class="micro-star pp-num" style="color:{gem.accent}">★</span>
                    {/if}
                  </button>
                {/if}
                {/if}
              {/each}
            </div>
          </div>
        {/each}
      </div>
    </div>

    <div class="bottom-group">
      {#if discardMode}
        <div class="discard-banner">Too many pokéballs — discard one ({totalTokens}/10)</div>
      {/if}
      <div class="belt-header">
        <div class="field-label">Poké Balls</div>
        <span class="tok-total pp-num">{totalTokens}/10</span>
      </div>
      <div class="token-belt">
        {#if heldTypes.length}
          {#each heldTypes as t}
            {@const count = player.tokens[t] ?? 0}
            {@const discardable = discardMode && $humanTurnActions.includes(DISCARD_ACTION[t])}
            <button class="tok-chip" class:discardable
              on:click={() => handleTokenDiscard(t)}
              title={discardMode ? `Discard ${t}` : t}
            >
              <img src={BALL[t]} alt={t} width="18" height="18" draggable="false">
              <span class="pp-num" style="font-size:9px; color:#fff">{count}</span>
            </button>
          {/each}
        {:else}
          <span class="pp-name none-text">—</span>
        {/if}
      </div>
      {#if player.reserved_cards.length > 0}
        <div class="field-label">Reserved · cost &amp; pts</div>
        <div class="reserved-col">
          {#each player.reserved_cards as card, idx}
            {@const gem = GEMS[card.bonus[0] ?? 'black'] ?? GEMS.black}
            {@const catchable = $isMyTurn && $humanTurnActions.includes(44 + idx)}
            <button class="reserved-strip" class:catchable
              style="background:{gem.bg}; box-shadow:inset 0 0 0 2px rgba(0,0,0,.4)"
              on:click={(e) => handleReservedClick(e, idx)}
              on:mouseenter={(e) => showHover(e, card)}
              on:mouseleave={hideHover}
            >
              <div class="tier-bar" style="background:{TIER_BAR[card.tier] ?? '#888'}"></div>
              <img src={spriteUrl(card.name)} alt={card.name} width="20" height="20" draggable="false">
              <span class="pp-name strip-name" style="max-width:52px">{card.name}</span>
              <div class="cost-chips" style="flex:1; justify-content:flex-end">
                {#each groupCost(card.cost) as { c: g, n: count }}
                  <span class="chip">
                    <img src={BALL[g]} alt={g} width="10" height="10" draggable="false">
                    <span class="pp-num" style="font-size:8px">{count}</span>
                  </span>
                {/each}
              </div>
              <div class="pts-mini pp-num" style="box-shadow:inset 0 0 0 2px {gem.accent}">{card.point}</div>
            </button>
          {/each}
        </div>
      {/if}
      {#if passEvolve}
        <button class="pass-btn pp-name" on:click={() => sendAction(107)}>Pass evolution</button>
      {/if}
    </div>

  {:else}
    <!-- ── HORIZONTAL (bottom docks) ── -->
    <div class="info-col">
      <div class="header">
        <div class="avatar pp-num" class:avatar-active={isActive}>{avatarNum}</div>
        <div class="header-info">
          <div class="pp-name player-name">
            {displayName}{#if isActive}<span class="turn-tag">● TURN</span>{/if}
          </div>
          {#if $lastActions[player.name]}
            <div class="pp-name last-action">{$lastActions[player.name]}</div>
          {/if}
        </div>
        <div class="score-lcd pp-num">{player.points}</div>
      </div>
      <div class="belt-header">
        <div class="field-label">Poké Balls</div>
        <span class="tok-total pp-num">{totalTokens}/10</span>
      </div>
      <div class="token-belt">
        {#if heldTypes.length}
          {#each heldTypes as t}
            {@const count = player.tokens[t] ?? 0}
            {@const discardable = discardMode && $humanTurnActions.includes(DISCARD_ACTION[t])}
            <button class="tok-chip" class:discardable
              on:click={() => handleTokenDiscard(t)}
              title={discardMode ? `Discard ${t}` : t}
            >
              <img src={BALL[t]} alt={t} width="18" height="18" draggable="false">
              <span class="pp-num" style="font-size:9px; color:#fff">{count}</span>
            </button>
          {/each}
        {:else}
          <span class="pp-name none-text">—</span>
        {/if}
      </div>
      {#if discardMode}
        <div class="discard-banner">Too many pokéballs — discard one ({totalTokens}/10)</div>
      {/if}
      <div class="bottom-group" style="margin-top:auto">
        {#if player.reserved_cards.length > 0}
          <div class="field-label">Reserved · cost &amp; pts</div>
          <div class="reserved-row">
            {#each player.reserved_cards as card, idx}
              {@const gem = GEMS[card.bonus[0] ?? 'black'] ?? GEMS.black}
              {@const catchable = $isMyTurn && $humanTurnActions.includes(44 + idx)}
              <button class="reserved-strip" class:catchable
                style="background:{gem.bg}; box-shadow:inset 0 0 0 2px rgba(0,0,0,.4)"
                on:click={(e) => handleReservedClick(e, idx)}
                on:mouseenter={(e) => showHover(e, card)}
                on:mouseleave={hideHover}
              >
                <div class="tier-bar" style="background:{TIER_BAR[card.tier] ?? '#888'}"></div>
                <img src={spriteUrl(card.name)} alt={card.name} width="20" height="20" draggable="false">
                <span class="pp-name strip-name" style="max-width:52px">{card.name}</span>
                <div class="cost-chips" style="flex:1; justify-content:flex-end">
                  {#each groupCost(card.cost) as { c: g, n: count }}
                    <span class="chip">
                      <img src={BALL[g]} alt={g} width="10" height="10" draggable="false">
                      <span class="pp-num" style="font-size:8px">{count}</span>
                    </span>
                  {/each}
                </div>
                <div class="pts-mini pp-num" style="box-shadow:inset 0 0 0 2px {gem.accent}">{card.point}</div>
              </button>
            {/each}
          </div>
        {/if}
        {#if passEvolve}
          <button class="pass-btn pp-name" on:click={() => sendAction(107)}>Pass evolution</button>
        {/if}
      </div>
    </div>

    <div class="divider-v"></div>

    <div class="lanes-right">
      <div class="field-label">Bonus Poké ball · ▸ evolve</div>
      <div class="lanes" class:gap-ultra={density==='ultra'}>
        {#each lanes as { color, items }}
          {@const gem = GEMS[color] ?? GEMS.black}
          <div class="lane">
            <div class="poke-rail" style="background:{gem.bg}; box-shadow:inset 0 0 0 2px {gem.accent}">
              <img src={BALL[color]} alt={color} width="15" height="15" draggable="false">
              <span class="pp-num rail-count">{items.reduce((s, {card}) => card.evolved ? s : s + card.bonus.length, 0)}</span>
            </div>
            <div class="lane-cards">
              {#each items as { card, origIdx }}
                {@const hasEvo = !!card.evolve_into}
                {@const evolvable = canEvolve(origIdx)}
                {#if card.evolved}
                  {#if density === 'roomy'}
                    <div class="evo-strip evo-strip-h evo-consumed" title="{card.name} (evolved ↑)"></div>
                  {:else if density === 'dense'}
                    <div class="evo-tile-mini evo-consumed" title="{card.name} (evolved ↑)"></div>
                  {:else}
                    <div class="evo-tile-micro evo-consumed" style="width:{microW}px; height:{microW}px" title="{card.name} (evolved ↑)"></div>
                  {/if}
                {:else}
                {#if density === 'roomy'}
                  <button class="evo-strip evo-strip-h" class:evolvable
                    class:evo-flash={$evolveFlash?.player === player.name && $evolveFlash?.cardIndex === origIdx}
                    class:catch-reveal={$catchFlash?.player === player.name && $catchFlash?.card === card.name}
                    data-card-index={origIdx}
                    style="background:{gem.bg}; box-shadow:inset 0 0 0 2px rgba(0,0,0,.4)"
                    title="{card.name}{hasEvo ? ' ▸ '+card.evolve_into : ' · MAX'}"
                    on:click={() => handleEvolve(origIdx)}
                    on:mouseenter={(e) => showHover(e, card)}
                    on:mouseleave={hideHover}
                  >
                    <div class="tier-bar" style="background:{TIER_BAR[card.tier] ?? '#888'}"></div>
                    <img src={spriteUrl(card.name)} alt={card.name} width="22" height="22" draggable="false">
                    {#if hasEvo}
                      <span class="evo-arrow" style="color:{gem.accent}">▸</span>
                      <img src={spriteUrl(card.evolve_into)} alt={card.evolve_into} width="18" height="18" draggable="false">
                      <span class="strip-name pp-name">{card.evolve_into}</span>
                      <div class="cost-chips">
                        {#each groupCost(card.evolve) as { c: g, n: count }}
                          <span class="chip">
                            <img src={BALL[g]} alt={g} width="10" height="10" draggable="false">
                            <span class="pp-num" style="font-size:8px">{count}</span>
                          </span>
                        {/each}
                      </div>
                    {:else}
                      <span class="strip-name pp-name">{card.name}</span>
                      <span class="max-tag" style="color:{gem.accent}">★ MAX</span>
                    {/if}
                  </button>
                {:else if density === 'dense'}
                  <button class="evo-tile-mini" class:evolvable
                    class:evo-flash={$evolveFlash?.player === player.name && $evolveFlash?.cardIndex === origIdx}
                    class:catch-reveal={$catchFlash?.player === player.name && $catchFlash?.card === card.name}
                    data-card-index={origIdx}
                    style="background:{gem.bg}; box-shadow:inset 0 0 0 2px {gem.accent}99"
                    title="{card.name}{hasEvo ? ' ▸ '+card.evolve_into : ' · MAX'}"
                    on:click={() => handleEvolve(origIdx)}
                    on:mouseenter={(e) => showHover(e, card)}
                    on:mouseleave={hideHover}
                  >
                    <div class="tile-top">
                      <img src={spriteUrl(card.name)} alt={card.name} width="18" height="18" draggable="false">
                      {#if hasEvo}
                        <span class="evo-arrow-sm" style="color:{gem.accent}">▸</span>
                        <img src={spriteUrl(card.evolve_into)} alt={card.evolve_into} width="15" height="15" draggable="false">
                      {:else}
                        <span style="color:{gem.accent}; font-size:8px; margin-left:2px">★</span>
                      {/if}
                    </div>
                    <div class="tile-cost">
                      {#if hasEvo}
                        {#each groupCost(card.evolve) as { c: g, n: count }}
                          <span class="chip">
                            <img src={BALL[g]} alt={g} width="9" height="9" draggable="false">
                            <span class="pp-num" style="font-size:7px">{count}</span>
                          </span>
                        {/each}
                      {:else}
                        <span class="pp-name" style="font-size:6.5px; color:rgba(255,255,255,.55)">final</span>
                      {/if}
                    </div>
                  </button>
                {:else}
                  <button class="evo-tile-micro" class:evolvable
                    class:evo-flash={$evolveFlash?.player === player.name && $evolveFlash?.cardIndex === origIdx}
                    class:catch-reveal={$catchFlash?.player === player.name && $catchFlash?.card === card.name}
                    data-card-index={origIdx}
                    style="width:{microW}px; height:{microW}px; background:{gem.bg}; box-shadow:inset 0 0 0 2px {gem.accent}99"
                    title="{hasEvo ? card.name+' ▸ '+card.evolve_into+'  (cost '+costTitle(card.evolve)+')' : card.name+' · MAX'}"
                    on:click={() => handleEvolve(origIdx)}
                    on:mouseenter={(e) => showHover(e, card)}
                    on:mouseleave={hideHover}
                  >
                    <img src={spriteUrl(card.name)} alt={card.name} width={microW-9} height={microW-9} draggable="false">
                    {#if hasEvo}
                      <span class="micro-badge" style="box-shadow:0 0 0 1.5px {gem.accent}">
                        <img src={spriteUrl(card.evolve_into)} alt={card.evolve_into} width="12" height="12" draggable="false">
                      </span>
                    {:else}
                      <span class="micro-star pp-num" style="color:{gem.accent}">★</span>
                    {/if}
                  </button>
                {/if}
                {/if}
              {/each}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

{#if reservedPopup}
  <ActionMenu
    anchorX={reservedPopup.x} anchorY={reservedPopup.y}
    actions={reservedPopup.actions} labels={reservedPopup.labels}
    on:cancel={() => reservedPopup = null}
  />
{/if}

<style>
  /* ── Fonts ── */
  .pp-num  { font-family: 'Press Start 2P', monospace; }
  .pp-name { font-family: 'Silkscreen', monospace; }

  /* ── Panel frame ── */
  .panel {
    box-sizing: border-box;
    padding: 14px;
    border-radius: 8px;
    background: linear-gradient(180deg, #23252e, #16171d);
    border: 3px solid #0c0d12;
    box-shadow: inset 0 0 0 2px rgba(255,255,255,.05), 6px 6px 0 rgba(0,0,0,.4);
    overflow: hidden;
    color: #fff;
    position: relative;
  }
  .panel::after {
    content: ''; position: absolute; inset: 0; pointer-events: none; z-index: 0;
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
    animation: holo-sweep-panel 3.2s ease-in-out infinite alternate; animation-play-state: paused;
  }
  .panel:hover::after { opacity: 1; animation-play-state: running; }
  @keyframes holo-sweep-panel {
    from { background-position:   0% 0%; }
    to   { background-position: 100% 100%; }
  }
  .panel.active {
    box-shadow:
      inset 0 0 0 2px rgba(255,210,63,.45),
      0 0 0 3px rgba(255,210,63,.55),
      6px 6px 0 rgba(0,0,0,.4);
  }
  .panel.orient-v {
    display: flex; flex-direction: column; gap: 11px;
  }
  .panel.orient-h {
    display: flex; flex-direction: row; gap: 14px;
  }

  /* ── Header ── */
  .header { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
  .avatar {
    width: 30px; height: 30px; flex: none;
    border-radius: 5px; display: grid; place-items: center;
    font-size: 12px; color: #0c0d12; background: #6b7280;
    box-shadow: 2px 2px 0 rgba(0,0,0,.4);
  }
  .avatar-active { background: #ffd23f; color: #0c0d12; }
  .header-info { flex: 1; min-width: 0; }
  .player-name { font-size: 12px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.15; }
  .turn-tag { color: #ffd23f; font-size: 7.5px; margin-left: 6px; }
  .last-action { font-size: 8.5px; color: rgba(255,255,255,.45); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.25; }
  .score-lcd {
    flex: none; min-width: 42px; height: 42px; padding: 0 6px;
    display: grid; place-items: center; border-radius: 5px;
    font-size: 20px; color: #fff; background: #0c0d12;
    box-shadow: inset 0 0 0 2px #ffd23f, 2px 2px 0 rgba(0,0,0,.4);
  }

  /* ── Dividers ── */
  .divider-h { height: 2px; background: rgba(255,255,255,.07); box-shadow: 0 1px 0 rgba(0,0,0,.45); flex-shrink: 0; }
  .divider-v { width: 2px; align-self: stretch; background: rgba(255,255,255,.07); flex-shrink: 0; }

  /* ── Field label ── */
  .field-label {
    font-family: 'Silkscreen', monospace;
    font-size: 8px; letter-spacing: .9px; text-transform: uppercase;
    color: rgba(255,255,255,.5); margin-bottom: 6px;
  }

  /* ── Lanes section ── */
  .lanes-wrap { flex: 1; min-height: 0; overflow: hidden; }
  .lanes-right { flex: 1; min-width: 0; overflow: hidden; }
  .lanes { display: flex; flex-direction: column; gap: 6px; }
  .lanes.gap-ultra { gap: 4px; }
  .lane { display: flex; gap: 6px; align-items: stretch; }

  /* PokeRail */
  .poke-rail {
    flex: none; width: 24px; align-self: stretch;
    border-radius: 3px;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  }

  .rail-count { font-size: 9px; color: #fff; }

  /* Lane cards */
  .lane-cards { flex: 1; min-width: 0; display: flex; flex-wrap: wrap; gap: 4px; align-content: flex-start; }

  /* ── EvoStrip ── */
  .evo-strip {
    height: 28px; width: 100%; box-sizing: border-box;
    border-radius: 3px; border: none; cursor: default;
    display: flex; align-items: center; gap: 5px;
    padding: 0 7px 0 0; overflow: hidden;
  }
  .evo-strip-h { width: 100px; }
  .evo-strip.evolvable { cursor: pointer; outline: 1.5px solid #ffd23f; }
  .evo-strip:hover { filter: brightness(1.12); }
  .tier-bar { width: 2px; align-self: stretch; flex-shrink: 0; }
  .evo-arrow { font-size: 12px; flex: none; line-height: 1; }
  .strip-name {
    flex: 1; min-width: 0; font-size: 9px; color: #fff;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .max-tag { font-size: 7.5px; letter-spacing: .6px; flex: none; }
  .cost-chips { display: flex; gap: 3px; flex-wrap: wrap; align-items: center; }
  .chip { display: inline-flex; align-items: center; gap: 1px; }

  /* ── EvoTileMini ── */
  .evo-tile-mini {
    width: 52px; box-sizing: border-box;
    border-radius: 3px; border: none; cursor: default;
    display: flex; flex-direction: column; align-items: center; gap: 1px;
    padding: 3px 2px 2px; overflow: hidden;
  }
  .evo-tile-mini.evolvable { cursor: pointer; outline: 1.5px solid #ffd23f; }
  .evo-tile-mini:hover { filter: brightness(1.12); }
  .tile-top { display: flex; align-items: center; gap: 0; height: 20px; }
  .evo-arrow-sm { font-size: 8px; line-height: 1; color: inherit; }
  .tile-cost { display: flex; flex-wrap: wrap; justify-content: center; gap: 1px 2px; }

  /* ── Catch reveal (fade in after catching) ── */
  .catch-reveal {
    animation: catch-reveal 550ms ease-out both;
  }
  @keyframes catch-reveal {
    0%   { opacity: 0; transform: translateY(6px); filter: drop-shadow(0 0  0px rgba(255,255,255,0)); }
    40%  { opacity: 0.6; }
    70%  { filter: drop-shadow(0 0 5px rgba(255,255,255,.5)); }
    100% { opacity: 1; transform: translateY(0); filter: drop-shadow(0 0  0px rgba(255,255,255,0)); }
  }

  /* ── Evolution flash ── */
  .evo-flash {
    animation: evo-flash 0.65s ease-out forwards;
  }
  @keyframes evo-flash {
    0%   { filter: brightness(1)   drop-shadow(0 0  0px rgba(255,210,63,0)); }
    25%  { filter: brightness(2.2) drop-shadow(0 0 10px rgba(255,210,63,.9)); }
    60%  { filter: brightness(1.5) drop-shadow(0 0  6px rgba(255,210,63,.55)); }
    100% { filter: brightness(1)   drop-shadow(0 0  0px rgba(255,210,63,0)); }
  }

  /* ── Evolved (consumed) placeholder ── */
  .evo-consumed {
    background: rgba(255,255,255,.06) !important;
    box-shadow: inset 0 0 0 1.5px rgba(255,255,255,.1) !important;
    opacity: 0.45;
    cursor: default !important;
    outline: none !important;
  }

  /* ── EvoTileMicro ── */
  .evo-tile-micro {
    border-radius: 3px; border: none; cursor: default;
    display: grid; place-items: center; position: relative;
    flex-shrink: 0;
  }
  .evo-tile-micro.evolvable { cursor: pointer; outline: 1.5px solid #ffd23f; }
  .evo-tile-micro:hover { filter: brightness(1.12); }
  .micro-badge {
    position: absolute; right: -4px; bottom: -4px;
    width: 15px; height: 15px; border-radius: 50%;
    background: #0c0d12; display: grid; place-items: center;
  }
  .micro-star {
    position: absolute; right: -3px; bottom: -3px;
    width: 11px; height: 11px; font-size: 7px; border-radius: 50%;
    background: #0c0d12; display: grid; place-items: center;
    box-shadow: 0 0 0 1px rgba(0,0,0,.5);
  }

  /* Sprites and balls inside this panel */
  .panel img { image-rendering: pixelated; display: block; }
  .hover-popup img { image-rendering: pixelated; display: block; }

  /* ── Belt header row ── */
  .belt-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
  .belt-header .field-label { margin-bottom: 0; }
  .tok-total { font-size: 8px; color: rgba(255,255,255,.45); }

  /* ── Token belt ── */
  .token-belt { display: flex; flex-wrap: wrap; gap: 7px 12px; }
  .tok-chip {
    background: none; border: none; padding: 0; cursor: default;
    display: inline-flex; align-items: center; gap: 3px;
  }
  .tok-chip.discardable { cursor: pointer; animation: discard-pulse 1s ease-in-out infinite; }
  .tok-chip.discardable:hover { filter: brightness(1.3); transform: scale(1.15); }
  .none-text { font-size: 9px; color: rgba(255,255,255,.3); }
  @keyframes discard-pulse {
    0%, 100% { filter: drop-shadow(0 0 0px rgba(231,76,60,0)); }
    50%       { filter: drop-shadow(0 0 5px rgba(231,76,60,.9)); }
  }

  /* ── Discard banner ── */
  .discard-banner {
    font-family: 'Silkscreen', monospace;
    font-size: .7rem; color: #e74c3c; font-weight: bold;
    background: rgba(231,76,60,.15); border: 1px solid rgba(231,76,60,.4);
    border-radius: 5px; padding: 3px 8px;
  }

  /* ── Reserved strip ── */
  .reserved-strip {
    height: 28px; width: 100%; box-sizing: border-box;
    border-radius: 3px; border: none; cursor: default;
    display: flex; align-items: center; gap: 5px;
    padding: 0 5px 0 0; overflow: hidden;
  }
  .reserved-strip.catchable { cursor: pointer; outline: 1.5px solid #ffd23f; }
  .reserved-strip:hover { filter: brightness(1.1); }
  .reserved-col { display: flex; flex-direction: column; gap: 4px; }
  .reserved-row { display: flex; flex-wrap: wrap; gap: 4px; }
  .reserved-row .reserved-strip { width: auto; min-width: 140px; flex: 1; }

  /* ── Points medallion ── */
  .pts-mini {
    flex: none; width: 20px; height: 20px; font-size: 10px;
    display: grid; place-items: center; border-radius: 4px;
    background: #0c0d12; color: #fff;
  }

  /* ── Bottom group (v) ── */
  .bottom-group { display: flex; flex-direction: column; gap: 8px; margin-top: auto; flex-shrink: 0; }

  /* ── Info col (h) ── */
  .info-col { width: 188px; flex: none; display: flex; flex-direction: column; gap: 8px; }

  /* ── Pass btn ── */
  .pass-btn {
    background: transparent; color: rgba(255,255,255,.5);
    border: 1px solid rgba(255,255,255,.15); border-radius: 5px;
    padding: 4px 12px; cursor: pointer; font-size: .8rem;
    align-self: flex-start;
  }
  .pass-btn:hover { background: rgba(255,255,255,.08); color: white; }

  /* ── Hover card popup ── */
  .hover-popup {
    position: fixed; z-index: 1000; pointer-events: none;
    filter: drop-shadow(0 4px 12px rgba(0,0,0,.7));
    transform: scale(2);
    transform-origin: bottom center;
  }
  .hover-popup.below {
    transform-origin: top center;
  }
</style>
