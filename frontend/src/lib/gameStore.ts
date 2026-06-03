// frontend/src/lib/gameStore.ts
import { writable, derived } from 'svelte/store'
import type { GameState, LobbyState, ActionEvent } from './types'

export const gameState = writable<GameState | null>(null)
export const lobbyState = writable<LobbyState | null>(null)
export const mySlot = writable<number | null>(null)
export const isHost = writable(false)
export const activePlayer = writable<string | null>(null)
export const thinkingPlayer = writable<string | null>(null)
export const humanTurnActions = writable<number[]>([])
export const pendingActionEvent = writable<ActionEvent | null>(null)
export const gameOver = writable<{ winner: string; scores: Record<string, number> } | null>(null)
export const phase = writable<string>('main')

export const isMyTurn = derived(
  [activePlayer, mySlot, gameState, humanTurnActions],
  ([$active, $slot, $game, $actions]) => {
    if ($slot === null || !$game || $actions.length === 0) return false
    return $active === $game.players[$slot]?.name
  }
)

