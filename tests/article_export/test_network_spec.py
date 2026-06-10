import os
import pytest
import tempfile
from pathlib import Path
from scripts.article_export.network_spec import extract_network_spec


@pytest.mark.skipif(
    not os.path.exists("models/v6-256x3.zip"),
    reason="needs real PPO checkpoint",
)
def test_extract_network_spec_from_real_model():
    spec = extract_network_spec(Path("models/v6-256x3.zip"))
    assert spec.hidden_size == 256
    assert spec.num_layers == 3
    assert spec.output_size > 0
    assert spec.input_size > 0


def test_extract_network_spec_writes_json():
    import json
    from scripts.article_export.network_spec import write_network_spec
    if not os.path.exists("models/v6-256x3.zip"):
        pytest.skip("needs real PPO checkpoint")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "network.json"
        write_network_spec(Path("models/v6-256x3.zip"), out)
        data = json.loads(out.read_text())
        assert data["hidden_size"] == 256
        assert data["num_layers"] == 3
