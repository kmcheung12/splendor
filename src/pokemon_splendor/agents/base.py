# src/pokemon_splendor/agents/base.py
from collections import Counter
import numpy as np
from pokemon_splendor.models import Game, GamePhase, Player, Pokemon, PokeballType, Tier
from pokemon_splendor.engine.actions import (
    TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START, DISCARD_START,
    EVOLVE_START, EVOLVE_PASS, DISCARD_ACTION, TAKE_SAME_ACTION,
)


def describe_action(action: int, game: Game, player: Player) -> str:
    all_slots = (
        game.board.common_revealed + game.board.uncommon_revealed +
        game.board.rare_revealed + game.board.epic_revealed +
        game.board.legendary_revealed
    )
    reservable = (
        game.board.common_revealed + game.board.uncommon_revealed +
        game.board.rare_revealed
    )
    if TAKE_DIFF_START <= action < TAKE_SAME_START:
        combo = TAKE_DIFF_COMBOS[action - TAKE_DIFF_START]
        return f"Take {', '.join(pt.value for pt in combo)}"
    if TAKE_SAME_START <= action < CATCH_BOARD_START:
        pt = NORMAL_TYPES[action - TAKE_SAME_START]
        return f"Take 2 {pt.value}"
    if CATCH_BOARD_START <= action < CATCH_RESERVED_START:
        p = all_slots[action - CATCH_BOARD_START]
        if p is None:
            return f"Catch board slot {action - CATCH_BOARD_START} (empty)"
        return f"Catch {p.name} ({p.tier.value}, {p.point}pts)"
    if CATCH_RESERVED_START <= action < RESERVE_MASTER_START:
        idx = action - CATCH_RESERVED_START
        if idx < len(player.reserved_cards):
            p = player.reserved_cards[idx]
            return f"Catch reserved {p.name}"
        return f"Catch reserved slot {idx} (empty)"
    if RESERVE_MASTER_START <= action < RESERVE_NO_MASTER_START:
        idx = action - RESERVE_MASTER_START
        p = reservable[idx] if idx < len(reservable) else None
        if p is None:
            return f"Reserve slot {idx} + Master token"
        return f"Reserve {p.name} + Master token"
    if RESERVE_NO_MASTER_START <= action < DISCARD_START:
        idx = action - RESERVE_NO_MASTER_START
        p = reservable[idx] if idx < len(reservable) else None
        if p is None:
            return f"Reserve slot {idx}"
        return f"Reserve {p.name}"
    if DISCARD_START <= action < EVOLVE_START:
        pt = list(PokeballType)[action - DISCARD_START]
        return f"Discard {pt.value}"
    if EVOLVE_START <= action < EVOLVE_PASS:
        idx = action - EVOLVE_START
        if idx < len(player.cards):
            card = player.cards[idx]
            return f"Evolve {card.name}"
        return f"Evolve slot {idx} (empty)"
    return "Pass evolution"


class RuleBasedAgent:
    def __init__(self, env, player_name: str):
        self._env = env
        self._player_name = player_name

    @property
    def _game(self) -> Game:
        return self._env.game

    @property
    def _player(self) -> Player:
        return next(p for p in self._env.game.players if p.name == self._player_name)

    def act(self, obs: np.ndarray, mask: np.ndarray) -> int:
        game = self._game
        if game.phase == GamePhase.DISCARD:
            return self._handle_discard(mask)
        if game.phase == GamePhase.EVOLVE:
            return self._handle_evolve(mask)
        return self._main_action(mask)

    def _main_action(self, mask: np.ndarray) -> int:
        raise NotImplementedError

    def _handle_discard(self, mask: np.ndarray) -> int:
        tc = Counter(t.name for t in self._player.tokens)
        best_action, best_score = None, -1
        for ptype, idx in DISCARD_ACTION.items():
            if not mask[idx]:
                continue
            score = tc.get(ptype, 0) if ptype != PokeballType.Master else -100
            if score > best_score:
                best_score = score
                best_action = idx
        return best_action if best_action is not None else int(np.where(mask)[0][0])

    def _handle_evolve(self, mask: np.ndarray) -> int:
        for action in range(EVOLVE_START, EVOLVE_PASS):
            if mask[action]:
                return action
        if mask[EVOLVE_PASS]:
            return EVOLVE_PASS
        return int(np.where(mask)[0][0])

    def _catchable(self, mask: np.ndarray) -> list[tuple[int, Pokemon]]:
        game = self._game
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed + game.board.epic_revealed +
            game.board.legendary_revealed
        )
        result = []
        for slot_idx, pokemon in enumerate(all_slots):
            action = CATCH_BOARD_START + slot_idx
            if mask[action] and pokemon is not None:
                result.append((action, pokemon))
        for i, pokemon in enumerate(self._player.reserved_cards):
            action = CATCH_RESERVED_START + i
            if mask[action]:
                result.append((action, pokemon))
        return result

    def _take_toward(self, mask: np.ndarray, needed: Counter) -> int:
        best_action, best_score = None, -1
        for i, combo in enumerate(TAKE_DIFF_COMBOS):
            action = TAKE_DIFF_START + i
            if not mask[action]:
                continue
            score = sum(min(needed.get(pt, 0), 1) for pt in combo)
            if score > best_score:
                best_score = score
                best_action = action
        for pt in NORMAL_TYPES:
            action = TAKE_SAME_ACTION[pt]
            if mask[action] and needed.get(pt, 0) >= 2 and 2 > best_score:
                best_score = 2
                best_action = action
        return best_action if best_action is not None else int(np.where(mask)[0][0])
