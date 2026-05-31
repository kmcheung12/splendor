# src/pokemon_splendor/agents/high_point.py
from collections import Counter
import numpy as np
from pokemon_splendor.agents.base import RuleBasedAgent
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost


class HighPointCaptureAgent(RuleBasedAgent):
    def _main_action(self, mask: np.ndarray) -> int:
        game = self._game
        player = self._player
        bonuses = get_player_bonuses(player)

        catchable = self._catchable(mask)
        if catchable:
            def ratio(item):
                _, p = item
                ec = calculate_effective_cost(p, bonuses)
                return p.point / max(1, sum(ec.values()))
            return max(catchable, key=ratio)[0]

        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed + game.board.epic_revealed +
            game.board.legendary_revealed
        )
        all_cards = [(i, p) for i, p in enumerate(all_slots) if p is not None]
        if all_cards:
            ptokens = Counter(t.name for t in player.tokens)

            def ratio_to_get(item):
                _, p = item
                ec = calculate_effective_cost(p, bonuses)
                remaining = sum(max(0, cnt - ptokens.get(pt, 0)) for pt, cnt in ec.items())
                rounds = max(1, (remaining + 2) // 3)
                return p.point / rounds

            target = max(all_cards, key=ratio_to_get)[1]
            ec = calculate_effective_cost(target, bonuses)
            needed = Counter({
                pt: max(0, cnt - ptokens.get(pt, 0))
                for pt, cnt in ec.items()
            })
            return self._take_toward(mask, needed)

        return int(np.where(mask)[0][0])
