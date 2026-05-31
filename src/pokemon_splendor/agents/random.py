# src/pokemon_splendor/agents/random.py
import numpy as np


class RandomAgent:
    def act(self, obs: np.ndarray, mask: np.ndarray) -> int:
        return int(np.random.choice(np.where(mask)[0]))
