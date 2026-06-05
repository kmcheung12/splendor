# src/pokemon_splendor/agents/mcts.py
import copy
import math
import pickle
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from pokemon_splendor.models import Game, Player, GamePhase, PokeballType, Tier
from pokemon_splendor.engine.eval import evaluate_position
from pokemon_splendor.engine.simulator import _step_inplace
from pokemon_splendor.engine.observation import compute_mask
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost, get_evolvable_cards
from pokemon_splendor.engine.actions import (
    TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START, DISCARD_START,
    EVOLVE_START, EVOLVE_PASS, DISCARD_ACTION, TAKE_SAME_ACTION,
)
from pokemon_splendor.agents.base import RuleBasedAgent

_C = math.sqrt(2)

OpponentPolicy = Callable[[Game, str], int]


def _clone(game: Game) -> Game:
    return pickle.loads(pickle.dumps(game, protocol=5))


@dataclass
class MCTSNode:
    game: Game
    parent: "MCTSNode | None"
    action: int | None
    depth: int = 0
    visits: int = 0
    total_value: float = 0.0
    children: dict[int, "MCTSNode"] = field(default_factory=dict)
    untried_actions: list[int] = field(default_factory=list)


class MCTSAgent(RuleBasedAgent):
    def __init__(self, env, player_name: str, n_simulations: int = 200,
                 depth: int = 4, opponent_policy: OpponentPolicy | None = None):
        super().__init__(env, player_name)
        self._n_simulations = n_simulations
        self._depth = depth
        self._opponent_policy = opponent_policy or make_early_capture_policy()

    def act(self, obs: np.ndarray, mask: np.ndarray) -> int:
        game = _clone(self._game)
        player = next(p for p in game.players if p.name == self._player_name)

        if game.phase == GamePhase.DISCARD:
            return self._best_discard_action(game, player, mask)

        pruned = self._prune_actions(game, player)
        if not pruned:
            return int(np.where(mask)[0][0])

        root = MCTSNode(
            game=game, parent=None, action=None, depth=0,
            untried_actions=list(pruned),
        )
        for _ in range(self._n_simulations):
            self._simulate(root)

        if not root.children:
            return pruned[0]
        return max(root.children.values(), key=lambda c: c.visits).action

    # ------------------------------------------------------------------
    # MCTS core
    # ------------------------------------------------------------------

    def _simulate(self, root: MCTSNode) -> None:
        node = self._select(root)
        if node.untried_actions and not self._is_terminal(node):
            node = self._expand(node)
        value = self._evaluate(node)
        self._backpropagate(node, value)

    def _select(self, node: MCTSNode) -> MCTSNode:
        while (not node.untried_actions and node.children
               and not self._is_terminal(node)):
            node = max(node.children.values(),
                       key=lambda c: self._ucb(c, node))
        return node

    def _ucb(self, node: MCTSNode, parent: MCTSNode) -> float:
        if node.visits == 0:
            return float("inf")
        return (node.total_value / node.visits
                + _C * math.sqrt(math.log(parent.visits) / node.visits))

    def _expand(self, node: MCTSNode) -> MCTSNode:
        action = node.untried_actions.pop()
        game = _clone(node.game)
        is_terminal = _step_inplace(game, action, self._player_name)

        # Handle forced discard for the MCTS agent
        while (not is_terminal
               and game.turn.name == self._player_name
               and game.phase == GamePhase.DISCARD):
            player = next(p for p in game.players if p.name == self._player_name)
            discard_mask = compute_mask(game, self._player_name)
            d_action = self._best_discard_action(game, player, discard_mask)
            is_terminal = _step_inplace(game, d_action, self._player_name)

        # Advance all opponents
        while not is_terminal and game.turn.name != self._player_name:
            opp_name = game.turn.name
            opp_action = self._opponent_policy(game, opp_name)
            is_terminal = _step_inplace(game, opp_action, opp_name)

        our_player = next(p for p in game.players if p.name == self._player_name)
        untried = ([] if is_terminal or node.depth + 1 >= self._depth
                   else self._prune_actions(game, our_player))

        child = MCTSNode(
            game=game, parent=node, action=action,
            depth=node.depth + 1, untried_actions=untried,
        )
        node.children[action] = child
        return child

    def _evaluate(self, node: MCTSNode) -> float:
        if self._is_terminal(node):
            if node.game.winner is None:
                player = next(p for p in node.game.players if p.name == self._player_name)
                return evaluate_position(node.game, player)
            return 1.0 if node.game.winner.name == self._player_name else 0.0
        player = next(p for p in node.game.players if p.name == self._player_name)
        return evaluate_position(node.game, player)

    def _backpropagate(self, node: MCTSNode, value: float) -> None:
        while node is not None:
            node.visits += 1
            node.total_value += value
            node = node.parent

    def _is_terminal(self, node: MCTSNode) -> bool:
        return node.game.winner is not None

    # ------------------------------------------------------------------
    # Action pruning
    # ------------------------------------------------------------------

    def _prune_actions(self, game: Game, player: Player) -> list[int]:
        mask = compute_mask(game, player.name)

        if game.phase == GamePhase.EVOLVE:
            actions = [a for a in range(EVOLVE_START, EVOLVE_PASS) if mask[a]]
            if mask[EVOLVE_PASS]:
                actions.append(EVOLVE_PASS)
            return actions

        actions: list[int] = []

        # Token-taking: 3-token TAKE_DIFF only
        for i, combo in enumerate(TAKE_DIFF_COMBOS):
            if len(combo) == 3:
                a = TAKE_DIFF_START + i
                if mask[a]:
                    actions.append(a)

        # TAKE_SAME: all valid
        for a in range(TAKE_SAME_START, CATCH_BOARD_START):
            if mask[a]:
                actions.append(a)

        # Catch: all valid
        for a in range(CATCH_BOARD_START, RESERVE_MASTER_START):
            if mask[a]:
                actions.append(a)

        # Reserve: hard filters + top-5 scoring
        actions.extend(self._pruned_reserve_actions(game, player, mask))

        return actions if actions else list(np.where(mask)[0])

    def _pruned_reserve_actions(self, game: Game, player: Player,
                                 mask: np.ndarray) -> list[int]:
        # Hard filter: winning catch available
        all_board_slots = (
            game.board.common_revealed + game.board.uncommon_revealed
            + game.board.rare_revealed + game.board.epic_revealed
            + game.board.legendary_revealed
        )
        for slot_idx, card in enumerate(all_board_slots):
            if mask[CATCH_BOARD_START + slot_idx] and card is not None:
                if player.points + card.point >= 18:
                    return []
        for i, card in enumerate(player.reserved_cards):
            if mask[CATCH_RESERVED_START + i]:
                if player.points + card.point >= 18:
                    return []

        # Hard filter: already holds 2+ reserved cards
        if len(player.reserved_cards) >= 2:
            return []

        reservable = (
            game.board.common_revealed + game.board.uncommon_revealed
            + game.board.rare_revealed
        )
        candidates: list[tuple[float, int]] = []
        for slot_idx, card in enumerate(reservable):
            if card is None:
                continue
            # Hard filter: common, 0 points, no bonus
            if card.tier == Tier.Common and card.point == 0 and not card.bonus:
                continue
            # Prefer RESERVE_MASTER when available (board has master tokens)
            if mask[RESERVE_MASTER_START + slot_idx]:
                action = RESERVE_MASTER_START + slot_idx
            elif mask[RESERVE_NO_MASTER_START + slot_idx]:
                action = RESERVE_NO_MASTER_START + slot_idx
            else:
                continue
            score = self._reserve_score(game, player, card)
            candidates.append((score, action))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [action for _, action in candidates[:5]]

    def _reserve_score(self, game: Game, player: Player, card) -> float:
        bonuses = get_player_bonuses(player)
        ptokens = Counter(t.name for t in player.tokens)
        ec = calculate_effective_cost(card, bonuses)
        my_shortfall = sum(
            max(0, ec.get(pt, 0) - ptokens.get(pt, 0))
            for pt in PokeballType if pt != PokeballType.Master
        )
        my_rounds = (my_shortfall + 2) // 3

        opponents = [p for p in game.players if p is not player]
        min_opp_rounds = 999
        for opp in opponents:
            opp_bonuses = get_player_bonuses(opp)
            opp_ec = calculate_effective_cost(card, opp_bonuses)
            opp_ptokens = Counter(t.name for t in opp.tokens)
            opp_shortfall = sum(
                max(0, opp_ec.get(pt, 0) - opp_ptokens.get(pt, 0))
                for pt in PokeballType if pt != PokeballType.Master
            )
            min_opp_rounds = min(min_opp_rounds, (opp_shortfall + 2) // 3)

        return float(card.point + min_opp_rounds - my_rounds)

    def _best_discard_action(self, game: Game, player: Player,
                              mask: np.ndarray) -> int:
        """Discard the token that increases total shortfall the least."""
        bonuses = get_player_bonuses(player)
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed
            + game.board.rare_revealed + game.board.epic_revealed
            + game.board.legendary_revealed
        )
        tc = Counter(t.name for t in player.tokens)
        best_action, best_score = None, float("inf")
        for ptype, idx in DISCARD_ACTION.items():
            if not mask[idx]:
                continue
            if ptype == PokeballType.Master:
                score = 1000.0
            else:
                temp = Counter(tc)
                temp[ptype] -= 1
                score = sum(
                    max(0, calculate_effective_cost(card, bonuses).get(pt, 0) - temp.get(pt, 0))
                    for card in all_slots if card is not None
                    for pt in PokeballType if pt != PokeballType.Master
                )
            if score < best_score:
                best_score = score
                best_action = idx
        return best_action if best_action is not None else int(np.where(mask)[0][0])


# ------------------------------------------------------------------
# Opponent policy factories
# ------------------------------------------------------------------

def make_early_capture_policy() -> OpponentPolicy:
    """Standalone early-capture policy: catch cheapest, else take tokens toward cheapest."""
    from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost, can_afford, get_evolvable_cards

    def policy(game: Game, player_name: str) -> int:
        player = next(p for p in game.players if p.name == player_name)
        bonuses = get_player_bonuses(player)
        ptokens = Counter(t.name for t in player.tokens)

        if game.phase == GamePhase.DISCARD:
            best_action, best_count = None, -1
            for ptype, idx in DISCARD_ACTION.items():
                if ptype == PokeballType.Master:
                    continue
                count = ptokens.get(ptype, 0)
                if count > best_count:
                    best_count = count
                    best_action = idx
            return best_action if best_action is not None else EVOLVE_PASS

        if game.phase == GamePhase.EVOLVE:
            evolvable = get_evolvable_cards(game, player)
            if evolvable:
                return EVOLVE_START + player.cards.index(evolvable[0][0])
            return EVOLVE_PASS

        # MAIN: catch cheapest affordable
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed
            + game.board.rare_revealed + game.board.epic_revealed
            + game.board.legendary_revealed
        )
        catchable = []
        for slot_idx, card in enumerate(all_slots):
            if card is not None and can_afford(card, bonuses, ptokens):
                catchable.append((CATCH_BOARD_START + slot_idx, card))
        for i, card in enumerate(player.reserved_cards):
            if can_afford(card, bonuses, ptokens):
                catchable.append((CATCH_RESERVED_START + i, card))

        if catchable:
            return min(catchable,
                       key=lambda item: sum(calculate_effective_cost(item[1], bonuses).values())
                       )[0]

        # Take tokens toward cheapest card
        all_cards = [(i, c) for i, c in enumerate(all_slots) if c is not None]
        available_types = {pt for pt in NORMAL_TYPES if game.tokens.get(pt, 0) > 0}
        if all_cards:
            target = min(all_cards, key=lambda item: sum(
                max(0, cnt - ptokens.get(pt, 0))
                for pt, cnt in calculate_effective_cost(item[1], bonuses).items()
            ))[1]
            ec = calculate_effective_cost(target, bonuses)
            needed = Counter({pt: max(0, cnt - ptokens.get(pt, 0))
                              for pt, cnt in ec.items()})
            best_action, best_score = None, -1
            for i, combo in enumerate(TAKE_DIFF_COMBOS):
                if not all(pt in available_types for pt in combo):
                    continue
                score = sum(min(needed.get(pt, 0), 1) for pt in combo)
                if score > best_score:
                    best_score = score
                    best_action = TAKE_DIFF_START + i
            for pt in NORMAL_TYPES:
                if game.tokens.get(pt, 0) >= 4 and needed.get(pt, 0) >= 2 and 2 > best_score:
                    best_score = 2
                    best_action = TAKE_SAME_ACTION[pt]
            if best_action is not None:
                return best_action

        # Fallback: DISCARD in MAIN phase (no normal actions available)
        for ptype, idx in DISCARD_ACTION.items():
            if ptype != PokeballType.Master and ptokens.get(ptype, 0) > 0:
                return idx

        return int(np.where(mask)[0][0])

    return policy


def make_rl_policy(model_path: str) -> OpponentPolicy:
    """Load a MaskablePPO model and return it as an opponent policy callable."""
    from sb3_contrib import MaskablePPO
    from pokemon_splendor.engine.observation import compute_observation
    model = MaskablePPO.load(model_path)

    def policy(game: Game, player_name: str) -> int:
        obs = compute_observation(game, player_name)
        mask = compute_mask(game, player_name)
        action, _ = model.predict(obs, action_masks=mask, deterministic=True)
        return int(action)

    return policy
