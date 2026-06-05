<script lang="ts">
  import { stagedTokens, tokenSelectMode, humanTurnActions, activePlayer } from '../lib/gameStore'
  import { sendAction } from '../lib/ws'
  import { BALL } from '../lib/tokens'
  import { flyArc, ARC_DURATION } from '../lib/arcAnimation'

  const TAKE_DIFF_COMBOS: string[][] = [
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

  function findValidAction(staged: string[]): number | null {
    if (staged.length === 0) return null
    if (staged.length === 2 && staged[0] === staged[1]) {
      const idx = TAKE_SAME_TYPES.indexOf(staged[0])
      if (idx < 0) return null
      const actionId = 25 + idx
      return $humanTurnActions.includes(actionId) ? actionId : null
    }
    const sorted = [...staged].sort()
    const hasDups = new Set(sorted).size < sorted.length
    if (hasDups) return null
    const idx = TAKE_DIFF_COMBOS.findIndex(c => {
      const cs = [...c].sort()
      return cs.length === sorted.length && cs.every((v, i) => v === sorted[i])
    })
    if (idx < 0) return null
    return $humanTurnActions.includes(idx) ? idx : null
  }

  $: validAction = findValidAction($stagedTokens)

  $: statusMsg = (() => {
    const n = $stagedTokens.length
    if (n === 0) return 'Click a token to start'
    const types = [...new Set($stagedTokens)]
    const hasDups = n > types.length
    if (hasDups && n === 2) return validAction !== null ? '✓ Take 2 of same' : 'Need 4+ on board'
    if (hasDups) return 'Can\'t mix same + different'
    if (n === 1) return 'Add 1 more (same or diff)'
    if (n === 2) return validAction !== null ? '✓ Take 2 different' : 'Invalid combo'
    if (n === 3) return validAction !== null ? '✓ Take 3 different' : 'Must all differ'
    return 'Too many'
  })()

  function returnToken(idx: number, e: MouseEvent) {
    const t = $stagedTokens[idx]
    const isLast = $stagedTokens.length === 1
    const fromRect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    const poolBtn = document.querySelector<HTMLElement>(`[data-token-type="${t}"]`)

    // Remove token immediately — staging stays visible (tokenSelectMode still true)
    // so the pool button remains in its shifted position during the flight.
    stagedTokens.update(s => s.filter((_, i) => i !== idx))

    if (poolBtn) {
      // Pool button is still in shifted position; capture rect now before any re-render.
      const toRect = poolBtn.getBoundingClientRect()
      flyArc(fromRect, toRect, BALL[t])
    }

    if (isLast) {
      // Hide staging only after the ball lands so the pool doesn't re-center mid-flight.
      setTimeout(() => tokenSelectMode.set(false), ARC_DURATION)
    }
  }

  function cancel() {
    stagedTokens.set([])
    tokenSelectMode.set(false)
  }

  function confirm() {
    if (validAction === null) return
    const slots = Array.from(document.querySelectorAll<HTMLElement>('.slot-filled'))
    const panelEl = document.querySelector<HTMLElement>(`[data-player-name="${$activePlayer}"]`)
    if (panelEl) {
      const toRect = panelEl.getBoundingClientRect()
      $stagedTokens.forEach((t, i) => {
        const slot = slots[i]
        if (slot) flyArc(slot.getBoundingClientRect(), toRect, BALL[t], ARC_DURATION, i * 80)
      })
    }
    sendAction(validAction)
    stagedTokens.set([])
    tokenSelectMode.set(false)
  }
</script>

<div class="staging-row">
  <div class="staging-left">
    <div class="slot-group">
      {#each [0, 1, 2] as i}
        {#if $stagedTokens[i]}
          <button class="slot-filled" title="Return {$stagedTokens[i]}" on:click={(e) => returnToken(i, e)}>
            <img src={BALL[$stagedTokens[i]]} alt={$stagedTokens[i]} width="28" height="28" draggable="false">
          </button>
        {:else}
          <div class="slot-empty"></div>
        {/if}
      {/each}
    </div>
    <div class="status" class:valid={validAction !== null}>{statusMsg}</div>
  </div>

  <div class="act-group">
    <button class="cancel-btn" on:click={cancel}>↩</button>
    <button class="confirm-btn" disabled={validAction === null} on:click={confirm}>✓ Take</button>
  </div>
</div>

<style>
  .staging-row {
    display: flex; align-items: center; gap: 12px;
    width: 100%; padding: 0 4px; box-sizing: border-box;
  }

  .staging-left { display: flex; flex-direction: column; gap: 4px; flex-shrink: 0; }

  /* 3 fixed-width token slots */
  .slot-group { display: flex; gap: 6px; }
  .slot-empty {
    width: 40px; height: 40px; border-radius: 8px;
    border: 1.5px dashed rgba(255,255,255,.18);
    background: rgba(255,255,255,.03);
  }
  .slot-filled {
    width: 40px; height: 40px; border-radius: 8px;
    background: rgba(255,255,255,.1); border: 1.5px solid rgba(255,255,255,.25);
    display: grid; place-items: center; cursor: pointer; padding: 0;
    transition: filter .1s, transform .1s;
  }
  .slot-filled img { image-rendering: pixelated; display: block; }
  .slot-filled:hover { filter: brightness(1.3) drop-shadow(0 0 4px rgba(255,255,255,.4)); transform: scale(1.1); }

  /* Status */
  .status { font-size: .75rem; color: rgba(255,255,255,.45); white-space: nowrap; }
  .status.valid { color: #2ecc71; }

  /* Buttons */
  .act-group { display: flex; gap: 6px; flex-shrink: 0; }
  .cancel-btn {
    background: transparent; color: rgba(255,255,255,.55);
    border: 1px solid rgba(255,255,255,.15); border-radius: 5px;
    padding: 5px 10px; cursor: pointer; font-size: .82rem;
  }
  .cancel-btn:hover { background: rgba(255,255,255,.08); color: #fff; }
  .confirm-btn {
    background: #27ae60; color: #fff; border: none;
    border-radius: 5px; padding: 5px 14px;
    cursor: pointer; font-size: .82rem; font-weight: bold;
  }
  .confirm-btn:disabled { opacity: .3; cursor: not-allowed; }
  .confirm-btn:not(:disabled):hover { background: #2ecc71; }
</style>
