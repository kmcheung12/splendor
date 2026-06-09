#!/usr/bin/env python
# scripts/record_replay.py
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).parent.parent))

import argparse
from pathlib import Path
from scripts.article_export.replay_recorder import record_replay


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--batch-id", required=True)
    p.add_argument("--opponents", required=True, help="comma-separated")
    p.add_argument("--data", type=Path, default=Path("data/pokemon.jsonl"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--id", required=True, help="Replay identifier")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()

    opponents = [o.strip() for o in args.opponents.split(",")]
    record_replay(
        agent_model=args.model,
        agent_batch_id=args.batch_id,
        opponents=opponents,
        data_path=args.data,
        out_path=args.out,
        replay_id=args.id,
        seed=args.seed,
    )
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
