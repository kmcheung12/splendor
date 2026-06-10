import { describe, it, expect, beforeEach } from 'vitest';
import { Canvas2DNetworkViz } from '../Canvas2DNetworkViz';
import { computeLayout } from '../Canvas2DNetworkViz';

describe('Canvas2DNetworkViz', () => {
  let container: HTMLElement;
  beforeEach(() => {
    container = document.createElement('div');
    Object.defineProperty(container, 'clientWidth', { value: 800 });
    Object.defineProperty(container, 'clientHeight', { value: 400 });
    document.body.appendChild(container);
  });

  it('mounts a canvas matching container size', () => {
    const viz = new Canvas2DNetworkViz();
    viz.mount(container, {
      inputSize: 100, hiddenLayers: [16, 16], outputSize: 10,
    });
    const canvas = container.querySelector('canvas');
    expect(canvas).toBeTruthy();
    expect(canvas?.width).toBe(800);
    expect(canvas?.height).toBe(400);
    viz.dispose();
    expect(container.querySelector('canvas')).toBeFalsy();
  });
});

describe('computeLayout', () => {
  it('produces one column per layer with correct x positions', () => {
    const layout = computeLayout(
      { inputSize: 4, hiddenLayers: [8, 8], outputSize: 3 },
      { width: 400, height: 200, padding: 40 },
    );
    expect(layout.columns).toHaveLength(4);
    expect(layout.columns[0].x).toBe(40);
    expect(layout.columns[3].x).toBe(360);
  });

  it('limits visible nodes per column to 32 (256-wide layers downsampled)', () => {
    const layout = computeLayout(
      { inputSize: 421, hiddenLayers: [256, 256, 256], outputSize: 50 },
      { width: 800, height: 400, padding: 40 },
    );
    layout.columns.forEach((c) => expect(c.nodes.length).toBeLessThanOrEqual(32));
  });
});
