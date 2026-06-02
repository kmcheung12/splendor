// frontend/src/lib/ws.ts
import type { ServerMessage, ActionEvent } from './types'
import {
  gameState, lobbyState, mySlot, isHost,
  activePlayer, thinkingPlayer, humanTurnActions,
  pendingActionEvent, gameOver, phase,
} from './gameStore'
import { animQueue, delay } from './animationQueue'

let ws: WebSocket | null = null

export function connect(gameId: string): void {
  ws = new WebSocket(`/ws/${gameId}`)
  ws.onmessage = (e) => handleMessage(JSON.parse(e.data) as ServerMessage)
  ws.onclose = () => { ws = null }
}

export function sendAction(actionId: number): void {
  ws?.send(JSON.stringify({ type: 'action', action_id: actionId }))
}

export function claimSlot(slot: number, name: string): void {
  ws?.send(JSON.stringify({ type: 'claim', slot, name }))
}

export function releaseSlot(): void {
  ws?.send(JSON.stringify({ type: 'release' }))
  mySlot.set(null)
}

export function startGame(): void {
  ws?.send(JSON.stringify({ type: 'start' }))
}

export function setDelay(ms: number): void {
  ws?.send(JSON.stringify({ type: 'config', delay_ms: ms }))
}

function handleMessage(msg: ServerMessage): void {
  switch (msg.type) {
    case 'lobby':
      lobbyState.set(msg)
      isHost.set(!!msg.is_host)
      break

    case 'state':
      gameState.set(msg.game)
      activePlayer.set(msg.game.turn)
      phase.set(msg.game.phase)
      thinkingPlayer.set(null)
      humanTurnActions.set([])
      break

    case 'thinking':
      thinkingPlayer.set(msg.player)
      break

    case 'human_turn':
      humanTurnActions.set(msg.valid_actions)
      thinkingPlayer.set(msg.player)
      break

    case 'game_over':
      gameOver.set({ winner: msg.winner, scores: msg.scores })
      break

    case 'take_tokens':
    case 'catch_card':
    case 'reserve_card':
    case 'discard_token':
    case 'evolve_card':
    case 'pass':
      animQueue.enqueue(async () => {
        pendingActionEvent.set(msg as ActionEvent)
        await delay(400)
        pendingActionEvent.set(null)
      })
      break
  }
}
