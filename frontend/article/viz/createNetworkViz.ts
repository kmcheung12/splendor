import type { NetworkVisualization } from './NetworkVisualization';
import type { VizType } from './types';
import { Canvas2DNetworkViz } from './Canvas2DNetworkViz';

export function isWebGLAvailable(): boolean {
  if (typeof document === 'undefined') return false;
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    if (!gl) return false;
    // A context can be created but lack a real GPU (headless / disabled accel).
    // Probe with a tiny shader compile to flush out fake contexts.
    const ctx = gl as WebGLRenderingContext;
    const vs = ctx.createShader(ctx.VERTEX_SHADER);
    if (!vs) return false;
    ctx.shaderSource(vs, 'void main(){gl_Position=vec4(0.0);}');
    ctx.compileShader(vs);
    const ok = !!ctx.getShaderParameter(vs, ctx.COMPILE_STATUS);
    ctx.deleteShader(vs);
    // Also check the standard "WebGL is masked" sentinel via DEBUG_RENDERER_INFO
    const dbg = ctx.getExtension('WEBGL_debug_renderer_info');
    if (dbg) {
      const renderer = ctx.getParameter(dbg.UNMASKED_RENDERER_WEBGL);
      if (typeof renderer === 'string' && /Disabled|SwiftShader/i.test(renderer)) {
        return false;
      }
    }
    return ok;
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
    try {
      const { WebGLNetworkViz } = await import('./WebGLNetworkViz');
      return new WebGLNetworkViz();
    } catch (e) {
      console.warn('WebGLNetworkViz construction failed; falling back to Canvas2D:', e);
    }
  }
  return new Canvas2DNetworkViz();
}
