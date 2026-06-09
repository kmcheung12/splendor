import os
import tempfile
import numpy as np
import pytest
from pathlib import Path
from scripts.article_export.onnx_export import export_policy_to_onnx


@pytest.mark.skipif(
    not os.path.exists("models/v6-256x3.zip"),
    reason="needs real PPO checkpoint",
)
def test_onnx_export_roundtrip():
    import onnxruntime as ort
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "network.onnx"
        export_policy_to_onnx(Path("models/v6-256x3.zip"), out)
        assert out.exists()
        sess = ort.InferenceSession(str(out))
        input_meta = sess.get_inputs()[0]
        # shape may contain dynamic-axis strings; substitute 1 for any non-int dim
        concrete_shape = [d if isinstance(d, int) else 1 for d in input_meta.shape]
        obs = np.zeros(concrete_shape, dtype=np.float32)
        outputs = sess.run(None, {input_meta.name: obs})
        # Expect: policy_logits, value, then hidden activations
        assert len(outputs) >= 2
