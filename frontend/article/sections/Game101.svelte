<section class="game101">
  <div class="prose">
    <h2>Splendor in 90 seconds</h2>
    <p>
      Players take turns. Each turn you do one of three things: grab
      tokens, reserve a card for later, or buy a card you can afford.
      Cards give you points and bonuses that make future cards cheaper.
      The first player to fifteen points wins the round.
    </p>
    <p class="aside">
      This article is about a variant called Pokémon Splendor — same rules,
      but with Pokémon cards and a tier system that rewards building
      evolution chains.
    </p>
  </div>
  <!-- Mini board mockup placeholder. Replaced in Plan 4 with GameReplayPlayer. -->
  <aside class="board-placeholder">
    <span>Mini board renders here in Plan 4</span>
  </aside>
</section>

<style>
  .game101 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4rem;
    padding: 8rem 4rem;
    max-width: 90rem;
    margin: 0 auto;
    align-items: center;
  }
  .prose h2 {
    font-size: clamp(2rem, 4vw, 3rem);
    margin: 0 0 1.5rem;
    letter-spacing: -0.02em;
  }
  .prose p { font-size: 1.15rem; color: #d6d3cb; }
  .aside { color: var(--muted); font-size: 1rem; }
  .board-placeholder {
    aspect-ratio: 1;
    border: 1px dashed rgba(255,255,255,0.1);
    display: grid;
    place-items: center;
    color: var(--muted);
    font-size: 0.9rem;
  }
  @media (max-width: 800px) {
    .game101 { grid-template-columns: 1fr; }
  }
</style>
