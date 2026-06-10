import { describe, it, expect, vi } from 'vitest';

describe('WebGLNetworkViz', () => {
  it('falls back gracefully when WebGL unavailable (jsdom case)', async () => {
    const { WebGLNetworkViz } = await import('../WebGLNetworkViz');
    const viz = new WebGLNetworkViz();
    const container = document.createElement('div');
    Object.defineProperty(container, 'clientWidth', { value: 800 });
    Object.defineProperty(container, 'clientHeight', { value: 400 });
    document.body.appendChild(container);
    // Three will throw in jsdom; viz constructor must not throw, mount must throw.
    expect(() => viz.mount(container, {
      inputSize: 100, hiddenLayers: [16], outputSize: 10,
    })).toThrow(/WebGL/);
  });
});
