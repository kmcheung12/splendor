import type { NetworkVisualization } from './NetworkVisualization';
import type { LayerActivations, NetworkSpec } from './types';

export interface LayoutOptions {
  width: number;
  height: number;
  padding: number;
}

export interface LayoutColumn {
  x: number;
  nodes: { y: number; activation: number }[];
}

export interface NetworkLayout {
  columns: LayoutColumn[];
}

const MAX_VISIBLE_NODES = 32;

export function computeLayout(
  spec: NetworkSpec, opts: LayoutOptions,
): NetworkLayout {
  const layerSizes = [
    spec.inputSize,
    ...spec.hiddenLayers,
    spec.outputSize,
  ];
  const cols = layerSizes.length;
  const xStep = (opts.width - 2 * opts.padding) / Math.max(cols - 1, 1);
  const innerHeight = opts.height - 2 * opts.padding;
  const columns: LayoutColumn[] = layerSizes.map((size, i) => {
    const visible = Math.min(size, MAX_VISIBLE_NODES);
    const yStep = visible > 1 ? innerHeight / (visible - 1) : 0;
    const nodes = Array.from({ length: visible }, (_, j) => ({
      y: opts.padding + j * yStep,
      activation: 0,
    }));
    return { x: opts.padding + i * xStep, nodes };
  });
  return { columns };
}

export class Canvas2DNetworkViz implements NetworkVisualization {
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private network: NetworkSpec | null = null;
  private activations: LayerActivations | null = null;
  private layout: NetworkLayout | null = null;
  private scrollT = 0;
  private highlight: number | null = null;
  private rafHandle = 0;

  mount(container: HTMLElement, network: NetworkSpec): void {
    this.network = network;
    const canvas = document.createElement('canvas');
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    container.appendChild(canvas);
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.layout = computeLayout(network, {
      width: this.canvas.width, height: this.canvas.height, padding: 40,
    });
    this.draw();
  }

  setActivations(_obs: Float32Array, layerOutputs: LayerActivations): void {
    this.activations = layerOutputs;
    if (!this.layout || !this.network) return;
    const layerSources: Float32Array[] = [
      _obs, ...layerOutputs.layers, layerOutputs.policy,
    ];
    this.layout.columns.forEach((col, ci) => {
      const src = layerSources[ci];
      if (!src) return;
      col.nodes.forEach((node, ni) => {
        const idx = Math.floor((ni / col.nodes.length) * src.length);
        node.activation = src[idx];
      });
    });
    this.draw();
  }

  setScrollProgress(t: number): void {
    this.scrollT = t;
    this.draw();
  }

  setHighlightedAction(actionIdx: number | null): void {
    this.highlight = actionIdx;
    this.draw();
  }

  dispose(): void {
    cancelAnimationFrame(this.rafHandle);
    this.canvas?.remove();
    this.canvas = null;
    this.ctx = null;
  }

  private draw(): void {
    if (!this.ctx || !this.canvas || !this.network) return;
    const { width, height } = this.canvas;
    const ctx = this.ctx;
    ctx.clearRect(0, 0, width, height);

    const layout = this.layout ?? computeLayout(this.network, {
      width, height, padding: 40,
    });
    const reveal = this.scrollT;
    const colsToShow = Math.ceil(layout.columns.length * reveal);

    // Edges
    ctx.strokeStyle = 'rgba(243,241,236,0.06)';
    ctx.lineWidth = 1;
    for (let i = 0; i < colsToShow - 1; i++) {
      const a = layout.columns[i];
      const b = layout.columns[i + 1];
      for (const na of a.nodes) {
        for (const nb of b.nodes) {
          ctx.beginPath();
          ctx.moveTo(a.x, na.y);
          ctx.lineTo(b.x, nb.y);
          ctx.stroke();
        }
      }
    }

    // Nodes
    for (let i = 0; i < colsToShow; i++) {
      const col = layout.columns[i];
      for (const n of col.nodes) {
        const a = Math.max(0, Math.min(1, n.activation));
        ctx.fillStyle = `rgba(255,${Math.floor(61 + 100 * (1 - a))},${Math.floor(138 + 60 * (1 - a))},${0.4 + 0.6 * a})`;
        ctx.beginPath();
        ctx.arc(col.x, n.y, 4, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }
}
