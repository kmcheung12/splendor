import torch
import torch.nn as nn
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.agents.rl import SingleAgentEnv
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker


def _mask_fn(env):
    return env.action_masks()


class PolicyWrapper(nn.Module):
    """Wraps a MaskablePPO policy to emit policy logits, value, and per-layer activations."""

    def __init__(self, policy):
        super().__init__()
        self.shared = policy.mlp_extractor.policy_net
        self.policy_head = policy.action_net
        self.value_extractor = policy.mlp_extractor.value_net
        self.value_head = policy.value_net

    def forward(self, obs):
        x = obs
        activations = []
        for layer in self.shared:
            x = layer(x)
            if isinstance(layer, nn.Linear):
                activations.append(x.clone())
        policy_logits = self.policy_head(x)
        vx = obs
        for layer in self.value_extractor:
            vx = layer(vx)
        value = self.value_head(vx).squeeze(-1)
        return (policy_logits, value, *activations)


def export_policy_to_onnx(model_path: Path, out_path: Path) -> None:
    env = ActionMasker(
        SingleAgentEnv(Path("data/pokemon.jsonl"), num_players=2),
        _mask_fn,
    )
    model = MaskablePPO.load(model_path, env=env)
    wrapper = PolicyWrapper(model.policy).eval()

    obs_size = model.policy.observation_space.shape[0]
    dummy = torch.zeros(1, obs_size, dtype=torch.float32)

    num_layers = sum(
        1 for m in model.policy.mlp_extractor.policy_net.modules()
        if isinstance(m, nn.Linear)
    )
    activation_names = [f"hidden_{i}" for i in range(num_layers)]
    output_names = ["policy_logits", "value", *activation_names]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        wrapper,
        dummy,
        str(out_path),
        input_names=["observation"],
        output_names=output_names,
        dynamic_axes={"observation": {0: "batch"}},
        opset_version=17,
    )
