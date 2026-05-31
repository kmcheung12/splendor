# src/pokemon_splendor/agents/denial.py
from collections import Counter
import numpy as np
from pokemon_splendor.agents.base import RuleBasedAgent
from pokemon_splendor.models import Player, Pokemon, Game
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost
from pokemon_splendor.engine.actions import RESERVE_MASTER_START, RESERVE_NO_MASTER_START


class DenialAgent(RuleBasedAgent):
    def _rounds_to_catch(self, opp: Player, pokemon: Pokemon, game: Game) -> int:
        bonuses = get_player_bonuses(opp)
        ec = calculate_effective_cost(pokemon, bonuses)
        ptokens = Counter(t.name for t in opp.tokens)
        shortfall = sum(max(0, cnt - ptokens.get(pt, 0)) for pt, cnt in ec.items())
        return (shortfall + 2) // 3

    def _main_action(self, mask: np.ndarray) -> int:
        game = self._game
        player = self._player
        bonuses = get_player_bonuses(player)
        opponents = [p for p in game.players if p.name != player.name]

        reservable = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed
        )

        # Find the card an opponent can catch soonest
        denial_slot, min_rounds = None, float("inf")
        for slot_idx, pokemon in enumerate(reservable):
            if pokemon is None:
                continue
            for opp in opponents:
                r = self._rounds_to_catch(opp, pokemon, game)
                if r < min_rounds:
                    min_rounds = r
                    denial_slot = slot_idx

        if denial_slot is not None:
            reserve_master = RESERVE_MASTER_START + denial_slot
            reserve_no_master = RESERVE_NO_MASTER_START + denial_slot
            if mask[reserve_master]:
                return reserve_master
            if mask[reserve_no_master]:
                return reserve_no_master

        # Fallback: catch or take tokens toward highest-ratio card
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
                return p.point / max(1, (remaining + 2) // 3)

            target = max(all_cards, key=ratio_to_get)[1]
            ec = calculate_effective_cost(target, bonuses)
            needed = Counter({
                pt: max(0, cnt - ptokens.get(pt, 0))
                for pt, cnt in ec.items()
            })
            return self._take_toward(mask, needed)

        return int(np.where(mask)[0][0])
