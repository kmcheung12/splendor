<!-- frontend/src/components/TutorialController.svelte -->
<script lang="ts">
  import { pendingActionEvent, isMyTurn, humanTurnActions, mySlot, gameState } from '../lib/gameStore'
  import { activeTutorialItem, tutorialMode, checkAndShow, handleActionEvent } from '../lib/tutorialStore'

  $: playerName = $gameState?.players[$mySlot ?? -1]?.name ?? ''

  /*
   * Rule 1: check for the next item to show when:
   *   - It becomes the player's turn ($isMyTurn changes to true)
   *   - The active item is dismissed ($activeTutorialItem changes to null)
   *   - humanTurnActions changes (new actions became available mid-turn)
   * checkAndShow no-ops when activeTutorialItem !== null, so calling it here is safe.
   */
  $: if ($tutorialMode && !$activeTutorialItem) {
    checkAndShow({
      isMyTurn: $isMyTurn,
      humanTurnActions: $humanTurnActions,
      playerName,
      latestEvent: null,
    })
  }

  /*
   * Rule 2: process action events.
   * Checks whether the active item's completion condition is met,
   * then checks for after_my_event trigger items.
   */
  $: if ($tutorialMode && $pendingActionEvent) {
    handleActionEvent({
      isMyTurn: $isMyTurn,
      humanTurnActions: $humanTurnActions,
      playerName,
      latestEvent: $pendingActionEvent,
    })
  }
</script>
