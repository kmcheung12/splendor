# src/pokemon_splendor/agents/alpha_mcts.py
import math
import pickle
import torch
import numpy as np
from collections import Counter
from dataclasses import dataclass, field
from pokemon_splendor.models import Game, GamePhase, PokeballType
from pokemon_splendor.engine.simulator import _step_inplace
from pokemon_splendor.engine.observation import compute_mask, compute_observation
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost
from pokemon_splendor.engine.actions import TOTAL_ACTIONS, DISCARD_ACTION
from pokemon_splendor.agents.base import RuleBasedAgent
from pokemon_splendor.agents.alpha_net import AlphaNet

_C = math.sqrt(2)


def _clone(game: Game) -> Game:
    return pickle.loads(pickle.dumps(game, protocol=5))


@dataclass
class AlphaMCTSNode:
    game: Game
    parent: "AlphaMCTSNode | None"
    action: int | None
    prior: float = 0.0
    depth: int = 0
    visits: int = 0
    total_value: float = 0.0
    children: dict[int, "AlphaMCTSNode"] = field(default_factory=dict)
    untried_actions: list[int] = field(default_factory=list)


class AlphaMCTSAgent(RuleBasedAgent):
    def __init__(self, env, player_name: str, network: AlphaNet,
                 n_simulations: int = 100, depth: int = 4):
        super().__init__(env, player_name)
        self._network = network
        self._n_simulations = n_simulations
        self._depth = depth

    def act(self, obs: np.ndarray, mask: np.ndarray) -> tuple[int, list[float]]:
        game = _clone(self._game)

        if game.phase == GamePhase.DISCARD:
            action = self._best_discard_action(game, mask)
            visit_counts = [0.0] * TOTAL_ACTIONS
            visit_counts[action] = 1.0
            return action, visit_counts

        valid_actions = list(np.where(mask)[0])

        root = AlphaMCTSNode(
            game=game, parent=None, action=None, depth=0,
            untried_actions=list(valid_actions),
        )
        for _ in range(self._n_simulations):
            self._simulate(root)

        if not root.children:
            action = valid_actions[0]
            visit_counts = [0.0] * TOTAL_ACTIONS
            visit_counts[action] = 1.0
            return action, visit_counts

        total_visits = sum(c.visits for c in root.children.values())
        visit_counts = [0.0] * TOTAL_ACTIONS
        for a, child in root.children.items():
            visit_counts[a] = child.visits / total_visits if total_visits > 0 else 0.0

        action = max(root.children.values(), key=lambda c: c.visits).action
        return action, visit_counts

    def _simulate(self, root: AlphaMCTSNode) -> None:
        node = self._select(root)
        if node.untried_actions and not self._is_terminal(node):
            node = self._expand(node)
        value = self._evaluate(node)
        self._backpropagate(node, value)

    def _select(self, node: AlphaMCTSNode) -> AlphaMCTSNode:
        while not node.untried_actions and node.children and not self._is_terminal(node):
            node = max(node.children.values(), key=lambda c: self._ucb(c, node))
        return node

    def _ucb(self, node: AlphaMCTSNode, parent: AlphaMCTSNode) -> float:
        if node.visits == 0:
            return float("inf")
        exploit = node.total_value / node.visits
        explore = _C * node.prior * math.sqrt(parent.visits) / (1 + node.visits)
        return exploit + explore

    def _expand(self, node: AlphaMCTSNode) -> AlphaMCTSNode:
        action = node.untried_actions.pop()

        # Compute prior from PARENT state before stepping (correct AlphaZero pattern)
        parent_obs = torch.tensor(
            compute_observation(node.game, self._player_name), dtype=torch.float32
        )
        parent_mask_np = compute_mask(node.game, self._player_name)
        parent_mask = torch.tensor(parent_mask_np, dtype=torch.bool)
        with torch.no_grad():
            parent_priors, _ = self._network(parent_obs, parent_mask)
        child_prior = parent_priors[action].item()

        game = _clone(node.game)
        is_terminal = _step_inplace(game, action, self._player_name)

        while (not is_terminal
               and game.turn.name == self._player_name
               and game.phase == GamePhase.DISCARD):
            discard_mask = compute_mask(game, self._player_name)
            d_action = self._best_discard_action(game, discard_mask)
            is_terminal = _step_inplace(game, d_action, self._player_name)

        while not is_terminal and game.turn.name != self._player_name:
            opp_name = game.turn.name
            opp_mask_np = compute_mask(game, opp_name)

            if game.phase == GamePhase.DISCARD:
                # Rule-based: discard the most-held non-master token
                opp_player = next(p for p in game.players if p.name == opp_name)
                tc = Counter(t.name for t in opp_player.tokens)
                opp_action = None
                best_count = -1
                for ptype, idx in DISCARD_ACTION.items():
                    if opp_mask_np[idx] and ptype != PokeballType.Master:
                        count = tc.get(ptype, 0)
                        if count > best_count:
                            best_count = count
                            opp_action = idx
                if opp_action is None:
                    opp_action = int(np.where(opp_mask_np)[0][0])
            else:
                opp_obs = torch.tensor(compute_observation(game, opp_name), dtype=torch.float32)
                opp_mask = torch.tensor(opp_mask_np, dtype=torch.bool)
                with torch.no_grad():
                    opp_policy, _ = self._network(opp_obs, opp_mask)
                opp_action = int(torch.multinomial(opp_policy, 1).item())

            is_terminal = _step_inplace(game, opp_action, opp_name)

        if not is_terminal and node.depth + 1 < self._depth:
            child_mask_np = compute_mask(game, self._player_name)
            untried = list(np.where(child_mask_np)[0])
        else:
            untried = []

        child = AlphaMCTSNode(
            game=game, parent=node, action=action,
            prior=child_prior,
            depth=node.depth + 1, untried_actions=untried,
        )
        node.children[action] = child
        return child

    def _evaluate(self, node: AlphaMCTSNode) -> float:
        if self._is_terminal(node):
            if node.game.winner is None:
                return 0.5
            return 1.0 if node.game.winner.name == self._player_name else 0.0
        obs = torch.tensor(
            compute_observation(node.game, self._player_name), dtype=torch.float32
        )
        mask = torch.tensor(compute_mask(node.game, self._player_name), dtype=torch.bool)
        with torch.no_grad():
            _, value = self._network(obs, mask)
        return value.item()

    def _backpropagate(self, node: AlphaMCTSNode, value: float) -> None:
        while node is not None:
            node.visits += 1
            node.total_value += value
            node = node.parent

    def _is_terminal(self, node: AlphaMCTSNode) -> bool:
        return node.game.winner is not None

    def _best_discard_action(self, game: Game, mask: np.ndarray) -> int:
        player = next(p for p in game.players if p.name == self._player_name)
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
