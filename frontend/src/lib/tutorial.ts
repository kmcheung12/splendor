// frontend/src/lib/tutorial.ts
import type { ActionEvent } from './types'

// ── Types ────────────────────────────────────────────────────────────────────

export interface TutorialItem {
  id: string
  title: string
  body: string
  targets: string[]              // keys in SelectorMap to highlight
  trigger: TutorialTrigger
  completedBy: TutorialCompletion
}

/** Condition that makes a pending item eligible to show. */
export type TutorialTrigger =
  | { type: 'human_turn' }
  | { type: 'human_turn_action'; min: number; max: number }   // fires when humanTurnActions contains any id in [min, max)
  | { type: 'after_my_event'; eventType: ActionEvent['type'] }  // fires when player's own event fires

/** Condition that auto-dismisses an active item (in addition to the dismiss button). */
export type TutorialCompletion =
  | { type: 'action_event'; eventType: ActionEvent['type']; condition?: (e: ActionEvent) => boolean }
  | { type: 'dismiss_only' }

/** Context passed into trigger/completion checks. */
export interface TriggerContext {
  isMyTurn: boolean
  humanTurnActions: number[]
  playerName: string
  latestEvent: ActionEvent | null
}

/** A selector value may be a static string or a function that receives the player's name. */
export type SelectorFn = string | ((playerName: string) => string)
export type SelectorMap = Record<string, SelectorFn>

// ── Helpers ──────────────────────────────────────────────────────────────────

export function resolveSelector(fn: SelectorFn, playerName: string): string {
  return typeof fn === 'function' ? fn(playerName) : fn
}

export function isTriggerMet(trigger: TutorialTrigger, ctx: TriggerContext): boolean {
  switch (trigger.type) {
    case 'human_turn':
      return ctx.isMyTurn
    case 'human_turn_action':
      return ctx.isMyTurn && ctx.humanTurnActions.some(a => a >= trigger.min && a < trigger.max)
    case 'after_my_event':
      return ctx.latestEvent?.type === trigger.eventType &&
             ctx.latestEvent?.player === ctx.playerName
  }
}

// ── Selector map for the desktop board layout ─────────────────────────────────
//
// A different layout (e.g. mobile) would provide its own SelectorMap and pass
// it to TutorialOverlay / TutorialController via props on App.svelte.

export const BOARD_SELECTOR_MAP: SelectorMap = {
  'board':               '.board',
  'token-pool':          '.token-pool',
  'tier-reservable':     '.row-lower',          // all three lower rows (rare/uncommon/common)
  'tier-rarer':          '.row-top',            // epic + legendary row
  'own-panel':           (p) => `[data-player-name="${p}"]`,
  'own-panel-tokens':    (p) => `[data-player-name="${p}"] .token-belt`,
  'own-panel-reserved':  (p) => `[data-player-name="${p}"] .reserved-col, [data-player-name="${p}"] .reserved-row`,
  'own-panel-lanes':     (p) => `[data-player-name="${p}"] .lanes, [data-player-name="${p}"] .lanes-right`,
}

// ── Tutorial items (ordered — engine shows the first pending item whose trigger fires) ──

export const TUTORIAL_ITEMS: TutorialItem[] = [
  // ── UI orientation: shown at start of first human turn, one at a time ─────
  {
    id: 'ui_board',
    title: 'The Pokémon Board',
    body: 'Cards are arranged in 5 tiers. Catch them to earn type bonuses and score points. Higher tiers cost more but score more.',
    targets: ['board'],
    trigger: { type: 'human_turn' },
    completedBy: { type: 'dismiss_only' },
  },
  {
    id: 'ui_tiers_reservable',
    title: 'Common, Uncommon & Rare',
    body: 'These three tiers can be reserved — hold a card for later and receive a golden Master Ball as a bonus.',
    targets: ['tier-reservable'],
    trigger: { type: 'human_turn' },
    completedBy: { type: 'dismiss_only' },
  },
  {
    id: 'ui_tiers_rarer',
    title: 'Epic & Legendary',
    body: 'The rarest Pokémon live here. They score big points but can only be caught directly — no reserving.',
    targets: ['tier-rarer'],
    trigger: { type: 'human_turn' },
    completedBy: { type: 'dismiss_only' },
  },
  {
    id: 'ui_token_pool',
    title: 'Pokéball Pool',
    body: 'Each turn you may take Pokéballs from here. Collect the right types to afford cards. The gold Master Ball is a wildcard.',
    targets: ['token-pool'],
    trigger: { type: 'human_turn' },
    completedBy: { type: 'dismiss_only' },
  },
  {
    id: 'ui_own_panel',
    title: 'Your Trainer Panel',
    body: 'Your score, held Pokéballs, reserved cards, and collection all live here.',
    targets: ['own-panel'],
    trigger: { type: 'human_turn' },
    completedBy: { type: 'dismiss_only' },
  },

  // ── Action tutorials: shown when the relevant action first becomes available ─
  {
    id: 'action_take_3_diff',
    title: 'Take 3 Different Pokéballs',
    body: 'Click up to 3 differently-coloured balls from the pool, then confirm. This is your main way to gather resources.',
    targets: ['token-pool'],
    trigger: { type: 'human_turn_action', min: 0, max: 25 },
    completedBy: { type: 'action_event', eventType: 'take_tokens' },
  },
  {
    id: 'action_take_2_same',
    title: 'Take 2 of the Same',
    body: 'When a pile has 4 or more balls, you can take 2 of the same colour in one go.',
    targets: ['token-pool'],
    trigger: { type: 'human_turn_action', min: 25, max: 30 },
    completedBy: { type: 'action_event', eventType: 'take_tokens' },
  },
  {
    id: 'action_capture_board',
    title: 'Catch a Pokémon',
    body: 'Click any card you can afford. Caught Pokémon give permanent type bonuses that reduce future costs.',
    targets: ['board'],
    trigger: { type: 'human_turn_action', min: 30, max: 44 },
    completedBy: {
      type: 'action_event',
      eventType: 'catch_card',
      condition: (e): boolean => e.type === 'catch_card' && !e.from_reserve,
    },
  },
  {
    id: 'action_reserve_master',
    title: 'Reserve + Master Ball',
    body: "Reserve a Common, Uncommon, or Rare card to save it for later. You'll receive a golden Master Ball wildcard.",
    targets: ['tier-reservable'],
    trigger: { type: 'human_turn_action', min: 47, max: 59 },
    completedBy: { type: 'action_event', eventType: 'reserve_card' },
  },
  {
    id: 'action_capture_reserve',
    title: 'Catch from Reserve',
    body: 'Your reserved cards sit in your panel. When you can afford one, click it to catch it.',
    targets: ['own-panel-reserved'],
    trigger: { type: 'human_turn_action', min: 44, max: 47 },
    completedBy: {
      type: 'action_event',
      eventType: 'catch_card',
      condition: (e): boolean => e.type === 'catch_card' && e.from_reserve,
    },
  },

  // ── Post-action UI reveals: shown immediately after player's first relevant action ─
  {
    id: 'ui_panel_tokens',
    title: 'Your Pokéball Stash',
    body: "Balls you collect appear here. You can hold up to 10 — if you go over, you'll need to discard some.",
    targets: ['own-panel-tokens'],
    trigger: { type: 'after_my_event', eventType: 'take_tokens' },
    completedBy: { type: 'dismiss_only' },
  },
  {
    id: 'ui_panel_reserved',
    title: 'Reserved Pokémon',
    body: 'Reserved cards wait here. You can hold up to 3. Click one to catch it when you have enough balls.',
    targets: ['own-panel-reserved'],
    trigger: { type: 'after_my_event', eventType: 'reserve_card' },
    completedBy: { type: 'dismiss_only' },
  },
  {
    id: 'ui_panel_lanes',
    title: 'Your Pokémon Collection',
    body: 'Caught Pokémon are grouped by type. Each provides permanent bonus balls reducing future costs. Some can evolve into stronger forms.',
    targets: ['own-panel-lanes'],
    trigger: { type: 'after_my_event', eventType: 'catch_card' },
    completedBy: { type: 'dismiss_only' },
  },
]
