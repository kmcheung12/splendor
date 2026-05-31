# src/pokemon_splendor/agents/evolution_chain.py
from collections import Counter
import numpy as np
from pokemon_splendor.agents.base import RuleBasedAgent
from pokemon_splendor.models import Game, Pokemon
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost


class EvolutionChainAgent(RuleBasedAgent):
    def _chain_value(self, pokemon: Pokemon, game: Game, depth: int = 0) -> int:
        if depth > 4:
            return pokemon.point
        total = pokemon.point
        if not pokemon.evolve_into:
            return total
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed + game.board.epic_revealed +
            game.board.legendary_revealed
        )
        for p in all_slots:
            if p and p.name == pokemon.evolve_into:
                total += self._chain_value(p, game, depth + 1)
                break
        return total

    def _main_action(self, mask: np.ndarray) -> int:
        game = self._game
        player = self._player
        bonuses = get_player_bonuses(player)

        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed + game.board.epic_revealed +
            game.board.legendary_revealed
        )
        chain_scores = {
            i: self._chain_value(p, game)
            for i, p in enumerate(all_slots)
            if p is not None
        }

        catchable = self._catchable(mask)
        if catchable:
            def score(item):
                action, p = item
                slot_idx = action - 30 if 30 <= action < 44 else None
                return chain_scores.get(slot_idx, p.point) if slot_idx is not None else p.point
            return max(catchable, key=score)[0]

        if chain_scores:
            target_slot = max(chain_scores, key=chain_scores.get)
            target = all_slots[target_slot]
            ec = calculate_effective_cost(target, bonuses)
            ptokens = Counter(t.name for t in player.tokens)
            needed = Counter({
                pt: max(0, cnt - ptokens.get(pt, 0))
                for pt, cnt in ec.items()
            })
            return self._take_toward(mask, needed)

        return int(np.where(mask)[0][0])
