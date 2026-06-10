<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { HeroParticles } from '../viz/HeroParticles';
  import { isWebGLAvailable } from '../viz/createNetworkViz';

  let particleContainer: HTMLElement;
  let particles: HeroParticles | null = null;

  onMount(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) return;
    if (!isWebGLAvailable()) return;
    try {
      particles = new HeroParticles(particleContainer);
    } catch (e) {
      console.warn('HeroParticles disabled:', e);
    }
  });
  onDestroy(() => particles?.dispose());
</script>

<section class="hero">
  <div class="particles" bind:this={particleContainer}></div>
  <div class="content">
    <h1>We taught a neural network<br />to play Splendor.</h1>
    <p class="subtitle">
      One million games. Seven generations. Here's how the agent learned —
      and how we know it really did.
    </p>
    <nav class="toc" aria-label="Contents">
      <span class="toc-label">Contents</span>
      <ol>
        <li><a href="#game">Splendor in 90 seconds</a></li>
        <li><a href="#rl">How a network learns by playing</a></li>
        <li><a href="#anatomy">The shape of the network</a></li>
        <li><a href="#training">Watching it learn, batch by batch</a></li>
        <li><a href="#in-depth">The same network, in three dimensions</a></li>
        <li><a href="#in-action">The agent, mid-decision</a></li>
        <li><a href="#closing">Try it yourself</a></li>
      </ol>
    </nav>
    <div class="scroll-hint">Scroll to begin</div>
  </div>
</section>

<style>
  .hero {
    min-height: 100vh;
    position: relative;
    display: grid;
    place-items: center;
    text-align: center;
    padding: 4rem 1.5rem;
  }
  .particles {
    position: absolute; inset: 0;
    z-index: 0;
    opacity: 0.65;
  }
  .content { position: relative; z-index: 1; max-width: 56rem; }
  h1 {
    font-size: clamp(2.5rem, 7vw, 5rem);
    font-weight: 700;
    line-height: 1.05;
    letter-spacing: -0.02em;
    margin: 0 0 1.5rem;
  }
  .subtitle {
    color: var(--muted);
    font-size: clamp(1.1rem, 2vw, 1.35rem);
    max-width: 38rem;
    margin: 0 auto;
  }
  .toc {
    margin: 3rem auto 0;
    max-width: 32rem;
    text-align: left;
  }
  .toc-label {
    display: block;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--muted);
    opacity: 0.7;
    margin-bottom: 0.75rem;
  }
  .toc ol {
    margin: 0;
    padding: 0;
    list-style: none;
    counter-reset: chapter;
    display: grid;
    gap: 0.4rem;
  }
  .toc li {
    counter-increment: chapter;
    display: flex;
    align-items: baseline;
    gap: 0.85rem;
    font-size: 1rem;
  }
  .toc li::before {
    content: counter(chapter, decimal-leading-zero);
    color: var(--accent);
    font-variant-numeric: tabular-nums;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
    min-width: 1.5rem;
  }
  .toc a {
    color: var(--fg);
    text-decoration: none;
    border-bottom: 1px solid rgba(255,255,255,0.12);
    padding-bottom: 0.05em;
    transition: border-color 0.2s ease, color 0.2s ease;
  }
  .toc a:hover {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }
  .scroll-hint {
    margin-top: 3rem;
    font-size: 0.8rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--muted);
    opacity: 0.7;
  }
</style>
