export interface SlotInfo {
  index: number
  agent_type: string
  claimed_by: string | null
}

export interface LobbyState {
  type: 'lobby'
  join_code: string
  delay_ms: number
  slots: SlotInfo[]
  spectators: number
  is_host?: boolean
}

export interface PokemonCard {
  name: string
  tier: string
  cost: string[]
  bonus: string[]
  evolve: string[]
  evolve_into: string
  point: number
  evolved: boolean
}

export interface PlayerState {
  name: string
  points: number
  tokens: Record<string, number>
  cards: PokemonCard[]
  reserved_cards: PokemonCard[]
}

export interface BoardState {
  common_revealed: (PokemonCard | null)[]
  uncommon_revealed: (PokemonCard | null)[]
  rare_revealed: (PokemonCard | null)[]
  epic_revealed: (PokemonCard | null)[]
  legendary_revealed: (PokemonCard | null)[]
  common_deck_count: number
  uncommon_deck_count: number
  rare_deck_count: number
  epic_deck_count: number
  legendary_deck_count: number
}

export interface GameState {
  round: number
  phase: string
  turn: string
  players: PlayerState[]
  board: BoardState
  board_tokens: Record<string, number>
}

export type ActionEvent =
  | { type: 'take_tokens'; player: string; tokens: string[] }
  | { type: 'catch_card'; player: string; card: string | null; slot: number; tier: string | null; from_reserve: boolean }
  | { type: 'reserve_card'; player: string; card: string | null; slot: number; tier: string | null; took_master: boolean }
  | { type: 'discard_token'; player: string; token: string }
  | { type: 'evolve_card'; player: string; card: string | null; card_index: number }
  | { type: 'pass'; player: string }

export type ServerMessage =
  | LobbyState
  | { type: 'state'; game: GameState }
  | ActionEvent
  | { type: 'thinking'; player: string }
  | { type: 'human_turn'; player: string; valid_actions: number[] }
  | { type: 'game_over'; winner: string; scores: Record<string, number> }
  | { type: 'error'; msg: string }
