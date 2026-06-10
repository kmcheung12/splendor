import { describe, it, expect, beforeEach } from 'vitest';
import { Canvas2DNetworkViz } from '../Canvas2DNetworkViz';

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
