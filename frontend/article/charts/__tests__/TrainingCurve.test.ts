import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import TrainingCurve from '../TrainingCurve.svelte';

describe('TrainingCurve', () => {
  it('renders an SVG with one polyline', () => {
    const { container } = render(TrainingCurve, {
      props: {
        batches: [
          { id: 'v1', total_timesteps: 200000, explained_variance: -0.1,
            entropy_loss: -1.5, value_loss: 0.05 },
          { id: 'v2', total_timesteps: 500000, explained_variance: 0.1,
            entropy_loss: -1.0, value_loss: 0.04 },
        ],
        metric: 'explained_variance',
        currentIndex: 1,
      },
    });
    expect(container.querySelector('svg')).toBeTruthy();
    expect(container.querySelectorAll('circle').length).toBe(2);
  });
});
