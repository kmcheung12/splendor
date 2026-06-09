import { describe, it, expect, vi, beforeEach } from 'vitest';
import { loadRunSummary } from '../data';
import fixture from './fixtures/summary.json';

describe('loadRunSummary', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => fixture,
    }) as unknown as typeof fetch;
  });

  it('fetches and validates run summary', async () => {
    const summary = await loadRunSummary('v1-to-v7');
    expect(summary.title).toBe('Test run');
    expect(summary.batches[0].id).toBe('v1');
  });

  it('throws on missing required field', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ batches: [] }),
    }) as unknown as typeof fetch;
    await expect(loadRunSummary('x')).rejects.toThrow(/title/);
  });
});
