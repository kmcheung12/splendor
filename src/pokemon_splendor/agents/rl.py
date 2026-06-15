# src/pokemon_splendor/agents/rl.py
import numpy as np
import gymnasium
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv


def _make_opponent(agent_type: str, pz_env, player_name: str):
    if agent_type == "random":
        return None  # None = random, handled inline in _play_others
    if agent_type == "mcts" or agent_type.startswith("mcts:"):
        from pokemon_splendor.agents.mcts import MCTSAgent, make_early_capture_policy, make_rl_policy
        parts = agent_type.split(":")
        sims = int(parts[1]) if len(parts) > 1 else 50
        depth = int(parts[2]) if len(parts) > 2 else 2
        opp_model = parts[3] if len(parts) > 3 else None
        opp_policy = make_rl_policy(opp_model) if opp_model else make_early_capture_policy()
        return MCTSAgent(pz_env, player_name, n_simulations=sims, depth=depth,
                         opponent_policy=opp_policy)
    if agent_type.endswith(".zip"):
        return RLAgent(agent_type)
    if agent_type == "early-capture":
        from pokemon_splendor.agents.early_capture import EarlyCaptureAgent
        return EarlyCaptureAgent(pz_env, player_name)
    if agent_type == "high-point":
        from pokemon_splendor.agents.high_point import HighPointCaptureAgent
        return HighPointCaptureAgent(pz_env, player_name)
    if agent_type == "bonus-engine":
        from pokemon_splendor.agents.bonus_engine import BonusEngineAgent
        return BonusEngineAgent(pz_env, player_name)
    if agent_type == "evolution-chain":
        from pokemon_splendor.agents.evolution_chain import EvolutionChainAgent
        return EvolutionChainAgent(pz_env, player_name)
    if agent_type == "denial":
        from pokemon_splendor.agents.denial import DenialAgent
        return DenialAgent(pz_env, player_name)
    raise ValueError(f"Unknown opponent type: {agent_type}")


class SingleAgentEnv(gymnasium.Env):
    """Gymnasium wrapper: player_0 trains against configurable opponents."""

    def __init__(self, jsonl_path: Path, num_players: int = 2, opponent_types: list[str] | None = None,
                 obs_fn=None, obs_size: int | None = None):
        assert num_players >= 2
        self._jsonl_path = jsonl_path
        self._num_players = num_players
        self._opponent_types = opponent_types or ["random"] * (num_players - 1)
        assert len(self._opponent_types) == num_players - 1

        self._pz = PokemonSplendorEnv(jsonl_path, num_players=num_players,
                                      obs_fn=obs_fn, obs_size=obs_size)
        self.observation_space = self._pz.observation_spaces["player_0"]
        self.action_space = self._pz.action_spaces["player_0"]
        self._opponents: dict = {}

    def reset(self, seed=None, options=None):
        self._pz.reset(seed=seed)
        self._opponents = {
            f"player_{i+1}": _make_opponent(t, self._pz, f"player_{i+1}")
            for i, t in enumerate(self._opponent_types)
        }
        self._play_others()
        obs, _, _, _, info = self._pz.last()
        return obs, info

    def step(self, action: int):
        self._pz.step(action)
        self._play_others()
        obs, reward, term, trunc, info = self._pz.last()
        return obs, reward, term, trunc, info

    def action_masks(self) -> np.ndarray:
        return self._pz.action_mask("player_0")

    def _play_others(self):
        while self._pz.agents and self._pz.agent_selection != "player_0":
            name = self._pz.agent_selection
            mask = self._pz.action_mask(name)
            opp = self._opponents.get(name)
            if opp is None:
                action = int(np.random.choice(np.where(mask)[0]))
            else:
                obs, _, _, _, _ = self._pz.last()
                action = opp.act(obs, mask)
            self._pz.step(action)


class RLAgent:
    def __init__(self, model_path: str):
        from sb3_contrib import MaskablePPO
        from pokemon_splendor.engine.observation import get_obs_fn
        self.model = MaskablePPO.load(model_path)
        self._obs_fn = get_obs_fn(self.model)

    def act(self, obs: np.ndarray, mask: np.ndarray) -> int:
        action, _ = self.model.predict(obs, action_masks=mask, deterministic=True)
        return int(action)
