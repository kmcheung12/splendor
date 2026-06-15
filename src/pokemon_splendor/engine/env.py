import copy
import random
from pathlib import Path
from collections import Counter
import numpy as np
import gymnasium
from pettingzoo import AECEnv
from pettingzoo.utils.agent_selector import agent_selector

from pokemon_splendor.models import (
    Game, Player, Board, Pokemon, PokeballType, Tier, GamePhase,
)
from pokemon_splendor.data.loader import load_pokemon
from pokemon_splendor.engine.actions import (
    TOTAL_ACTIONS, TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START,
    CATCH_RESERVED_START, RESERVE_MASTER_START, RESERVE_NO_MASTER_START,
    DISCARD_START, EVOLVE_START, EVOLVE_PASS,
    BOARD_SLOT_TIERS, RESERVABLE_TIERS, DISCARD_ACTION, TAKE_SAME_ACTION,
    MAX_OWNED_CARDS,
)
from pokemon_splendor.engine.rules import (
    apply_take_different_tokens, apply_take_same_tokens,
    apply_catch_pokemon, apply_reserve, apply_discard, apply_evolve,
    get_evolvable_cards, check_win_condition, refill_board_slot,
    get_player_bonuses, calculate_effective_cost,
)
from pokemon_splendor.engine.observation import compute_observation, compute_mask, OBS_SIZE

GAMMA_SHAPING = 0.99
BASE_ALPHA = 1.0
WIN_SCORE = 18.0  # keeps shaping on the same scale as the terminal ±1.0 reward


def _phi(player: Player, game: Game) -> float:
    """Potential of state: current points + opportunity value of best affordable card."""
    player_bonuses = get_player_bonuses(player)
    ptokens = Counter(t.name for t in player.tokens)
    all_slots = (
        game.board.common_revealed + game.board.uncommon_revealed
        + game.board.rare_revealed + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    max_pts = 0
    for pokemon in all_slots:
        if pokemon is None:
            continue
        effective = calculate_effective_cost(pokemon, player_bonuses)
        master_req = effective.get(PokeballType.Master, 0)
        if pokemon.tier in (Tier.Epic, Tier.Legendary):
            master_req = max(master_req, 1)
        master_have = ptokens.get(PokeballType.Master, 0)
        if master_have < master_req:
            continue
        shortfall = sum(
            max(0, effective.get(pt, 0) - ptokens.get(pt, 0))
            for pt in PokeballType if pt != PokeballType.Master
        )
        if (master_have - master_req) >= shortfall:
            max_pts = max(max_pts, pokemon.point)
    alpha = BASE_ALPHA / max(1, len(game.players) - 1)
    return player.points + alpha * max_pts


def _shaping(phi_before: float, phi_after: float) -> float:
    return (GAMMA_SHAPING * phi_after - phi_before) / WIN_SCORE


INITIAL_TOKENS = {2: 4, 3: 5, 4: 7}
TIER_SLOTS = {
    Tier.Common: (0, 4),
    Tier.Uncommon: (4, 8),
    Tier.Rare: (8, 12),
    Tier.Epic: (12, 13),
    Tier.Legendary: (13, 14),
}


class PokemonSplendorEnv(AECEnv):
    metadata = {"name": "pokemon_splendor_v0"}

    def __init__(self, jsonl_path: Path, num_players: int = 2, render_mode: str | None = None,
                 obs_fn=None, obs_size: int | None = None):
        assert 2 <= num_players <= 4
        self.jsonl_path = jsonl_path
        self.num_players = num_players
        self.render_mode = render_mode
        self._all_pokemon = load_pokemon(jsonl_path)
        self._obs_fn = obs_fn if obs_fn is not None else compute_observation
        self._obs_size_override = obs_size if obs_size is not None else OBS_SIZE

        self.possible_agents = [f"player_{i}" for i in range(num_players)]
        self.agents = list(self.possible_agents)

        size = self._obs_size()
        self.observation_spaces = {
            a: gymnasium.spaces.Box(0, 1, shape=(size,), dtype=np.float32)
            for a in self.possible_agents
        }
        self.action_spaces = {
            a: gymnasium.spaces.Discrete(TOTAL_ACTIONS)
            for a in self.possible_agents
        }
        self.game: Game | None = None

    def _obs_size(self) -> int:
        return self._obs_size_override

    def observation_space(self, agent: str):
        return self.observation_spaces[agent]

    def action_space(self, agent: str):
        return self.action_spaces[agent]

    def reset(self, seed=None, options=None):
        if seed is not None:
            random.seed(seed)

        by_tier: dict[Tier, list[Pokemon]] = {t: [] for t in Tier}
        for p in self._all_pokemon:
            by_tier[p.tier].append(copy.deepcopy(p))
        for lst in by_tier.values():
            random.shuffle(lst)

        def fill(lst, n):
            revealed = lst[:n] + [None] * max(0, n - len(lst))
            deck = lst[n:]
            return revealed[:n], deck

        cr, cd = fill(by_tier[Tier.Common], 4)
        ur, ud = fill(by_tier[Tier.Uncommon], 4)
        rr, rd = fill(by_tier[Tier.Rare], 4)
        er, ed = fill(by_tier[Tier.Epic], 1)
        lr, ld = fill(by_tier[Tier.Legendary], 1)

        board = Board(
            common_revealed=cr, common_deck=cd,
            uncommon_revealed=ur, uncommon_deck=ud,
            rare_revealed=rr, rare_deck=rd,
            epic_revealed=er, epic_deck=ed,
            legendary_revealed=lr, legendary_deck=ld,
        )

        normal_count = INITIAL_TOKENS[self.num_players]
        tokens = {
            PokeballType.Red: normal_count,
            PokeballType.Yellow: normal_count,
            PokeballType.Blue: normal_count,
            PokeballType.Pink: normal_count,
            PokeballType.Black: normal_count,
            PokeballType.Master: 5,
        }

        players = [Player(name=a) for a in self.possible_agents]
        fpi = (options or {}).get('first_player_index')
        start = players[fpi] if fpi is not None else random.choice(players)

        self.game = Game(
            players=players,
            turn=start,
            starting_player=start,
            round=1,
            board=board,
            tokens=tokens,
        )

        self.agents = list(self.possible_agents)
        self._agent_selector = agent_selector(self.agents)
        self.agent_selection = self._agent_selector.reset()
        # Sync selector to starting player
        while self.agent_selection != start.name:
            self.agent_selection = self._agent_selector.next()

        self.rewards = {a: 0.0 for a in self.agents}
        self.terminations = {a: False for a in self.agents}
        self.truncations = {a: False for a in self.agents}
        self.infos = {a: {} for a in self.agents}
        self._cumulative_rewards = {a: 0.0 for a in self.agents}
        self._step_count = 0
        self._max_steps = 9000

    def observe(self, agent: str) -> np.ndarray:
        return self._obs_fn(self.game, agent)

    def action_mask(self, agent: str) -> np.ndarray:
        return compute_mask(self.game, agent)

    def _enter_evolve_phase(self, agent: str, player: Player) -> None:
        self.game.phase = GamePhase.EVOLVE
        if not self.action_mask(agent)[EVOLVE_START:EVOLVE_PASS].any():
            self._end_turn(player)

    def _declare_winner_by_points(self):
        """Declare a winner based on current points (used for truncation)."""
        winner = max(self.game.players, key=lambda p: (p.points, len(p.cards)))
        for p in self.game.players:
            self.rewards[p.name] = 1.0 if p is winner else -1.0
            self.terminations[p.name] = True
        self.agents = []

    def step(self, action: int):
        self._step_count += 1
        agent = self.agent_selection
        self.rewards[agent] = 0
        player = next(p for p in self.game.players if p.name == agent)

        self._apply_action(player, action)

        # Check max steps truncation
        if self._step_count >= self._max_steps:
            self._declare_winner_by_points()
            return

        if self.game.phase == GamePhase.EVOLVE:
            # Evolve action (or pass) just taken — end turn
            self._end_turn(player)
            return

        if self.game.phase == GamePhase.DISCARD:
            if len(player.tokens) <= 10:
                self._enter_evolve_phase(agent, player)
            # else stay in DISCARD for next discard action
            return

        # Main phase action just taken
        if len(player.tokens) > 10:
            self.game.phase = GamePhase.DISCARD
        else:
            self._enter_evolve_phase(agent, player)

    def _apply_action(self, player: Player, action: int):
        game = self.game

        if game.phase == GamePhase.DISCARD:
            for ptype, idx in DISCARD_ACTION.items():
                if action == idx:
                    apply_discard(game, player, ptype)
                    return
            raise ValueError(f"Invalid discard action {action}")

        if game.phase == GamePhase.EVOLVE:
            if action == EVOLVE_PASS:
                return
            card_idx = action - EVOLVE_START
            phi_before = _phi(player, game)
            apply_evolve(game, player, card_idx)
            game.evolved_this_turn = True
            self.rewards[player.name] += _shaping(phi_before, _phi(player, game))
            return

        # Main phase
        if action == EVOLVE_PASS:
            # Fallback pass when no other main-phase action is available
            return

        # Fallback discard in MAIN phase (when no normal actions available)
        if DISCARD_START <= action < EVOLVE_START:
            for ptype, idx in DISCARD_ACTION.items():
                if action == idx:
                    apply_discard(game, player, ptype)
                    return
            raise ValueError(f"Invalid discard action {action}")

        if TAKE_DIFF_START <= action < TAKE_SAME_START:
            combo = TAKE_DIFF_COMBOS[action - TAKE_DIFF_START]
            apply_take_different_tokens(game, player, list(combo))
        elif TAKE_SAME_START <= action < CATCH_BOARD_START:
            ptype = NORMAL_TYPES[action - TAKE_SAME_START]
            apply_take_same_tokens(game, player, ptype)
        elif CATCH_BOARD_START <= action < CATCH_RESERVED_START:
            slot_idx = action - CATCH_BOARD_START
            all_slots = (
                game.board.common_revealed + game.board.uncommon_revealed
                + game.board.rare_revealed + game.board.epic_revealed
                + game.board.legendary_revealed
            )
            pokemon = all_slots[slot_idx]
            phi_before = _phi(player, game)
            apply_catch_pokemon(game, player, pokemon, from_reserved=False, board_slot=slot_idx)
            self.rewards[player.name] += _shaping(phi_before, _phi(player, game))
        elif CATCH_RESERVED_START <= action < RESERVE_MASTER_START:
            idx = action - CATCH_RESERVED_START
            pokemon = player.reserved_cards[idx]
            phi_before = _phi(player, game)
            apply_catch_pokemon(game, player, pokemon, from_reserved=True, board_slot=None)
            self.rewards[player.name] += _shaping(phi_before, _phi(player, game))
        elif RESERVE_MASTER_START <= action < RESERVE_NO_MASTER_START:
            slot_idx = action - RESERVE_MASTER_START
            all_slots = (
                game.board.common_revealed + game.board.uncommon_revealed + game.board.rare_revealed
            )
            pokemon = all_slots[slot_idx]
            apply_reserve(game, player, pokemon, board_slot=slot_idx, take_master=True)
        elif RESERVE_NO_MASTER_START <= action < DISCARD_START:
            slot_idx = action - RESERVE_NO_MASTER_START
            all_slots = (
                game.board.common_revealed + game.board.uncommon_revealed + game.board.rare_revealed
            )
            pokemon = all_slots[slot_idx]
            apply_reserve(game, player, pokemon, board_slot=slot_idx, take_master=False)

    def _end_turn(self, player: Player):
        self.game.phase = GamePhase.MAIN
        self.game.evolved_this_turn = False

        winner = check_win_condition(self.game)
        if winner:
            self.game.win_triggered = True

        if self.game.win_triggered:
            # The round ends when the player just before the starting player
            # completes their turn (everyone has had the same number of turns).
            starting_idx = self.game.players.index(self.game.starting_player)
            last_in_round_idx = (starting_idx - 1) % len(self.game.players)
            last_in_round = self.game.players[last_in_round_idx]
            if player is last_in_round:
                final_winner = check_win_condition(self.game)
                for p in self.game.players:
                    agent = p.name
                    self.rewards[agent] = 1.0 if p is final_winner else -1.0
                    self.terminations[agent] = True
                self.agents = []
                return

        # Advance turn
        idx = self.game.players.index(player)
        next_player = self.game.players[(idx + 1) % len(self.game.players)]
        if next_player is self.game.starting_player:
            self.game.round += 1
        self.game.turn = next_player
        self.agent_selection = self._agent_selector.next()

    def last(self, observe=True):
        agent = self.agent_selection
        obs = self.observe(agent) if observe else None
        return (
            obs,
            self.rewards.get(agent, 0),
            self.terminations.get(agent, False),
            self.truncations.get(agent, False),
            self.infos.get(agent, {}),
        )

    def render(self):
        if self.render_mode == "human":
            from pokemon_splendor.cli.renderer import render
            render(self.game)
