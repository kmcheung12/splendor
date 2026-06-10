export interface TrainingMetrics {
  total_timesteps: number;
  explained_variance: number;
  entropy_loss: number;
  value_loss: number;
  clip_fraction: number;
}

export interface BenchmarkResult {
  opponents: string[];
  win_rates: number[];
  games: number;
}

export interface BatchResult {
  id: string;
  stage: number;
  opponents: string[];
  episodes: number;
  lr: number;
  result: TrainingMetrics;
  benchmarks: BenchmarkResult[];
  narrative: string;
}

export interface RunSummary {
  title: string;
  batches: BatchResult[];
}

export interface RunIndexEntry {
  id: string;
  title: string;
  default: boolean;
}

export interface RunIndex {
  runs: RunIndexEntry[];
}

export interface CurvesPerBatch {
  id: string;
  total_timesteps: number;
  explained_variance: number;
  entropy_loss: number;
  value_loss: number;
}

export interface Curves {
  batches: CurvesPerBatch[];
}

export interface NetworkSpec {
  hidden_size: number;
  num_layers: number;
  input_size: number;
  output_size: number;
}

export interface TurnRecord {
  turn: number;
  player: string;
  observation: number[];
  action: number;
  action_desc: string;
  value: number;
  policy_top_k: { action: number; prob: number }[];
}

export interface Replay {
  id: string;
  agent_batch: string;
  opponents: string[];
  turns: TurnRecord[];
  winner: string;
  rounds: number;
}
