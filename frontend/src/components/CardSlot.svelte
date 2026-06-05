<script lang="ts">
  import type { PokemonCard } from '../lib/types'
  import { BALL } from '../lib/tokens'

  export let card: PokemonCard | null
  export let tier: string
  export let highlight = false
  export let dimmed = false
  export let noPop = false

  // our data uses 'master'; design tokens use 'gold'
  const GEM: Record<string, string> = {
    red: 'red', yellow: 'yellow', blue: 'blue',
    pink: 'pink', black: 'black', master: 'gold',
  }

  const GEMS: Record<string, { accent: string; bg: string }> = {
    red:    { accent: '#ff3434', bg: '#6b2a2a' },
    yellow: { accent: '#f1c40f', bg: '#5c5020' },
    blue:   { accent: '#3498db', bg: '#1e3d5c' },
    pink:   { accent: '#ffa3da', bg: '#a04f78' },
    black:  { accent: '#9aa0a6', bg: '#2a2a2a' },
    gold:   { accent: '#f39c12', bg: '#6e5212' },
  }

  const TIER_BAR: Record<string, string> = {
    common:    '#b08d57',
    uncommon:  '#c7ccd1',
    rare:      '#e8b923',
    epic:      '#a55fd0',
    legendary: 'linear-gradient(90deg,#3aa0e0,#f0852e)',
  }

  const TIER_BG: Record<string, string> = {
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
    return id
      ? `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${id}.png`
      : ''
  }

  function accentHalo(hex: string): string {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `radial-gradient(ellipse at center, rgba(${r},${g},${b},.45) 0%, transparent 70%)`
  }

  $: bonusGem = GEM[card?.bonus[0] ?? ''] ?? 'black'
  $: gem = GEMS[bonusGem] ?? GEMS.black
  $: bonusCount = card?.bonus.length ?? 1
  $: ballSize = bonusCount > 1 ? 16 : 20
  $: tierBar = card ? (TIER_BAR[card.tier] ?? '#888') : (TIER_BG[tier] ?? TIER_BG.common)
  $: mainSprite = card ? spriteUrl(card.name) : ''
  $: evoSprite = card?.evolve_into ? spriteUrl(card.evolve_into) : ''
  $: hasEvo = !!(card?.evolve_into)
  $: evoCostGems = card?.evolve.map(g => GEM[g] ?? g) ?? []
  $: bonusBalls = Array.from({ length: bonusCount }, (_, i) => i)
  $: costGroups = (() => {
    if (!card) return [] as { gem: string; count: number }[]
    const counts: Record<string, number> = {}
    for (const g of card.cost) {
      const k = GEM[g] ?? g
      counts[k] = (counts[k] ?? 0) + 1
    }
    return Object.entries(counts)
      .map(([gem, count]) => ({ gem, count }))
      .sort((a, b) => b.count - a.count)
  })()
  $: totalCost = card?.cost.length ?? 0
  $: singleLine = totalCost < 7
  $: maxBallCount = costGroups[0]?.count ?? 1
  $: col1W = singleLine
    ? `${totalCost * 16 + Math.max(0, totalCost - 1) * 2}px`
    : `${maxBallCount * 16 + (maxBallCount - 1) * 2}px`
  let mx = 50, my = 50
  function onMouseMove(e: MouseEvent) {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
    mx = ((e.clientX - r.left) / r.width) * 100
    my = ((e.clientY - r.top) / r.height) * 100
  }
  function onMouseLeave() { mx = 50; my = 50 }

  let jumping = false
  function startJump() {
    if (jumping) return
    jumping = true
    setTimeout(() => { jumping = false }, 480)
  }

  $: cardStyle = card
    ? `--bg:${gem.bg};--accent:${gem.accent};--mx:${mx}%;--my:${my}%;--holo:${mx * 1.8}deg`
    : ''
  $: halo = accentHalo(gem.accent)
  $: accentShadow = `inset 0 0 0 2px ${gem.accent}, 2px 2px 0 rgba(0,0,0,.4)`
</script>

{#if card}
  <button
    class="card"
    class:highlight
    class:dimmed
    class:no-pop={noPop}
    style={cardStyle}
    on:click={startJump}
    on:click
    on:mousemove={onMouseMove}
    on:mouseleave={onMouseLeave}
  >
    <div class="v1-tierbar" style="background:{tierBar}"></div>

    <div class="v1-strip">
      <div class="v1-evobox">
        <div class="v1-name">{card.name}</div>
        {#if hasEvo}
          <div class="v1-evo">
            {#if evoSprite}<img class="sprite" src={evoSprite} alt={card.evolve_into} width="16" height="16">{/if}
            <div class="v1-evo-meta">
              <span class="v1-evo-name">▸ {card.evolve_into}</span>
              <span class="v1-evo-cost">
                {#each evoCostGems as g}
                  <img class="ball" src={BALL[g]} alt={g} width="10" height="10">
                {/each}
              </span>
            </div>
          </div>
        {/if}
      </div>

      <div class="v1-bonus" style="background:{halo}">
        {#each bonusBalls as _}
          <img class="ball" src={BALL[bonusGem]} alt={bonusGem} width={ballSize} height={ballSize}
            style="filter:drop-shadow(1px 2px 0 rgba(0,0,0,.45))">
        {/each}
      </div>
    </div>

    <div class="v1-art">
      <div class="v1-stage" class:jumping>
        {#if mainSprite}<img class="sprite" src={mainSprite} alt={card.name} width="48" height="48">{/if}
        <div class="v1-shadow"></div>
      </div>
    </div>

    <div class="v1-cost" style="grid-template-columns:{col1W} minmax(0px,auto)">
      {#if singleLine}
        <div class="ball-row">
          {#each costGroups as { gem: g, count }}
            {#each Array.from({ length: count }) as _}
              <img class="ball" src={BALL[g]} alt={g} width="16" height="16">
            {/each}
          {/each}
        </div>
        <div></div>
      {:else}
        <div class="ball-groups">
          {#each costGroups.slice(0, 2) as { gem: g, count }}
            <div class="ball-row">
              {#each Array.from({ length: count }) as _}
                <img class="ball" src={BALL[g]} alt={g} width="16" height="16">
              {/each}
            </div>
          {/each}
        </div>
        <div class="ball-groups">
          {#each costGroups.slice(2, 4) as { gem: g, count }}
            <div class="ball-row">
              {#each Array.from({ length: count }) as _}
                <img class="ball" src={BALL[g]} alt={g} width="16" height="16">
              {/each}
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="v1-pts" style="box-shadow:{accentShadow}">{card.point}</div>
  </button>
{:else}
  <div class="card empty" style="background:{TIER_BG[tier] ?? TIER_BG.common}"></div>
{/if}

<style>
  .card {
    width: 158px; height: 130px;
    display: flex; flex-direction: column;
    background: var(--bg, #2a2a2a);
    border: 2px solid #0c0d12; border-radius: 3px; overflow: hidden;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.10), 3px 3px 0 rgba(0,0,0,.42);
    font-family: 'Silkscreen', monospace; color: #fff;
    user-select: none; cursor: pointer;
    text-align: left; padding: 0; box-sizing: border-box;
    position: relative; z-index: 0;
    transform-origin: center;
    transition: transform .18s cubic-bezier(.34,1.56,.64,1), z-index 0s;
  }
  .card:hover {
    transform: scale(2);
    z-index: 200;
    filter: brightness(1.08);
  }
  .card.no-pop:hover {
    transform: none;
    z-index: 0;
    filter: brightness(1.08);
  }
  .card::after {
    content: '';
    position: absolute; inset: 0; border-radius: 3px;
    background:
      radial-gradient(ellipse 65% 55% at var(--mx,50%) var(--my,50%),
        rgba(255,255,255,.11) 0%, transparent 58%),
      linear-gradient(var(--holo,115deg),
        transparent       0%,
        rgba(255, 60, 60,.15) 18%,
        rgba(255,200, 50,.15) 32%,
        rgba( 60,255,120,.15) 46%,
        rgba( 50,160,255,.15) 62%,
        rgba(200, 60,255,.15) 76%,
        transparent       90%
      );
    opacity: 0;
    pointer-events: none;
    transition: opacity .15s;
  }
  .card:hover::after { opacity: 1; }
  .card.highlight { outline: 2px solid #f1c40f; outline-offset: 1px; }
  .card.dimmed { opacity: .45; }
  .card.empty { cursor: default; border-style: dashed; border-color: rgba(255,255,255,.15); box-shadow: none; opacity: .5; }

  .v1-tierbar {
    height: 2px; flex-shrink: 0;
    box-shadow: inset 0 -1px 0 rgba(0,0,0,.4);
  }

  .v1-strip {
    flex: 1; min-height: 0;
    display: flex; align-items: center; justify-content: space-between; gap: 5px;
    padding: 4px 7px;
    background: linear-gradient(180deg, rgba(0,0,0,.32), rgba(0,0,0,.12));
    overflow: hidden;
  }

  .v1-art {
    flex: 1; min-height: 0;
    display: flex; align-items: center; justify-content: center;
    position: relative;
  }

  .v1-stage {
    display: flex; flex-direction: column; align-items: center;
  }

  .v1-shadow {
    width: 36px; height: 5px; margin-top: -2px;
    background: rgba(0,0,0,.4); border-radius: 50%;
    filter: blur(1px);
    transform-origin: center;
  }

  .v1-stage.jumping .sprite {
    animation: poke-jump 480ms cubic-bezier(.23,.54,.46,.77) forwards;
  }
  .v1-stage.jumping .v1-shadow {
    animation: shadow-shrink 480ms cubic-bezier(.23,.54,.46,.77) forwards;
  }

  @keyframes poke-jump {
    0%   { transform: translateY(0px);   }
    50%  { transform: translateY(-22px); animation-timing-function: cubic-bezier(.54,.23,.77,.46); }
    100% { transform: translateY(0px);   }
  }
  @keyframes shadow-shrink {
    0%   { transform: scaleX(1);    opacity: 1;    }
    50%  { transform: scaleX(0.28); opacity: 0.22; animation-timing-function: cubic-bezier(.54,.23,.77,.46); }
    100% { transform: scaleX(1);    opacity: 1;    }
  }

  .v1-evobox {
    display: flex; flex-direction: column; gap: 3px;
    flex: 1; min-width: 0; overflow: hidden;
  }

  .v1-name {
    font-weight: 700; font-size: 9px; letter-spacing: .2px;
    color: #fff; text-shadow: 1px 1px 0 rgba(0,0,0,.5);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }

  .v1-evo {
    display: flex; align-items: center; gap: 4px;
  }

  .v1-evo-meta {
    display: flex; flex-direction: column; gap: 2px;
    min-width: 0; overflow: hidden;
  }

  .v1-evo-name {
    font-weight: 400; font-size: 7px;
    color: rgba(255,255,255,.58); text-shadow: 1px 1px 0 rgba(0,0,0,.45);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }

  .v1-evo-cost { display: flex; gap: 1px; flex-wrap: wrap; }

  .v1-bonus {
    display: inline-flex; align-items: center; gap: 1px;
    padding: 3px 4px; border-radius: 12px; flex-shrink: 0;
  }

  .v1-cost {
    display: grid; /* grid-template-columns set inline per-card */
    align-items: end; gap: 3px;
    padding: 4px 36px 5px 5px; flex-shrink: 0; /* right padding reserves space for abs-positioned pts */
    min-height: 34px; /* at least as tall as pts badge (24px) + top/bottom padding */
    background: rgba(0,0,0,.26);
  }

  .ball-groups { display: flex; flex-direction: column; gap: 2px; overflow: hidden; min-width: 0; }
  .ball-row { display: flex; gap: 2px; flex-wrap: wrap; }

  .v1-pts {
    position: absolute; bottom: 4px; right: 4px;
    font-family: 'Press Start 2P', monospace; font-size: 10px; color: #fff;
    width: 24px; height: 24px; display: grid; place-items: center;
    border-radius: 4px;
    background: #0c0d12;
  }

  .sprite { image-rendering: pixelated; display: block; }
  .ball  { image-rendering: pixelated; display: block; }
</style>
