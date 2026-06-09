import type { LayerActivations, NetworkSpec } from './types';

export interface NetworkVisualization {
  mount(container: HTMLElement, network: NetworkSpec): void;
  setActivations(obs: Float32Array, layerOutputs: LayerActivations): void;
  setScrollProgress(t: number): void;
  setHighlightedAction(actionIdx: number | null): void;
  dispose(): void;
}
