<section id="rl" class="rl101">
  <div class="prose">
    <h2>How a network learns by playing</h2>
    <p>
      Reinforcement learning is what happens when an agent plays a game,
      tries things, and gets a single number back at the end — did it win?
      The agent uses that single number to nudge every decision it made
      slightly more toward the kind of decision that wins.
    </p>

    <div class="concept-grid">
      <div class="concept">
        <h3>Observation</h3>
        <p>What the agent sees. For us: a vector of every card on the
          board, every token in every pile, and every player's hand.</p>
      </div>
      <div class="concept">
        <h3>Action</h3>
        <p>What the agent does. One of fifty possible moves: take tokens,
          reserve a card, catch a card.</p>
      </div>
      <div class="concept">
        <h3>Reward</h3>
        <p>The signal it learns from. We give +1 for winning the game and
          0 for everything else. That's it.</p>
      </div>
      <div class="concept">
        <h3>Policy</h3>
        <p>The agent's strategy — a function from observation to a
          probability over each action.</p>
      </div>
      <div class="concept">
        <h3>Value</h3>
        <p>The agent's gut feel — a single number that estimates "from
          this position, how likely am I to win?"</p>
      </div>
    </div>

    <p>
      Every action the agent took during a winning game becomes a tiny
      vote toward doing that action again. Every action during a losing
      game becomes a tiny vote against. Repeated a million times, the
      votes accumulate into a strategy.
    </p>
  </div>
</section>

<style>
  .rl101 {
    padding: 8rem 1.5rem;
  }
  .prose {
    max-width: 60rem;
    margin: 0 auto;
  }
  h2 {
    font-size: clamp(2rem, 4vw, 3rem);
    margin-bottom: 2rem;
    letter-spacing: -0.02em;
  }
  p {
    font-size: 1.15rem;
    color: #d6d3cb;
    margin: 0 0 1.5rem;
  }
  .concept-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
    gap: 1.5rem;
    margin: 3rem 0;
  }
  .concept {
    padding: 1.5rem;
    border-left: 2px solid var(--accent);
    background: rgba(255,255,255,0.02);
  }
  .concept h3 {
    margin: 0 0 0.75rem;
    font-size: 1.1rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent);
  }
  .concept p { font-size: 0.95rem; margin: 0; }
</style>
