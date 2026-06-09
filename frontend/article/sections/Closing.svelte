<section class="closing">
  <div class="prose">
    <h2>Try it yourself.</h2>
    <p>
      The trained agent is playable in your browser. The training scripts,
      benchmarks, and source code are open.
    </p>
    <ul class="links">
      <li><a href="https://geo-dude.com/splendor">Play against the agent</a></li>
      <li><a href="https://github.com/your-org/splendor">Source on GitHub</a></li>
      <li><a href="https://github.com/your-org/splendor/blob/main/training_log.txt">Full training log</a></li>
    </ul>
    <p class="credits">
      Built with Svelte, GSAP, and Three.js. The neural network was trained
      using <a href="https://github.com/Stable-Baselines-Team/stable-baselines3-contrib">MaskablePPO</a>.
      Inspired by Bartosz Ciechanowski and Tensorflow Playground.
    </p>
  </div>
</section>

<style>
  .closing {
    padding: 12rem 1.5rem;
    text-align: center;
  }
  .prose {
    max-width: 48rem;
    margin: 0 auto;
  }
  h2 { font-size: clamp(2.5rem, 5vw, 4rem); margin: 0 0 2rem; }
  .links {
    list-style: none;
    padding: 0;
    margin: 3rem 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .links a {
    font-size: 1.2rem;
    text-decoration: none;
    border-bottom: 1px solid currentColor;
  }
  .credits { font-size: 0.9rem; color: var(--muted); margin-top: 4rem; }
</style>
