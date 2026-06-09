<!-- frontend/src/components/ReservedCard.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import { BALL } from '../lib/tokens'
  import type { PokemonCard } from '../lib/types'

  export let card: PokemonCard
  export let size: 'sm' | 'lg' = 'sm'
  export let catchable = false

  const dispatch = createEventDispatcher<{ click: void }>()

  const COL: Record<string, string> = {
    red: '#ff3434', yellow: '#f1c40f', blue: '#3498db',
    pink: '#ffa3da', black: '#9aa0a6', master: '#a569bd',
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

  const GEM_ORDER = ['red', 'yellow', 'blue', 'pink', 'black', 'master']
  function groupCost(gems: string[]): { c: string; n: number }[] {
    const counts: Record<string, number> = {}
    for (const g of gems) counts[g] = (counts[g] ?? 0) + 1
    return GEM_ORDER.filter(c => counts[c]).map(c => ({ c, n: counts[c] }))
  }

  $: lg = size === 'lg'
  $: color = card.bonus[0] ?? 'black'
  $: groupedCost = groupCost(card.cost)
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
  class="rm"
  class:lg
  class:catchable
  on:click={() => dispatch('click')}
>
  <span class="rm-bar" style="background:{COL[color] ?? '#888'}"></span>
  {#if lg}
    <img src={spriteUrl(card.name)} alt={card.name} width="18" height="18" draggable="false">
  {/if}
  <span class="rm-name">{card.name}</span>
  {#if groupedCost.length}
    <span class="rm-cost">
      {#each groupedCost as g}
        <span class="rm-cv" style="--gc:{COL[g.c]}">
          <span class="rm-cv-n">{g.n}</span>
          <img class="rm-cv-mb" src={BALL[g.c]} alt={g.c} draggable="false">
        </span>
      {/each}
    </span>
  {/if}
  <span class="rm-pts">{card.point}</span>
  {#if catchable}<span class="catch-tag">Catch</span>{/if}
</div>

<style>
  .rm {
    display: flex; align-items: center; gap: 3px;
    background: rgba(255,255,255,.06); border-radius: 4px;
    padding: 2px 4px 2px 0; overflow: hidden; cursor: default;
  }
  .rm.lg {
    gap: 4px; padding: 4px 7px 4px 0;
  }
  .rm.catchable { cursor: pointer; outline: 1.5px solid #ffd23f; animation: catch-pulse 1s ease-in-out infinite; }
  @keyframes catch-pulse {
    0%,100% { filter: drop-shadow(0 0 0px rgba(255,210,63,0)); }
    50%     { filter: drop-shadow(0 0 5px rgba(255,210,63,.8)); }
  }
  .rm img { image-rendering: pixelated; display: block; }

  .rm-bar { width: 2px; align-self: stretch; flex: none; }
  .rm-name {
    font-family: 'Silkscreen', monospace; font-size: 7px; color: #fff;
    flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .rm.lg .rm-name { font-size: 9px; }
  .rm-pts {
    font-family: 'Press Start 2P', monospace; font-size: 7px; color: #fff;
    background: #0c0d12; border-radius: 3px; padding: 2px 3px; flex: none;
  }
  .rm.lg .rm-pts { font-size: 8px; }
  .catch-tag {
    font-family: 'Silkscreen', monospace; font-size: 7px;
    background: #27ae60; color: #fff; border-radius: 3px; padding: 1px 4px; flex: none;
  }

  /* Cost tokens */
  .rm-cost { display: flex; gap: 2px; align-items: center; flex: none; }
  .rm-cv {
    position: relative; width: 12px; height: 12px; border-radius: 50%; flex: none;
    background: #0c0d12; display: grid; place-items: center;
    box-shadow: inset 0 0 0 1.5px var(--gc, #555);
  }
  .rm.lg .rm-cv { width: 14px; height: 14px; }
  .rm-cv-n { font-family: 'Press Start 2P', monospace; font-size: 5px; color: #fff; }
  .rm.lg .rm-cv-n { font-size: 6px; }
  .rm-cv-mb { position: absolute; right: -2px; bottom: -2px; width: 6px; height: 6px; image-rendering: pixelated; display: block; }
  .rm.lg .rm-cv-mb { width: 7px; height: 7px; }
</style>
