<!-- frontend/src/components/TutorialOverlay.svelte -->
<script lang="ts">
  import { onDestroy } from 'svelte'
  import { activeTutorialItem, dismissActive } from '../lib/tutorialStore'
  import { gameState, mySlot } from '../lib/gameStore'
  import { resolveSelector, type SelectorMap } from '../lib/tutorial'

  export let selectorMap: SelectorMap

  $: playerName = $gameState?.players[$mySlot ?? -1]?.name ?? ''

  let highlighted: Element[] = []

  function applyHighlights(targets: string[]): void {
    clearHighlights()
    for (const targetId of targets) {
      const fn = selectorMap[targetId]
      if (!fn) continue
      const selectors = resolveSelector(fn, playerName)
      for (const sel of selectors.split(',').map(s => s.trim())) {
        document.querySelectorAll(sel).forEach(el => {
          el.classList.add('tutorial-highlight')
          highlighted.push(el)
        })
      }
    }
  }

  function clearHighlights(): void {
    highlighted.forEach(el => el.classList.remove('tutorial-highlight'))
    highlighted = []
  }

  $: if ($activeTutorialItem) {
    applyHighlights($activeTutorialItem.targets)
  } else {
    clearHighlights()
  }

  onDestroy(clearHighlights)
</script>

{#if $activeTutorialItem}
  <!-- Dim overlay — pointer-events: none so game elements remain interactive -->
  <div class="tutorial-dim"></div>

  <!-- Modal — anchored bottom-centre of viewport -->
  <div class="tutorial-modal" role="dialog" aria-modal="true" aria-labelledby="tut-title">
    <p class="tut-title" id="tut-title">{$activeTutorialItem.title}</p>
    <p class="tut-body">{$activeTutorialItem.body}</p>
    <button class="tut-dismiss" on:click={dismissActive}>Got it</button>
  </div>
{/if}

<style>
  /* ── Dim overlay ── */
  .tutorial-dim {
    position: fixed; inset: 0;
    background: rgba(0, 0, 0, 0.65);
    z-index: 1000;
    pointer-events: none;
  }

  /* ── Modal ── */
  .tutorial-modal {
    position: fixed;
    bottom: 36px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1020;
    background: #1a1a2e;
    border: 1.5px solid rgba(255, 210, 63, 0.6);
    border-radius: 10px;
    padding: 18px 22px;
    min-width: 280px;
    max-width: 420px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.8);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .tut-title {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.65rem;
    color: #ffd23f;
    margin: 0;
    line-height: 1.5;
  }

  .tut-body {
    font-family: 'Silkscreen', monospace;
    font-size: 0.78rem;
    color: rgba(255, 255, 255, 0.85);
    margin: 0;
    line-height: 1.6;
  }

  .tut-dismiss {
    background: #ffd23f;
    color: #0c0d12;
    border: none;
    border-radius: 5px;
    padding: 7px 16px;
    cursor: pointer;
    font-family: 'Press Start 2P', monospace;
    font-size: 0.55rem;
    align-self: flex-end;
    letter-spacing: 0.05em;
  }

  .tut-dismiss:hover { background: #ffe066; }

  /*
   * Global class applied via JS to target DOM elements.
   * Elevates target above the dim overlay and adds a gold outline.
   * position:relative is required for z-index to take effect on non-positioned elements.
   */
  :global(.tutorial-highlight) {
    position: relative !important;
    z-index: 1010 !important;
    outline: 2px solid rgba(255, 210, 63, 0.7) !important;
    outline-offset: 3px !important;
    border-radius: 6px !important;
  }
</style>
