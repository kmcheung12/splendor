// frontend/src/lib/ws.ts
import type { ServerMessage, ActionEvent } from './types'
import {
  gameState, lobbyState, mySlot, isHost,
  activePlayer, thinkingPlayer, humanTurnActions,
  pendingActionEvent, gameOver, phase,
  tokenSelectMode, stagedTokens, lastActions, playerNames,
} from './gameStore'
import { animQueue, delay } from './animationQueue'

let ws: WebSocket | null = null

export function connect(gameId: string): void {
  ws = new WebSocket(`/ws/${gameId}`)
  ws.onmessage = (e) => handleMessage(JSON.parse(e.data) as ServerMessage)
  ws.onclose = () => { ws = null }
}

export function sendAction(actionId: number): void {
  humanTurnActions.set([])  // clear immediately so isMyTurn → false before animQueue fires
  ws?.send(JSON.stringify({ type: 'action', action_id: actionId }))
}

export function claimSlot(slot: number, name: string): void {
  ws?.send(JSON.stringify({ type: 'claim', slot, name }))
}

export function renameSlot(name: string): void {
  console.log('[renameSlot] ws=%o name=%s', ws?.readyState, name)
  ws?.send(JSON.stringify({ type: 'rename', name }))
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

function actionLabel(e: ActionEvent): string {
  switch (e.type) {
    case 'take_tokens': return `Took ${e.tokens.join(', ')}`
    case 'catch_card':  return e.card ? `Caught ${e.card}` : 'Caught card'
    case 'reserve_card': return e.card ? `Reserved ${e.card}` : 'Reserved card'
    case 'discard_token': return `Discarded ${e.token}`
    case 'evolve_card': return e.card ? `Evolved ${e.card}` : 'Evolved card'
    case 'pass': return 'Passed'
  }
}

function handleMessage(msg: ServerMessage): void {
  switch (msg.type) {
    case 'lobby':
      console.log('[lobby] slots=%o', msg.slots.map((s: {index:number,claimed_by:string|null}) => `${s.index}:${s.claimed_by}`))
      lobbyState.set(msg)
      isHost.set(!!msg.is_host)
      break

    case 'state':
      gameState.set(msg.game)
      activePlayer.set(msg.game.turn)
      phase.set(msg.game.phase)
      thinkingPlayer.set(null)
      humanTurnActions.set([])
      tokenSelectMode.set(false)
      stagedTokens.set([])
      if (msg.player_names) playerNames.set(msg.player_names)
      console.log('[state] round=%d phase=%s turn=%s tokens=%o', msg.game.round, msg.game.phase, msg.game.turn, msg.game.board_tokens)
      break

    case 'thinking':
      thinkingPlayer.set(msg.player)
      break

    case 'human_turn':
      humanTurnActions.set(msg.valid_actions)
      thinkingPlayer.set(msg.player)
      console.log('[human_turn] player=%s validActions=%o', msg.player, msg.valid_actions)
      break

    case 'game_over':
      gameOver.set({ winner: msg.winner, scores: msg.scores, rounds: msg.rounds })
      break

    case 'take_tokens':
    case 'catch_card':
    case 'reserve_card':
    case 'discard_token':
    case 'evolve_card':
    case 'pass':
      console.log('[action] %o', msg)
      lastActions.update(m => ({ ...m, [(msg as ActionEvent).player]: actionLabel(msg as ActionEvent) }))
      animQueue.enqueue(async () => {
        pendingActionEvent.set(msg as ActionEvent)
        await delay(400)
        pendingActionEvent.set(null)
      })
      break
  }
}
