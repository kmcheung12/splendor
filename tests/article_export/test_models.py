from scripts.article_export.models import BatchResult, BenchmarkResult, TrainingMetrics


def test_batch_result_roundtrip():
    batch = BatchResult(
        id="v1",
        stage=1,
        opponents=["random"],
        episodes=200000,
        lr=1e-4,
        result=TrainingMetrics(
            total_timesteps=200000,
            explained_variance=-0.12,
            entropy_loss=-1.8,
            value_loss=0.04,
            clip_fraction=0.3,
        ),
        benchmarks=[
            BenchmarkResult(
                opponents=["v1", "random", "early-capture", "denial"],
                win_rates=[0.0, 0.0, 0.42, 0.58],
                games=200,
            )
        ],
        narrative="Pure random opponent.",
    )
    js = batch.model_dump_json()
    parsed = BatchResult.model_validate_json(js)
    assert parsed == batch


def test_benchmark_result_validates_win_rate_sum():
    bench = BenchmarkResult(
        opponents=["a", "b"], win_rates=[0.6, 0.4], games=100
    )
    assert bench.opponents == ["a", "b"]
