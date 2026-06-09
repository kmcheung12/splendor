#!/usr/bin/env python
# scripts/export_article_data.py
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).parent.parent))

import argparse
from pathlib import Path
from scripts.article_export.log_parser import parse_training_log
from scripts.article_export.narrative import apply_narratives, load_narratives
from scripts.article_export.network_spec import write_network_spec
from scripts.article_export.writer import write_run_index, write_run_outputs


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--models-dir", type=Path, default=Path("models"))
    p.add_argument("--network-from", default=None,
                   help="Batch id to extract network.json from (default: last batch)")
    p.add_argument("--narratives", type=Path, default=None)
    p.add_argument("--out", type=Path, required=True,
                   help="frontend/article/data/runs/")
    p.add_argument("--default", action="store_true",
                   help="Mark this run as the default in index.json")
    args = p.parse_args()

    batches = parse_training_log(args.log)
    if args.narratives:
        apply_narratives(batches, load_narratives(args.narratives))

    run_out = args.out / args.run_id
    write_run_outputs(
        run_out, run_id=args.run_id, title=args.title,
        batches=batches, set_default=args.default,
    )
    write_run_index(
        args.out, run_id=args.run_id,
        title=args.title, set_default=args.default,
    )

    network_batch = args.network_from or batches[-1].id
    model_path = args.models_dir / f"{network_batch}-256x3.zip"
    if model_path.exists():
        write_network_spec(model_path, run_out / "network.json")

    print(f"Wrote {run_out}")


if __name__ == "__main__":
    main()
