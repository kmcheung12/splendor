import { clamp } from '../lib/scrollProgress';

export function mapScrollToBatchTurn(
  t: number, batchTurnCounts: number[],
): [number, number] {
  const total = batchTurnCounts.reduce((s, n) => s + n, 0);
  if (total === 0) return [0, 0];
  const target = clamp(t, 0, 1) * (total - 1);
  let cumulative = 0;
  for (let i = 0; i < batchTurnCounts.length; i++) {
    if (target < cumulative + batchTurnCounts[i]) {
      return [i, Math.floor(target - cumulative)];
    }
    cumulative += batchTurnCounts[i];
  }
  const last = batchTurnCounts.length - 1;
  return [last, batchTurnCounts[last] - 1];
}
