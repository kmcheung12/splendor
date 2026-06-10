import { describe, it, expect, vi } from 'vitest';
import { loadReplaySnapshots } from '../snapshot';

describe('loadReplaySnapshots', () => {
  it('fetches a snapshot file', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        initial: { tokens: {}, common_revealed: [], uncommon_revealed: [],
                   rare_revealed: [], epic_revealed: [], legendary_revealed: [],
                   players: [], active_player: 'p0' },
        turns: [],
      }),
    }) as unknown as typeof fetch;
    const snaps = await loadReplaySnapshots('test');
    expect(snaps.initial.active_player).toBe('p0');
  });

  it('throws on missing replay file', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 });
    await expect(loadReplaySnapshots('missing')).rejects.toThrow('404');
  });
});
