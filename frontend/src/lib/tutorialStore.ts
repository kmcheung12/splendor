// frontend/src/lib/tutorialStore.ts
import { writable, get } from 'svelte/store'
import { TUTORIAL_ITEMS, isTriggerMet, type TriggerContext, type TutorialItem } from './tutorial'

// ── State ─────────────────────────────────────────────────────────────────────

export const tutorialMode = writable(false)
export const activeTutorialItem = writable<TutorialItem | null>(null)

/** Ordered list of item IDs not yet shown. Engine shows the first whose trigger fires. */
export const pendingTutorialIds = writable<string[]>([])

// ── Public API ────────────────────────────────────────────────────────────────

/** Call once when "Play Tutorial" creates the game. Resets all state. */
export function initTutorial(): void {
  pendingTutorialIds.set(TUTORIAL_ITEMS.map(i => i.id))
  activeTutorialItem.set(null)
  tutorialMode.set(true)
}

/** Dismiss button handler — marks active item done (no longer pending) and clears active. */
export function dismissActive(): void {
  const active = get(activeTutorialItem)
  if (!active) return
  _markDone(active.id)
}

/**
 * Called by TutorialController whenever turn state changes (isMyTurn, humanTurnActions).
 * Finds the first pending item whose trigger is met and sets it as active.
 * No-ops if already showing an item.
 */
export function checkAndShow(ctx: TriggerContext): void {
  if (!get(tutorialMode)) return
  if (get(activeTutorialItem) !== null) return

  const pending = get(pendingTutorialIds)
  for (const id of pending) {
    const item = TUTORIAL_ITEMS.find(i => i.id === id)
    if (item && isTriggerMet(item.trigger, ctx)) {
      activeTutorialItem.set(item)
      return
    }
  }
}

/**
 * Called by TutorialController when pendingActionEvent fires.
 * 1. If the active item has an action_event completion that matches, marks it done.
 * 2. Then checks whether any after_my_event item should now show.
 */
export function handleActionEvent(ctx: TriggerContext): void {
  if (!get(tutorialMode)) return
  if (!ctx.latestEvent) return

  const active = get(activeTutorialItem)
  if (active?.completedBy.type === 'action_event') {
    const c = active.completedBy
    if (
      ctx.latestEvent.type === c.eventType &&
      ctx.latestEvent.player === ctx.playerName &&
      (!c.condition || c.condition(ctx.latestEvent))
    ) {
      _markDone(active.id)
      // Immediately check whether an after_my_event item should follow
      checkAndShow(ctx)
      return
    }
  }

  // No completion — check whether an after_my_event item should show
  checkAndShow(ctx)
}

// ── Internal ──────────────────────────────────────────────────────────────────

function _markDone(id: string): void {
  pendingTutorialIds.update(ids => ids.filter(x => x !== id))
  activeTutorialItem.set(null)
}
