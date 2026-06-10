import { describe, it, expect, vi } from 'vitest';
import { createNetworkViz } from '../createNetworkViz';
import { Canvas2DNetworkViz } from '../Canvas2DNetworkViz';

describe('createNetworkViz', () => {
  it('returns Canvas2D for canvas2d', () => {
    const v = createNetworkViz('canvas2d');
    expect(v).toBeInstanceOf(Canvas2DNetworkViz);
  });

  it('falls back to Canvas2D when WebGL is unavailable', () => {
    const v = createNetworkViz('webgl');
    expect(v).toBeInstanceOf(Canvas2DNetworkViz);
  });
});
