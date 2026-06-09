from pathlib import Path
from scripts.article_export.log_parser import parse_training_log

FIXTURE = Path(__file__).parent / "fixtures" / "training_log_sample.txt"


def test_parse_single_batch():
    batches = parse_training_log(FIXTURE)
    assert len(batches) >= 1
    b = batches[0]
    assert b.id == "v1"
    assert b.stage == 1
    assert b.opponents == ["random"]
    assert b.episodes == 200000
    assert b.result.total_timesteps == 200704
    assert b.result.explained_variance == -0.122
    assert b.result.entropy_loss == -1.81
    assert b.result.value_loss == 0.0431
    assert b.result.clip_fraction == 0.301
    assert len(b.benchmarks) == 1
    bench = b.benchmarks[0]
    assert bench.opponents == ["v1-256x3.zip", "random", "early-capture", "denial"]
    assert bench.win_rates == [0.0, 0.0, 0.415, 0.585]
    assert bench.games == 200
    assert "agent has not yet learned" in b.narrative


def test_parse_multiple_batches():
    batches = parse_training_log(FIXTURE)
    assert [b.id for b in batches] == ["v1", "v3"]
    assert batches[1].stage == 3
    assert batches[1].opponents == ["denial", "high-point"]
    assert batches[1].lr == 0.0001
    assert len(batches[1].benchmarks) == 2
    assert batches[1].benchmarks[1].opponents == ["v3-256x3.zip", "high-point"]
    assert batches[1].benchmarks[1].win_rates == [0.56, 0.44]
