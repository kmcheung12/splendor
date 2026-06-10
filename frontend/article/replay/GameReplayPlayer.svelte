<!-- frontend/article/replay/GameReplayPlayer.svelte -->
<script lang="ts">
  import type { BoardSnapshot } from './snapshot';
  import { spriteUrl } from './sprite';

  export let snapshot: BoardSnapshot;
  export let description: string = '';

  const TIER_ORDER: (keyof BoardSnapshot)[] = [
    'legendary_revealed', 'epic_revealed', 'rare_revealed',
    'uncommon_revealed', 'common_revealed',
  ];
</script>

<div class="board">
  <div class="tokens">
    {#each Object.entries(snapshot.tokens) as [color, count]}
      <span class="token" data-color={color}>{count}× {color}</span>
    {/each}
  </div>
  <div class="grid">
    {#each TIER_ORDER as tier}
      <div class="row">
        {#each (snapshot[tier] as any[]) as card}
          {#if card}
            <div class="card" data-tier={card.tier}>
              {#if spriteUrl(card.name)}
                <img
                  class="art"
                  src={spriteUrl(card.name)}
                  alt={card.name}
                  loading="lazy"
                  decoding="async" />
              {/if}
              <div class="name">{card.name}</div>
              <div class="meta">
                <span>+{card.point}</span>
                <span class="bonus" data-bonus={card.bonus ?? ''}>{card.bonus ?? ''}</span>
              </div>
            </div>
          {:else}
            <div class="card empty"></div>
          {/if}
        {/each}
      </div>
    {/each}
  </div>
  {#if description}
    <p class="caption">{description}</p>
  {/if}
</div>

<style>
  .board {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    font-size: 0.85rem;
  }
  .tokens {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.5rem;
    background: rgba(255,255,255,0.03);
    border-radius: 6px;
  }
  .grid {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  .row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.25rem;
  }
  .card {
    aspect-ratio: 2/3;
    background: rgba(255,255,255,0.04);
    border-radius: 6px;
    padding: 0.4rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    font-size: 0.65rem;
    position: relative;
    overflow: hidden;
  }
  .card.empty {
    background: rgba(255,255,255,0.015);
    border: 1px dashed rgba(255,255,255,0.05);
  }
  .card[data-tier="legendary"] { background: linear-gradient(135deg, #6e4cff, #ff3d8a); }
  .card[data-tier="epic"] { background: rgba(110,76,255,0.4); }
  .card[data-tier="rare"] { background: rgba(255,196,77,0.3); }
  .card[data-tier="uncommon"] { background: rgba(220,220,220,0.2); }
  .card[data-tier="common"] { background: rgba(170,120,80,0.25); }
  .art {
    width: 100%;
    flex: 1;
    object-fit: contain;
    image-rendering: pixelated;
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5));
    min-height: 0;
  }
  .name { font-weight: 600; line-height: 1.1; }
  .meta { display: flex; justify-content: space-between; color: rgba(255,255,255,0.85); }
  .bonus[data-bonus="red"] { color: #ff7676; }
  .bonus[data-bonus="yellow"] { color: #ffd45a; }
  .bonus[data-bonus="blue"] { color: #66b7ff; }
  .bonus[data-bonus="pink"] { color: #ff9bd9; }
  .bonus[data-bonus="black"] { color: #c0c0c0; }
  .caption {
    margin: 0; color: var(--muted); font-size: 0.85rem;
  }
</style>
