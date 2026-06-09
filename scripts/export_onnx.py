#!/usr/bin/env python
# scripts/export_onnx.py
import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).parent.parent))

import argparse
from pathlib import Path
from scripts.article_export.onnx_export import export_policy_to_onnx


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    export_policy_to_onnx(args.model, args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
