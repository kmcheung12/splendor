# src/pokemon_splendor/agents/bonus_engine.py
from collections import Counter
import numpy as np
from pokemon_splendor.agents.base import RuleBasedAgent
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost

BONUS_THRESHOLD = 5


class BonusEngineAgent(RuleBasedAgent):
    def _main_action(self, mask: np.ndarray) -> int:
        game = self._game
        player = self._player
        bonuses = get_player_bonuses(player)
        total_bonuses = sum(bonuses.values())

        catchable = self._catchable(mask)
        if catchable:
            if total_bonuses < BONUS_THRESHOLD:
                def bonus_count(item):
                    _, p = item
                    return len(p.bonus)
                return max(catchable, key=bonus_count)[0]
            else:
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
            if total_bonuses < BONUS_THRESHOLD:
                def sort_key(item):
                    _, p = item
                    remaining = sum(
                        max(0, cnt - ptokens.get(pt, 0))
                        for pt, cnt in Counter(t.name for t in p.cost).items()
                    )
                    return (len(p.bonus), -remaining)
                target = max(all_cards, key=sort_key)[1]
            else:
                def ratio_to_get(item):
                    _, p = item
                    ec = calculate_effective_cost(p, bonuses)
                    remaining = sum(max(0, cnt - ptokens.get(pt, 0)) for pt, cnt in ec.items())
                    return p.point / max(1, (remaining + 2) // 3)
                target = max(all_cards, key=ratio_to_get)[1]

            ec = calculate_effective_cost(target, bonuses)
            needed = Counter({
                pt: max(0, cnt - ptokens.get(pt, 0))
                for pt, cnt in ec.items()
            })
            return self._take_toward(mask, needed)

        return int(np.where(mask)[0][0])
