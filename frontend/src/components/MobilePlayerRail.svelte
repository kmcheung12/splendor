<!-- frontend/src/components/MobilePlayerRail.svelte -->
<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import { isMyTurn, phase, activePlayer, lastActions } from '../lib/gameStore'
  import { BALL } from '../lib/tokens'
  import type { PlayerState } from '../lib/types'
  import ReservedCard from './ReservedCard.svelte'

  export let player: PlayerState
  export let displayName: string
  export let isOwnPlayer: boolean

  const dispatch = createEventDispatcher<{ expand: void }>()

  import { COL, CARDBG, TIER_BAR, LANE_ORDER } from '../lib/gameData'

  $: bonuses = LANE_ORDER.reduce<Record<string, number>>((acc, c) => {
    acc[c] = player.cards.reduce((n, card) => card.evolved ? n : n + card.bonus.filter(b => b === c).length, 0)
    return acc
  }, {})

  $: isActive = $activePlayer === player.name
  $: avatarNum = (player.name.match(/\d+/) ?? ['?'])[0]
  $: needsAction = isOwnPlayer && $isMyTurn && isActive &&
    ($phase === 'discard' || $phase === 'evolve')
  $: lastAction = $lastActions[player.name] ?? ''
</script>

<button class="railbtn" on:click={() => dispatch('expand')}>
  <div class="prail" class:active={isActive}>
    <div class="prail-head">
      <div class="avatar" class:avatar-on={isActive}>{avatarNum}</div>
      <div class="meta">
        <span class="pname">{displayName}{#if isActive}<em class="turn">● TURN</em>{/if}</span>
        {#if lastAction}<span class="plast">{lastAction}</span>{/if}
      </div>
      <div class="lcd">{player.points}</div>
    </div>

    <div class="field-label">Bonus <span class="fl">/</span> Pokéball</div>
    <div class="cstacks">
      {#each LANE_ORDER as c}
        {@const bn = bonuses[c] ?? 0}
        {@const tn = player.tokens[c] ?? 0}
        <div class="cstack">
          <div class="cs-card" class:csz={bn === 0} style="background:{CARDBG[c]}">
            <span class="cs-bar" style="background:{COL[c]}"></span>
            <span class="cs-bn">{bn}</span>
          </div>
          <div class="cs-gem" class:csz={tn === 0} style="--gc:{COL[c]}">
            <span class="cs-n">{tn}</span>
            <img class="cs-mb" src={BALL[c]} alt={c} width="9" height="9" draggable="false">
          </div>
        </div>
      {/each}
      <!-- Master (wild) — always shown, no bonus card -->
      {#each [player.tokens['master'] ?? 0] as masterN}
      <div class="cstack">
        <div class="cs-card wild" style="background:#3a2f0e">
          <span class="cs-bar" style="background:{COL.master}"></span>
          <span class="cs-star">✦</span>
        </div>
        <div class="cs-gem" class:csz={masterN === 0} style="--gc:{COL.master}">
          <span class="cs-n">{masterN}</span>
          <img class="cs-mb" src={BALL['master']} alt="master" width="9" height="9" draggable="false">
        </div>
      </div>
      {/each}
    </div>

    {#if player.reserved_cards.length > 0}
      <div class="field-label">Reserved</div>
      <div class="rmini">
        {#each player.reserved_cards as card}
          <ReservedCard {card} size="sm" />
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
    flex: 1; min-height: 0; padding: 6px;
    background: linear-gradient(180deg, #23252e, #16171d);
    border: 2px solid #0c0d12; border-radius: 8px;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.05), 3px 3px 0 rgba(0,0,0,.35);
    overflow: hidden; display: flex; flex-direction: column; gap: 4px;
    transition: transform .12s ease, filter .12s ease;
  }
  .railbtn:hover .prail { filter: brightness(1.12); }
  .railbtn:active .prail { transform: scale(.985); }
  .prail.active {
    box-shadow: inset 0 0 0 2px rgba(255,210,63,.5), 0 0 0 2px rgba(255,210,63,.5), 3px 3px 0 rgba(0,0,0,.35);
  }
  .prail-head { display: flex; align-items: center; gap: 5px; }

  .avatar {
    width: 22px; height: 22px; flex: none; border-radius: 4px;
    display: grid; place-items: center;
    font-family: 'Press Start 2P', monospace; font-size: 9px;
    color: #0c0d12; background: #6b7280;
    box-shadow: 2px 2px 0 rgba(0,0,0,.4);
  }
  .avatar.avatar-on { background: #ffd23f; }
  .lcd {
    flex: none; min-width: 24px; height: 24px; padding: 0 3px;
    display: grid; place-items: center; border-radius: 4px;
    font-family: 'Press Start 2P', monospace; font-size: 11px; color: #fff;
    background: #0c0d12; box-shadow: inset 0 0 0 2px #ffd23f, 2px 2px 0 rgba(0,0,0,.4);
  }
  .meta { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
  .pname { font-family: 'Silkscreen', monospace; font-size: 9px; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  em.turn { color: #ffd23f; font-style: normal; font-size: 6px; margin-left: 3px; }
  .plast { font-size: 7px; color: rgba(255,255,255,.45); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .field-label { font-family: 'Silkscreen', monospace; font-size: 6px; letter-spacing: .7px; text-transform: uppercase; color: rgba(255,255,255,.5); }
  .fl { color: rgba(255,255,255,.28); margin: 0 1px; }

  /* ── Color stacks: card (bonus) over gem (pokéball) ── */
  .cstacks { display: flex; gap: 2px; align-items: flex-end; }
  .cstack { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: 3px; }

  .cs-card {
    position: relative; width: 100%; aspect-ratio: 1;
    border-radius: 2px; display: grid; place-items: center; overflow: hidden;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.14), 1px 1px 0 rgba(0,0,0,.45);
  }
  .cs-bar { position: absolute; top: 0; left: 0; right: 0; height: 2px; }
  .cs-bn { font-family: 'Press Start 2P', monospace; font-size: 8px; color: #fff; text-shadow: 1px 1px 0 rgba(0,0,0,.65); }
  .cs-card.csz { opacity: .26; }
  .cs-card.wild { display: grid; place-items: center; }
  .cs-star { font-size: 9px; color: #f4d23a; text-shadow: 1px 1px 0 rgba(0,0,0,.6); }

  .cs-gem {
    position: relative; width: 100%; aspect-ratio: 1; border-radius: 50%;
    background: #0c0d12; display: grid; place-items: center;
    box-shadow: inset 0 0 0 2px var(--gc, #555), 1px 1px 0 rgba(0,0,0,.45);
  }
  .cs-n { font-family: 'Press Start 2P', monospace; font-size: 8px; color: #fff; text-shadow: 1px 1px 0 rgba(0,0,0,.6); }
  .cs-mb { position: absolute; right: -2px; bottom: -2px; image-rendering: pixelated; display: block; }
  .cs-gem.csz { opacity: .24; }

  /* ── Reserved ── */
  .rmini { display: flex; flex-direction: column; gap: 3px; }

  .expand-cue {
    position: absolute; top: 5px; right: 6px;
    font-size: 11px; color: rgba(255,255,255,.45); pointer-events: none; line-height: 1;
  }
  .railbtn:hover .expand-cue { color: #ffd23f; }

  .action-badge {
    position: absolute; top: 4px; left: 4px;
    width: 14px; height: 14px; border-radius: 50%;
    background: #e74c3c; color: #fff;
    font-family: 'Press Start 2P', monospace; font-size: 7px;
    display: grid; place-items: center; pointer-events: none;
    animation: badge-pulse 1s ease-in-out infinite;
  }
  @keyframes badge-pulse {
    0%,100% { box-shadow: 0 0 0px rgba(231,76,60,0); }
    50%      { box-shadow: 0 0 6px rgba(231,76,60,.8); }
  }
</style>
