# src/pokemon_splendor/agents/rl.py
import numpy as np
import gymnasium
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv


class SingleAgentEnv(gymnasium.Env):
    """Gymnasium wrapper for player_0 training against random opponents."""

    def __init__(self, jsonl_path: Path, num_players: int = 2):
        self._pz = PokemonSplendorEnv(jsonl_path, num_players=num_players)
        self.observation_space = self._pz.observation_spaces["player_0"]
        self.action_space = self._pz.action_spaces["player_0"]

    def reset(self, seed=None, options=None):
        self._pz.reset(seed=seed)
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
            agent = self._pz.agent_selection
            mask = self._pz.action_mask(agent)
            valid = np.where(mask)[0]
            self._pz.step(int(np.random.choice(valid)))


class RLAgent:
    def __init__(self, model_path: str):
        from sb3_contrib import MaskablePPO
        self.model = MaskablePPO.load(model_path)

    def act(self, obs: np.ndarray, mask: np.ndarray) -> int:
        action, _ = self.model.predict(obs, action_masks=mask, deterministic=True)
        return int(action)
