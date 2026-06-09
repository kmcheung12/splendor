from pathlib import Path
from scripts.article_export.narrative import load_narratives, apply_narratives
from scripts.article_export.models import (
    BatchResult, TrainingMetrics,
)


def test_load_narratives():
    narrs = load_narratives(
        Path("scripts/article_export/narratives/v1-to-v7.yaml")
    )
    assert "v1" in narrs
    assert "buy anything" in narrs["v1"]


def test_apply_narratives_overrides_only_listed():
    batches = [
        BatchResult(
            id="v1", stage=1, opponents=[], episodes=0, lr=0.0,
            result=TrainingMetrics(
                total_timesteps=0, explained_variance=0, entropy_loss=0,
                value_loss=0, clip_fraction=0,
            ),
            benchmarks=[], narrative="original v1",
        ),
        BatchResult(
            id="v2", stage=1, opponents=[], episodes=0, lr=0.0,
            result=TrainingMetrics(
                total_timesteps=0, explained_variance=0, entropy_loss=0,
                value_loss=0, clip_fraction=0,
            ),
            benchmarks=[], narrative="original v2",
        ),
    ]
    apply_narratives(batches, {"v1": "new v1"})
    assert batches[0].narrative == "new v1"
    assert batches[1].narrative == "original v2"
