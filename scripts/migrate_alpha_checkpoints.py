#!/usr/bin/env python3
"""
One-time migration: rewrite all .pt checkpoint files to embed architecture metadata.

Before: torch.save(state_dict, path)          — raw OrderedDict of weights
After:  torch.save({                           — dict with metadata
            "state_dict": state_dict,
            "hidden_size": 256,
            "num_layers": 2,
        }, path)

Run once after alpha training completes, before upgrading AlphaNet defaults.
"""
import sys
import torch
from pathlib import Path


def infer_architecture(state_dict: dict) -> tuple[int, int]:
    # Count Linear layers in shared trunk by looking for shared.N.weight keys
    layer_indices = set()
    for key in state_dict:
        if key.startswith("shared.") and key.endswith(".weight"):
            parts = key.split(".")
            # shared.0.weight, shared.2.weight, ... (ReLU has no weights, so step=2)
            layer_indices.add(int(parts[1]))
    num_layers = len(layer_indices)
    # hidden_size is the output dim of the first shared layer
    hidden_size = state_dict["shared.0.weight"].shape[0]
    return hidden_size, num_layers


def migrate(checkpoint_dir: Path, dry_run: bool = False) -> None:
    pts = sorted(checkpoint_dir.glob("*.pt"))
    if not pts:
        print(f"No .pt files found in {checkpoint_dir}")
        return

    print(f"Found {len(pts)} checkpoint(s) in {checkpoint_dir}")
    for path in pts:
        data = torch.load(path, map_location="cpu", weights_only=True)

        if isinstance(data, dict) and "state_dict" in data:
            print(f"  {path.name} — already migrated, skipping")
            continue

        hidden_size, num_layers = infer_architecture(data)
        new_data = {
            "state_dict": data,
            "hidden_size": hidden_size,
            "num_layers": num_layers,
        }
        print(f"  {path.name} — hidden_size={hidden_size} num_layers={num_layers}", end="")
        if dry_run:
            print(" [dry run, not saved]")
        else:
            torch.save(new_data, path)
            print(" — saved")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate AlphaNet checkpoints to embed architecture metadata")
    parser.add_argument("checkpoint_dir", nargs="?", default="alpha_checkpoints",
                        help="Directory containing .pt files (default: alpha_checkpoints)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done without writing files")
    args = parser.parse_args()

    migrate(Path(args.checkpoint_dir), dry_run=args.dry_run)
