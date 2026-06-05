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
              disabled={!discardable}
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
