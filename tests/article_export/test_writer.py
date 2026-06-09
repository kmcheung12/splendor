import json
import tempfile
from pathlib import Path
from scripts.article_export.models import (
    BatchResult, BenchmarkResult, TrainingMetrics
)
from scripts.article_export.writer import write_run_outputs


def _make_batch(id_: str, ev: float) -> BatchResult:
    return BatchResult(
        id=id_, stage=1, opponents=["random"],
        episodes=200000, lr=1e-4,
        result=TrainingMetrics(
            total_timesteps=200000, explained_variance=ev,
            entropy_loss=-1.5, value_loss=0.05, clip_fraction=0.3,
        ),
        benchmarks=[BenchmarkResult(
            opponents=["self", "random"],
            win_rates=[0.6, 0.4], games=200,
        )],
        narrative="example",
    )


def test_write_run_outputs():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        batches = [_make_batch("v1", -0.1), _make_batch("v2", 0.2)]
        write_run_outputs(
            out, run_id="r", title="My run",
            batches=batches, set_default=True,
        )
        summary = json.loads((out / "summary.json").read_text())
        assert summary["title"] == "My run"
        assert [b["id"] for b in summary["batches"]] == ["v1", "v2"]
        curves = json.loads((out / "curves.json").read_text())
        assert curves["batches"][1]["explained_variance"] == 0.2
