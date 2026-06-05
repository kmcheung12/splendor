<script lang="ts">
  import type { PokemonCard } from '../lib/types'
  import { fly } from 'svelte/transition'
  import { cubicOut } from 'svelte/easing'
  import { createEventDispatcher } from 'svelte'
  import CardSlot from './CardSlot.svelte'

  export let cards: PokemonCard[]
  export let flyX = 0
  export let flyY = 0
  export let evolveActions: number[] = []

  const dispatch = createEventDispatcher<{ evolve: number }>()

  // Clip back cards to show tier bar + strip only (hide art + cost).
  // tier bar ~4px + strip ~42px (half of available after cost) + borders ~2px = ~48px.
  const STRIP_H = 48

  function canEvolve(origIdx: number): boolean {
    return evolveActions.includes(77 + origIdx)
  }

  function debugHover(e: MouseEvent, i: number, stackLen: number) {
    const item = e.currentTarget as HTMLElement
    const card = item.querySelector('.card') as HTMLElement | null
    const cs = getComputedStyle(item)
    const parent = item.parentElement!
    const pcs = getComputedStyle(parent)
    console.group(`[CardStack] hover i=${i}/${stackLen - 1} (${i < stackLen - 1 ? 'back' : 'top'})`)
    console.log('stack-item computed:', {
      position: cs.position, zIndex: cs.zIndex, overflow: cs.overflow,
      height: cs.height, transform: cs.transform,
    })
    console.log('.stack computed:', {
      position: pcs.position, zIndex: pcs.zIndex, overflow: pcs.overflow,
    })
    if (card) {
      const ccs = getComputedStyle(card)
      console.log('.card computed:', {
        position: ccs.position, zIndex: ccs.zIndex, transform: ccs.transform, overflow: ccs.overflow,
      })
      // Sample elementsFromPoint at card centre after a tick (transform takes a frame)
      const rect = card.getBoundingClientRect()
      const cx = rect.left + rect.width / 2
      const cy = rect.top + rect.height / 2
      setTimeout(() => {
        const els = document.elementsFromPoint(cx, cy)
        console.log('elementsFromPoint at card centre (after 200ms):', els.map(el => `${el.tagName}${el.id ? '#'+el.id : ''}${el.className ? '.'+[...el.classList].join('.') : ''}`))
      }, 200)
    }
    console.groupEnd()
  }

  $: groups = (() => {
    const map: Record<string, { card: PokemonCard; origIdx: number }[]> = {}
    for (let i = 0; i < cards.length; i++) {
      const c = cards[i]
      const key = c.bonus[0] ?? 'none'
      ;(map[key] ??= []).push({ card: c, origIdx: i })
    }
    return Object.entries(map)
  })()
</script>

<div class="card-stacks">
  {#each groups as [, stack]}
    <div class="stack">
      {#each stack as { card, origIdx }, i (origIdx)}
        <div
          class="stack-item"
          class:back={i < stack.length - 1}
          in:fly={{ x: flyX, y: flyY, duration: 440, easing: cubicOut }}
          on:mouseenter={(e) => debugHover(e, i, stack.length)}
        >
          <CardSlot
            {card}
            tier={card.tier}
            highlight={canEvolve(origIdx)}
            dimmed={card.evolved}

            on:click={() => canEvolve(origIdx) && dispatch('evolve', origIdx)}
          />
        </div>
      {/each}
    </div>
  {/each}
</div>

<style>
  .card-stacks { display: flex; gap: 8px; flex-wrap: wrap; }

  .stack { display: flex; flex-direction: column; gap: 3px; }

  .stack-item { position: relative; z-index: 0; }
  .stack-item:has(:global(.card:hover)) { z-index: 300; }
  .stack-item.back {
    height: 48px;
    overflow: hidden;
    flex-shrink: 0;
  }
  .stack-item.back:has(:global(.card:hover)) { overflow: visible; }
</style>
