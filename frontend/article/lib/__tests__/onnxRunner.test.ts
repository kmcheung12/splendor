import { describe, it, expect } from 'vitest';
import { extractActivations } from '../onnxRunner';

describe('extractActivations', () => {
  it('packs ORT output map into LayerActivations', () => {
    const fakeOut = {
      policy_logits: { data: new Float32Array([1, 2, 3, 4]) },
      value: { data: new Float32Array([0.5]) },
      hidden_0: { data: new Float32Array([0.1, 0.2]) },
      hidden_1: { data: new Float32Array([0.3, 0.4]) },
    };
    const acts = extractActivations(fakeOut as any);
    expect(acts.layers).toHaveLength(2);
    expect(acts.layers[0]).toEqual(new Float32Array([0.1, 0.2]));
    expect(acts.value).toBeCloseTo(0.5);
    expect(acts.policy.length).toBe(4);
  });
});
