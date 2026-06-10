from pydantic import BaseModel


class TrainingMetrics(BaseModel):
    total_timesteps: int
    explained_variance: float
    entropy_loss: float
    value_loss: float
    clip_fraction: float


class BenchmarkResult(BaseModel):
    opponents: list[str]
    win_rates: list[float]
    games: int


class BatchResult(BaseModel):
    id: str
    stage: int
    opponents: list[str]
    episodes: int
    lr: float
    result: TrainingMetrics
    benchmarks: list[BenchmarkResult]
    narrative: str


class RunSummary(BaseModel):
    title: str
    batches: list[BatchResult]


class RunIndexEntry(BaseModel):
    id: str
    title: str
    default: bool = False


class RunIndex(BaseModel):
    runs: list[RunIndexEntry]


class CurvesPerBatch(BaseModel):
    id: str
    total_timesteps: int
    explained_variance: float
    entropy_loss: float
    value_loss: float


class Curves(BaseModel):
    batches: list[CurvesPerBatch]


class NetworkSpec(BaseModel):
    hidden_size: int
    num_layers: int
    input_size: int
    output_size: int


class TurnRecord(BaseModel):
    turn: int
    player: str
    observation: list[float]
    action: int
    action_desc: str
    value: float
    policy_top_k: list[dict]


class Replay(BaseModel):
    id: str
    agent_batch: str
    opponents: list[str]
    turns: list[TurnRecord]
    winner: str
    rounds: int
