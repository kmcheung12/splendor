<!-- frontend/article/replay/GameReplayPlayer.svelte -->
<script lang="ts">
  import type { BoardSnapshot } from './snapshot';

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
              <div class="name">{card.name}</div>
              <div class="meta">
                <span>+{card.point}</span>
                <span>{card.bonus ?? ''}</span>
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
    font-size: 0.7rem;
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
  .name { font-weight: 600; }
  .meta { display: flex; justify-content: space-between; color: rgba(255,255,255,0.7); }
  .caption {
    margin: 0; color: var(--muted); font-size: 0.85rem;
  }
</style>
