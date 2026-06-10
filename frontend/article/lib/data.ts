import type {
  RunSummary, RunIndex, Curves, NetworkSpec, Replay,
} from './types';

function validateRunSummary(x: unknown): RunSummary {
  if (!x || typeof x !== 'object') throw new Error('summary not an object');
  const o = x as Record<string, unknown>;
  if (typeof o.title !== 'string') throw new Error('summary.title missing');
  if (!Array.isArray(o.batches)) throw new Error('summary.batches missing');
  return o as unknown as RunSummary;
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return (await res.json()) as T;
}

export async function loadRunIndex(): Promise<RunIndex> {
  return fetchJson<RunIndex>('/runs/index.json');
}

export async function loadRunSummary(runId: string): Promise<RunSummary> {
  const raw = await fetchJson<unknown>(`/runs/${runId}/summary.json`);
  return validateRunSummary(raw);
}

export async function loadCurves(runId: string): Promise<Curves> {
  return fetchJson<Curves>(`/runs/${runId}/curves.json`);
}

export async function loadNetworkSpec(runId: string): Promise<NetworkSpec> {
  return fetchJson<NetworkSpec>(`/runs/${runId}/network.json`);
}

export async function loadReplay(runId: string, replayId: string): Promise<Replay> {
  return fetchJson<Replay>(`/runs/${runId}/replays/${replayId}.json`);
}
