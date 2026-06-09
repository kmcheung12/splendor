from pathlib import Path
from scripts.article_export.models import (
    BatchResult, Curves, CurvesPerBatch, RunSummary,
)


def write_run_outputs(
    out_dir: Path,
    run_id: str,
    title: str,
    batches: list[BatchResult],
    set_default: bool,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = RunSummary(title=title, batches=batches)
    (out_dir / "summary.json").write_text(summary.model_dump_json(indent=2))

    curves = Curves(batches=[
        CurvesPerBatch(
            id=b.id,
            total_timesteps=b.result.total_timesteps,
            explained_variance=b.result.explained_variance,
            entropy_loss=b.result.entropy_loss,
            value_loss=b.result.value_loss,
        )
        for b in batches
    ])
    (out_dir / "curves.json").write_text(curves.model_dump_json(indent=2))
