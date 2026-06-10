import os
import json
import tempfile
import pytest
from pathlib import Path
from scripts.article_export.replay_recorder import record_replay_with_snapshots


@pytest.mark.skipif(
    not os.path.exists("models/v6-256x3.zip"),
    reason="needs real PPO checkpoint",
)
def test_record_replay_emits_snapshots():
    with tempfile.TemporaryDirectory() as tmp:
        snap_out = Path(tmp) / "snapshots.json"
        record_replay_with_snapshots(
            agent_model=Path("models/v6-256x3.zip"),
            agent_batch_id="v6",
            opponents=["random"],
            data_path=Path("data/pokemon.jsonl"),
            replay_out=Path(tmp) / "replay.json",
            snapshot_out=snap_out,
            replay_id="test-game",
            seed=42,
        )
        data = json.loads(snap_out.read_text())
        assert "initial" in data
        assert "turns" in data
        assert len(data["turns"]) > 0
        first = data["turns"][0]
        assert "snapshot" in first
        assert "active_player" in first["snapshot"]
