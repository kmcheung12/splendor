export interface NetworkSpec {
  inputSize: number;
  hiddenLayers: number[];
  outputSize: number;
}

export interface LayerActivations {
  layers: Float32Array[];
  policy: Float32Array;
  value: number;
}

export type VizType = 'canvas2d' | 'webgl';
