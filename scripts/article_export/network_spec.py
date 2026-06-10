from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.agents.rl import SingleAgentEnv
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from scripts.article_export.models import NetworkSpec


def _mask_fn(env):
    return env.action_masks()


def _load_model(model_path: Path) -> MaskablePPO:
    env = ActionMasker(
        SingleAgentEnv(Path("data/pokemon.jsonl"), num_players=2),
        _mask_fn,
    )
    return MaskablePPO.load(model_path, env=env)


def extract_network_spec(model_path: Path) -> NetworkSpec:
    model = _load_model(model_path)
    policy = model.policy
    mlp = policy.mlp_extractor.policy_net
    linears = [m for m in mlp.modules() if m.__class__.__name__ == "Linear"]
    hidden_size = linears[0].out_features
    num_layers = len(linears)
    input_size = linears[0].in_features
    output_size = policy.action_net.out_features
    return NetworkSpec(
        hidden_size=hidden_size,
        num_layers=num_layers,
        input_size=input_size,
        output_size=output_size,
    )


def write_network_spec(model_path: Path, out_path: Path) -> None:
    spec = extract_network_spec(model_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(spec.model_dump_json(indent=2))
