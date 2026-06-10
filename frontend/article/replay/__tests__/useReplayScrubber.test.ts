import { describe, it, expect, vi } from 'vitest';

vi.mock('gsap', () => ({ gsap: { registerPlugin: vi.fn() } }));
vi.mock('gsap/ScrollTrigger', () => ({ ScrollTrigger: { create: vi.fn(), update: vi.fn() } }));
vi.mock('lenis', () => ({ default: vi.fn() }));

import { mapScrollToBatchTurn } from '../useReplayScrubber';

describe('mapScrollToBatchTurn', () => {
  it('maps 0..1 to (batchIdx, turnIdx)', () => {
    const batchCounts = [10, 20, 5];
    expect(mapScrollToBatchTurn(0, batchCounts)).toEqual([0, 0]);
    expect(mapScrollToBatchTurn(1, batchCounts)).toEqual([2, 4]);
    const [b, _t] = mapScrollToBatchTurn(0.5, batchCounts);
    expect(b).toBe(1);
  });
});
