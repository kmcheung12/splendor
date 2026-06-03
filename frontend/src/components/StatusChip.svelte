<script lang="ts">
  import { thinkingPlayer, activePlayer, phase } from '../lib/gameStore'

  $: displayName = $thinkingPlayer ?? $activePlayer ?? '…'
  $: isThinking = !!$thinkingPlayer
  $: label = isThinking ? `${displayName} — thinking…` : `▶ ${displayName} — ${$phase}`
</script>

<div class="chip" class:thinking={isThinking}>
  {#if isThinking}
    <span class="spinner">⟳</span>
  {/if}
  {label}
</div>

<style>
  .chip {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 12px; border-radius: 20px;
    background: rgba(0,0,0,.5); color: white;
    font-size: .8rem; font-weight: 500;
    border: 1px solid rgba(255,255,255,.15);
    transition: background .3s;
  }
  .chip.thinking { background: rgba(52,73,94,.8); }
  .spinner { display: inline-block; animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
