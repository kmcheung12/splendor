# Pokemon Splendor — Training Explainer

A standalone Svelte article that explains how the Splendor agent was trained.

## Develop

```bash
npm install
npm run dev:article
```

Serves at http://localhost:5174

## Build

```bash
npm run build:article
npm run check-bundle
```

Output: `dist-article/`

## Regenerate data

From repo root:

```bash
uv run python scripts/export_article_data.py \
  --run-id v1-to-v7 --title "First curriculum" \
  --log training_log.txt \
  --narratives scripts/article_export/narratives/v1-to-v7.yaml \
  --out frontend/article/data/runs/ --default

for v in v1 v3 v6; do
  uv run python scripts/record_replay.py \
    --model models/${v}-256x3.zip --batch-id ${v} \
    --opponents random,early-capture,denial \
    --replay-out frontend/article/data/runs/v1-to-v7/replays/${v}-seed42.json \
    --snapshot-out frontend/article/data/runs/v1-to-v7/snapshots/${v}-seed42.json \
    --id ${v}-seed42 --seed 42
done

uv run python scripts/export_onnx.py \
  --model models/v6-256x3.zip \
  --out frontend/article/data/runs/v1-to-v7/network.onnx
```

## Architecture

See `docs/superpowers/specs/2026-06-09-training-explainer-design.md`.
