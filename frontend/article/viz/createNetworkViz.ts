import type { NetworkVisualization } from './NetworkVisualization';
import type { VizType } from './types';
import { Canvas2DNetworkViz } from './Canvas2DNetworkViz';

function isWebGLAvailable(): boolean {
  if (typeof document === 'undefined') return false;
  try {
    const canvas = document.createElement('canvas');
    return !!(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch {
    return false;
  }
}

export function createNetworkViz(type: VizType): NetworkVisualization {
  if (type === 'webgl' && isWebGLAvailable()) {
    // Note: dynamic import is async; we return Canvas2D synchronously and
    // callers that want WebGL should await createNetworkVizAsync instead.
    // In practice, jsdom never has WebGL so this branch is unreachable in tests.
    return new Canvas2DNetworkViz();
  }
  return new Canvas2DNetworkViz();
}

export async function createNetworkVizAsync(type: VizType): Promise<NetworkVisualization> {
  if (type === 'webgl' && isWebGLAvailable()) {
    const { WebGLNetworkViz } = await import('./WebGLNetworkViz');
    return new WebGLNetworkViz();
  }
  return new Canvas2DNetworkViz();
}
