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
