import os
import json
import tempfile
import pytest
from pathlib import Path
from scripts.article_export.replay_recorder import record_replay


@pytest.mark.skipif(
    not os.path.exists("models/v6-256x3.zip"),
    reason="needs real PPO checkpoint",
)
def test_record_replay_writes_valid_json():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "replay.json"
        record_replay(
            agent_model=Path("models/v6-256x3.zip"),
            agent_batch_id="v6",
            opponents=["random"],
            data_path=Path("data/pokemon.jsonl"),
            out_path=out,
            replay_id="test-game",
            seed=42,
        )
        data = json.loads(out.read_text())
        assert data["id"] == "test-game"
        assert data["agent_batch"] == "v6"
        assert data["opponents"] == ["random"]
        assert len(data["turns"]) > 0
        first_turn = data["turns"][0]
        assert "observation" in first_turn
        assert "action" in first_turn
        assert "policy_top_k" in first_turn
        assert len(first_turn["policy_top_k"]) <= 5
        assert data["winner"] in (data["agent_batch"], "random")
