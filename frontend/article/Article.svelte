<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { initSmoothScroll } from './lib/scrollProgress';
  import Hero from './sections/Hero.svelte';
  import Game101 from './sections/Game101.svelte';
  import RL101 from './sections/RL101.svelte';
  import NetworkAnatomy from './sections/NetworkAnatomy.svelte';
  import TrainingStory from './sections/TrainingStory.svelte';
  import NetworkInDepth from './sections/NetworkInDepth.svelte';
  import AgentInAction from './sections/AgentInAction.svelte';
  import Closing from './sections/Closing.svelte';

  let cleanup: () => void = () => undefined;

  onMount(() => {
    cleanup = initSmoothScroll();
  });
  onDestroy(() => cleanup());
</script>

<Hero />
<Game101 />
<RL101 />
<NetworkAnatomy />
<TrainingStory />
<NetworkInDepth />
<AgentInAction />
<Closing />
