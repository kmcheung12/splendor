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

    def __init__(self, jsonl_path: Path, num_players: int = 2, render_mode: str | None = None):
        assert 2 <= num_players <= 4
        self.jsonl_path = jsonl_path
        self.num_players = num_players
        self.render_mode = render_mode
        self._all_pokemon = load_pokemon(jsonl_path)

        self.possible_agents = [f"player_{i}" for i in range(num_players)]
        self.agents = list(self.possible_agents)

        obs_size = self._obs_size()
        self.observation_spaces = {
            a: gymnasium.spaces.Box(0, 1, shape=(obs_size,), dtype=np.float32)
            for a in self.possible_agents
        }
        self.action_spaces = {
            a: gymnasium.spaces.Discrete(TOTAL_ACTIONS)
            for a in self.possible_agents
        }
        self.game: Game | None = None

    def _obs_size(self) -> int:
        # Fixed size regardless of num_players so models are portable across game sizes.
        # Layout: 6 board tokens + 14*20 card slots + 4*13 player slots + 4 current-player one-hot + 3 phase
        return 6 + 14 * 20 + 4 * 13 + 4 + 3  # = 345

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
        start = random.choice(players)

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
        obs = np.zeros(self._obs_size(), dtype=np.float32)
        offset = 0
        # Board tokens
        for i, ptype in enumerate(PokeballType):
            obs[offset + i] = self.game.tokens.get(ptype, 0) / 10.0
        offset += 6
        # Revealed cards
        all_slots = (
            self.game.board.common_revealed
            + self.game.board.uncommon_revealed
            + self.game.board.rare_revealed
            + self.game.board.epic_revealed
            + self.game.board.legendary_revealed
        )
        for slot in all_slots:
            if slot:
                obs[offset:offset+6] = [
                    Counter(t.name for t in slot.cost).get(pt, 0) / 5.0
                    for pt in PokeballType
                ]
                obs[offset+6:offset+12] = [
                    sum(1 for b in slot.bonus if b.name == pt) / 3.0
                    for pt in PokeballType
                ]
                obs[offset+12:offset+18] = [
                    sum(1 for b in slot.evolve if b.name == pt) / 3.0
                    for pt in PokeballType
                ]
                obs[offset+18] = slot.point / 15.0
                obs[offset+19] = list(Tier).index(slot.tier) / 4.0
            offset += 20
        # Players — always 4 slots; absent players left as zeros
        player_map = {p.name: p for p in self.game.players}
        for i in range(4):
            a = f"player_{i}"
            if a in player_map:
                p = player_map[a]
                tc = Counter(t.name for t in p.tokens)
                for j, pt in enumerate(PokeballType):
                    obs[offset + j] = tc.get(pt, 0) / 10.0
                offset += 6
                tier_counts = Counter(c.tier for c in p.cards if not c.evolved)
                for t in Tier:
                    obs[offset] = tier_counts.get(t, 0) / 5.0
                    offset += 1
                obs[offset] = p.points / 18.0
                obs[offset+1] = len(p.reserved_cards) / 3.0
                offset += 2
            else:
                offset += 13
        # Current player one-hot — always 4 slots
        for i in range(4):
            obs[offset + i] = 1.0 if f"player_{i}" == self.game.turn.name else 0.0
        offset += 4
        # Phase
        for i, ph in enumerate(GamePhase):
            obs[offset + i] = 1.0 if self.game.phase == ph else 0.0
        return obs

    def action_mask(self, agent: str) -> np.ndarray:
        mask = np.zeros(TOTAL_ACTIONS, dtype=bool)
        player = next(p for p in self.game.players if p.name == agent)
        game = self.game

        if game.phase == GamePhase.DISCARD:
            tc = Counter(t.name for t in player.tokens)
            for ptype, idx in DISCARD_ACTION.items():
                if tc.get(ptype, 0) > 0:
                    mask[idx] = True
            return mask

        if game.phase == GamePhase.EVOLVE:
            mask[EVOLVE_PASS] = True
            evolvable = get_evolvable_cards(game, player)
            for card, _ in evolvable:
                idx = player.cards.index(card)
                if idx < MAX_OWNED_CARDS:
                    mask[EVOLVE_START + idx] = True
            return mask

        # Main phase
        available_types = {pt for pt in NORMAL_TYPES if game.tokens.get(pt, 0) > 0}
        for i, combo in enumerate(TAKE_DIFF_COMBOS):
            if all(pt in available_types for pt in combo):
                mask[TAKE_DIFF_START + i] = True

        for pt in NORMAL_TYPES:
            if game.tokens.get(pt, 0) >= 4:
                mask[TAKE_SAME_ACTION[pt]] = True

        all_slots = (
            game.board.common_revealed
            + game.board.uncommon_revealed
            + game.board.rare_revealed
            + game.board.epic_revealed
            + game.board.legendary_revealed
        )
        player_bonuses = get_player_bonuses(player)
        ptokens = Counter(t.name for t in player.tokens)

        for slot_idx, pokemon in enumerate(all_slots):
            if pokemon is None:
                continue
            effective = calculate_effective_cost(pokemon, player_bonuses)
            master_req = effective.get(PokeballType.Master, 0)
            if pokemon.tier in (Tier.Epic, Tier.Legendary):
                master_req = max(master_req, 1)
            master_have = ptokens.get(PokeballType.Master, 0)
            if master_have < master_req:
                catch_ok = False
            else:
                shortfall = sum(
                    max(0, needed - ptokens.get(pt, 0))
                    for pt, needed in effective.items()
                    if pt != PokeballType.Master
                )
                catch_ok = (master_have - master_req) >= shortfall
            if catch_ok:
                mask[CATCH_BOARD_START + slot_idx] = True

        for i, pokemon in enumerate(player.reserved_cards):
            effective = calculate_effective_cost(pokemon, player_bonuses)
            master_req = effective.get(PokeballType.Master, 0)
            if pokemon.tier in (Tier.Epic, Tier.Legendary):
                master_req = max(master_req, 1)
            master_have = ptokens.get(PokeballType.Master, 0)
            if master_have >= master_req:
                shortfall = sum(
                    max(0, needed - ptokens.get(pt, 0))
                    for pt, needed in effective.items()
                    if pt != PokeballType.Master
                )
                if (master_have - master_req) >= shortfall:
                    mask[CATCH_RESERVED_START + i] = True

        if len(player.reserved_cards) < 3:
            reservable_slots = [
                i for i, p in enumerate(all_slots[:12]) if p is not None
            ]
            for slot_idx in reservable_slots:
                if game.tokens.get(PokeballType.Master, 0) > 0:
                    mask[RESERVE_MASTER_START + slot_idx] = True
                mask[RESERVE_NO_MASTER_START + slot_idx] = True

        # Fallback: if no action is valid (e.g. all tokens exhausted),
        # allow the player to discard a token to break deadlock.
        if not mask.any():
            tc = Counter(t.name for t in player.tokens)
            for ptype, idx in DISCARD_ACTION.items():
                if tc.get(ptype, 0) > 0:
                    mask[idx] = True
            # If player has no tokens either, allow a bare pass.
            if not mask.any():
                mask[EVOLVE_PASS] = True

        return mask

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
            points_before = player.points
            apply_evolve(game, player, card_idx)
            game.evolved_this_turn = True
            self.rewards[player.name] += (player.points - points_before) * 0.05
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
            points_before = player.points
            apply_catch_pokemon(game, player, pokemon, from_reserved=False, board_slot=slot_idx)
            self.rewards[player.name] += (player.points - points_before) * 0.05
        elif CATCH_RESERVED_START <= action < RESERVE_MASTER_START:
            idx = action - CATCH_RESERVED_START
            pokemon = player.reserved_cards[idx]
            points_before = player.points
            apply_catch_pokemon(game, player, pokemon, from_reserved=True, board_slot=None)
            self.rewards[player.name] += (player.points - points_before) * 0.05
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
