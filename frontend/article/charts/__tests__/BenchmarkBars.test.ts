import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import BenchmarkBars from '../BenchmarkBars.svelte';

describe('BenchmarkBars', () => {
  it('renders one bar per opponent', () => {
    const { container } = render(BenchmarkBars, {
      props: {
        benchmark: {
          opponents: ['agent', 'random', 'early-capture', 'denial'],
          win_rates: [0.4, 0.0, 0.2, 0.4],
          games: 200,
        },
        agentIndex: 0,
      },
    });
    expect(container.querySelectorAll('.bar').length).toBe(4);
  });
});
