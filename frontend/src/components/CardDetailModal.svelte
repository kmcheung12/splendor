<!-- frontend/src/components/CardDetailModal.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import { BALL } from '../lib/tokens'
  import type { PokemonCard } from '../lib/types'

  export let card: PokemonCard
  export let tier: string
  export let actions: { id: number; label: string }[] = []

  const dispatch = createEventDispatcher<{ close: void; action: number }>()

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

  $: color = card.bonus[0] ?? 'black'
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="backdrop" on:click={() => dispatch('close')}>
  <div class="container" on:click|stopPropagation>
    <div class="card" style="background:{CARDBG[color] ?? '#2a2a2a'}">
      <div class="card-bar" style="background:{TIER_BAR[tier] ?? '#888'}"></div>
      <div class="card-head">
        <div class="card-names">
          <span class="card-name">{card.name}</span>
          {#if card.evolve_into}<span class="card-evo">▸ {card.evolve_into}</span>{/if}
        </div>
        <span class="card-bonus" style="background:radial-gradient({COL[color] ?? '#888'}44 0%,transparent 70%)">
          <img src={BALL[color]} alt={color} width="26" height="26" draggable="false">
        </span>
      </div>
      <div class="card-art">
        <img src={spriteUrl(card.name)} alt={card.name} width="76" height="76" draggable="false">
      </div>
      {#if card.cost.length}
        <div class="card-cost">
          {#each card.cost as gem}<img src={BALL[gem]} alt={gem} width="16" height="16" draggable="false">{/each}
        </div>
      {/if}
      <div class="card-pts" style="box-shadow:inset 0 0 0 2px {COL[color] ?? '#888'}">{card.point}</div>
    </div>

    <div class="btns">
      {#each actions as { id, label }}
        <button class="action-btn" on:click={() => dispatch('action', id)}>{label}</button>
      {/each}
      <button class="close-btn" on:click={() => dispatch('close')}>Close</button>
    </div>
  </div>
</div>

<style>
  .backdrop {
    position: absolute; inset: 0;
    background: rgba(5,5,12,.72);
    display: grid; place-items: center; z-index: 60;
    animation: fade .14s ease;
  }
  @keyframes fade { from { opacity: 0; } to { opacity: 1; } }

  .container {
    display: flex; flex-direction: column; align-items: center; gap: 10px;
    animation: pop .2s cubic-bezier(.34,1.4,.64,1);
  }
  @keyframes pop {
    from { opacity: 0; transform: scale(.88) translateY(8px); }
    to   { opacity: 1; transform: scale(1) translateY(0); }
  }

  .card {
    width: 200px; height: 160px; position: relative; color: #fff;
    border: 3px solid #0c0d12; border-radius: 6px; overflow: hidden;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.12), 4px 4px 0 rgba(0,0,0,.5);
    display: flex; flex-direction: column;
  }
  .card img { image-rendering: pixelated; display: block; }
  .card-bar { height: 5px; flex: none; }
  .card-head { display: flex; justify-content: space-between; align-items: flex-start; padding: 5px 6px 0; gap: 4px; }
  .card-names { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .card-name { font-family: 'Silkscreen', monospace; font-weight: 700; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .card-evo  { font-family: 'Silkscreen', monospace; font-size: 8px; color: rgba(255,255,255,.6); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .card-bonus { flex: none; width: 32px; height: 32px; border-radius: 16px; display: grid; place-items: center; }
  .card-art { flex: 1; display: grid; place-items: center; min-height: 0; }
  .card-cost { display: flex; flex-wrap: wrap; gap: 2px; padding: 0 40px 4px 6px; align-content: flex-end; }
  .card-pts {
    position: absolute; right: 5px; bottom: 5px;
    width: 26px; height: 26px; display: grid; place-items: center;
    border-radius: 4px; background: #0c0d12;
    font-family: 'Press Start 2P', monospace; font-size: 11px; color: #fff;
  }

  .btns { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
  .action-btn {
    background: #27ae60; color: #fff; border: none; border-radius: 6px;
    font-family: 'Silkscreen', monospace; font-size: 10px;
    padding: 8px 18px; cursor: pointer;
  }
  .action-btn:hover { filter: brightness(1.15); }
  .close-btn {
    background: rgba(255,255,255,.1); color: rgba(255,255,255,.7);
    border: 1px solid rgba(255,255,255,.2); border-radius: 6px;
    font-family: 'Silkscreen', monospace; font-size: 10px;
    padding: 8px 18px; cursor: pointer;
  }
  .close-btn:hover { background: rgba(255,255,255,.18); color: #fff; }
</style>
