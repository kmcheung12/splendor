import json
from pathlib import Path
from scripts.article_export.models import (
    BatchResult, Curves, CurvesPerBatch, RunIndex, RunIndexEntry, RunSummary,
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


def write_run_index(
    runs_dir: Path, run_id: str, title: str, set_default: bool
) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    index_path = runs_dir / "index.json"
    if index_path.exists():
        index = RunIndex.model_validate_json(index_path.read_text())
    else:
        index = RunIndex(runs=[])
    entries = [e for e in index.runs if e.id != run_id]
    if set_default:
        for e in entries:
            e.default = False
    entries.append(RunIndexEntry(id=run_id, title=title, default=set_default))
    index = RunIndex(runs=entries)
    index_path.write_text(index.model_dump_json(indent=2))
