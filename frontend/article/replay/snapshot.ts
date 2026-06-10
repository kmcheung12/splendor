import type { TurnRecord } from '../lib/types';

export interface CardSnapshot {
  name: string;
  tier: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
  point: number;
  cost: Record<string, number>;
  bonus: string | null;
}

export interface PlayerSnapshot {
  name: string;
  points: number;
  tokens: Record<string, number>;
  cards: CardSnapshot[];
  reserved_cards: CardSnapshot[];
}

export interface BoardSnapshot {
  common_revealed: (CardSnapshot | null)[];
  uncommon_revealed: (CardSnapshot | null)[];
  rare_revealed: (CardSnapshot | null)[];
  epic_revealed: (CardSnapshot | null)[];
  legendary_revealed: (CardSnapshot | null)[];
  tokens: Record<string, number>;
  players: PlayerSnapshot[];
  active_player: string;
}

export interface ReplaySnapshots {
  initial: BoardSnapshot;
  turns: { turn: number; snapshot: BoardSnapshot; description: string }[];
}

export function loadReplaySnapshots(replayId: string): Promise<ReplaySnapshots> {
  return fetch(`/runs/v1-to-v7/snapshots/${replayId}.json`)
    .then((r) => {
      if (!r.ok) throw new Error(`snapshot ${r.status}`);
      return r.json();
    });
}
