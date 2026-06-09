import { describe, it, expect, vi } from 'vitest';

vi.mock('gsap', () => ({ gsap: { registerPlugin: vi.fn() } }));
vi.mock('gsap/ScrollTrigger', () => ({ ScrollTrigger: { create: vi.fn(), update: vi.fn() } }));
vi.mock('lenis', () => ({ default: vi.fn() }));

import { clamp, mapRange } from '../scrollProgress';

describe('clamp', () => {
  it('clamps to range', () => {
    expect(clamp(-1, 0, 1)).toBe(0);
    expect(clamp(2, 0, 1)).toBe(1);
    expect(clamp(0.5, 0, 1)).toBe(0.5);
  });
});

describe('mapRange', () => {
  it('linearly maps a value across ranges', () => {
    expect(mapRange(50, 0, 100, 0, 1)).toBeCloseTo(0.5);
    expect(mapRange(0, 0, 100, 0, 1)).toBeCloseTo(0);
    expect(mapRange(100, 0, 100, 0, 1)).toBeCloseTo(1);
  });

  it('clamps outside source range by default', () => {
    expect(mapRange(150, 0, 100, 0, 1)).toBeCloseTo(1);
    expect(mapRange(-50, 0, 100, 0, 1)).toBeCloseTo(0);
  });
});
