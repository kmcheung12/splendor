<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { HeroParticles } from '../viz/HeroParticles';

  let particleContainer: HTMLElement;
  let particles: HeroParticles | null = null;

  onMount(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduced) {
      particles = new HeroParticles(particleContainer);
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
  .scroll-hint {
    margin-top: 4rem;
    font-size: 0.8rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--muted);
    opacity: 0.7;
  }
</style>
