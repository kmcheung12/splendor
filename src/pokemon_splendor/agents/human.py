# src/pokemon_splendor/agents/human.py
import numpy as np
from pokemon_splendor.agents.base import RuleBasedAgent, describe_action
from pokemon_splendor.cli.renderer import render


class HumanAgent(RuleBasedAgent):
    def act(self, obs: np.ndarray, mask: np.ndarray) -> int:
        game = self._game
        player = self._player
        render(game)
        valid = [(i, describe_action(i, game, player)) for i in np.where(mask)[0]]
        print("\nValid actions:")
        for seq, (action_id, desc) in enumerate(valid):
            print(f"  [{seq}] {desc}")
        while True:
            try:
                choice = int(input("Enter action number: "))
                if 0 <= choice < len(valid):
                    return valid[choice][0]
                print(f"Enter 0-{len(valid) - 1}")
            except ValueError:
                print("Enter a number")
