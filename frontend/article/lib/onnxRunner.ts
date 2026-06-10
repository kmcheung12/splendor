import type { LayerActivations } from '../viz/types';

let session: any | null = null;
let loading: Promise<void> | null = null;

export async function loadOnnxNetwork(runId: string): Promise<void> {
  if (session) return;
  if (loading) return loading;
  loading = (async () => {
    const ort = await import('onnxruntime-web');
    const modelUrl = `/runs/${runId}/network.onnx`;
    const dataUrl = `/runs/${runId}/network.onnx.data`;
    const [modelBuf, dataBuf] = await Promise.all([
      fetch(modelUrl).then((r) => r.arrayBuffer()),
      fetch(dataUrl).then((r) => (r.ok ? r.arrayBuffer() : null)),
    ]);
    const options: Record<string, unknown> = { executionProviders: ['wasm'] };
    if (dataBuf) {
      options.externalData = [
        { data: new Uint8Array(dataBuf), path: 'network.onnx.data' },
      ];
    }
    session = await ort.InferenceSession.create(
      new Uint8Array(modelBuf),
      options as never,
    );
  })();
  return loading;
}

function softmax(logits: Float32Array): Float32Array {
  let max = -Infinity;
  for (let i = 0; i < logits.length; i++) if (logits[i] > max) max = logits[i];
  let sum = 0;
  const out = new Float32Array(logits.length);
  for (let i = 0; i < logits.length; i++) {
    out[i] = Math.exp(logits[i] - max);
    sum += out[i];
  }
  for (let i = 0; i < out.length; i++) out[i] /= sum;
  return out;
}

export function extractActivations(
  outputs: Record<string, { data: Float32Array }>,
): LayerActivations {
  const layers: Float32Array[] = [];
  const keys = Object.keys(outputs)
    .filter((k) => k.startsWith('hidden_'))
    .sort();
  for (const k of keys) layers.push(outputs[k].data);
  const policy = softmax(outputs.policy_logits.data);
  const value = outputs.value.data[0];
  return { layers, policy, value };
}

export async function runNetwork(
  observation: Float32Array,
): Promise<LayerActivations> {
  if (!session) throw new Error('ONNX network not loaded');
  const ort = await import('onnxruntime-web');
  const tensor = new ort.Tensor('float32', observation, [1, observation.length]);
  const out = await session.run({ observation: tensor });
  return extractActivations(out);
}
