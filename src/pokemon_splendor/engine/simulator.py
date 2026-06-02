import copy
from pokemon_splendor.models import Game, Player, GamePhase
from pokemon_splendor.engine.rules import (
    apply_take_different_tokens, apply_take_same_tokens,
    apply_catch_pokemon, apply_reserve, apply_discard, apply_evolve,
    get_evolvable_cards, check_win_condition,
)
from pokemon_splendor.engine.actions import (
    TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START, DISCARD_START,
    EVOLVE_START, EVOLVE_PASS, DISCARD_ACTION,
)


def game_step(game: Game, action: int, player_name: str) -> tuple[Game, bool]:
    """Apply action to a deep copy of game. Returns (new_game, is_terminal)."""
    game = copy.deepcopy(game)
    is_terminal = _step_inplace(game, action, player_name)
    return game, is_terminal


def _step_inplace(game: Game, action: int, player_name: str) -> bool:
    """Apply action in-place. Returns True if game is now terminal."""
    player = next(p for p in game.players if p.name == player_name)
    _apply_action(game, player, action)
    return _process_transitions(game, player)


def _apply_action(game: Game, player: Player, action: int) -> None:
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
        apply_evolve(game, player, card_idx)
        game.evolved_this_turn = True
        return

    # MAIN phase
    if action == EVOLVE_PASS:
        return
    # Fallback: compute_mask returns DISCARD actions when no normal MAIN actions are valid
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
        _catch_preserving_bonus_points(game, player, pokemon, from_reserved=False, board_slot=slot_idx)
    elif CATCH_RESERVED_START <= action < RESERVE_MASTER_START:
        idx = action - CATCH_RESERVED_START
        pokemon = player.reserved_cards[idx]
        _catch_preserving_bonus_points(game, player, pokemon, from_reserved=True, board_slot=None)
    elif RESERVE_MASTER_START <= action < RESERVE_NO_MASTER_START:
        slot_idx = action - RESERVE_MASTER_START
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed
            + game.board.rare_revealed
        )
        pokemon = all_slots[slot_idx]
        apply_reserve(game, player, pokemon, board_slot=slot_idx, take_master=True)
    elif RESERVE_NO_MASTER_START <= action < DISCARD_START:
        slot_idx = action - RESERVE_NO_MASTER_START
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed
            + game.board.rare_revealed
        )
        pokemon = all_slots[slot_idx]
        apply_reserve(game, player, pokemon, board_slot=slot_idx, take_master=False)
    else:
        raise ValueError(f"Unrecognized MAIN action {action}")


def _catch_preserving_bonus_points(
    game: Game, player: Player, pokemon, from_reserved: bool, board_slot
) -> None:
    """Call apply_catch_pokemon but preserve any points not accounted for by cards.

    apply_catch_pokemon calls _recalculate_points which sets player.points to
    sum(card.point for card in player.cards). If the player had manually-set
    bonus points (e.g., in tests), those would be lost. We preserve them here.
    """
    cards_points_before = sum(c.point for c in player.cards if not c.evolved)
    bonus_points = player.points - cards_points_before
    apply_catch_pokemon(game, player, pokemon, from_reserved=from_reserved, board_slot=board_slot)
    if bonus_points != 0:
        player.points += bonus_points


def _process_transitions(game: Game, player: Player) -> bool:
    if game.phase == GamePhase.EVOLVE:
        return _end_turn(game, player)
    if game.phase == GamePhase.DISCARD:
        if len(player.tokens) <= 10:
            return _enter_evolve_phase(game, player)
        # Still need to discard — but check win early so win_triggered is visible
        if check_win_condition(game):
            game.win_triggered = True
        return False
    # MAIN phase action taken
    if len(player.tokens) > 10:
        game.phase = GamePhase.DISCARD
        # Check win early so win_triggered is visible even during discard phase
        if check_win_condition(game):
            game.win_triggered = True
        return False
    return _enter_evolve_phase(game, player)


def _enter_evolve_phase(game: Game, player: Player) -> bool:
    game.phase = GamePhase.EVOLVE
    evolvable = get_evolvable_cards(game, player)
    if not evolvable:
        return _end_turn(game, player)
    return False


def _end_turn(game: Game, player: Player) -> bool:
    game.phase = GamePhase.MAIN
    game.evolved_this_turn = False

    winner = check_win_condition(game)
    if winner:
        game.win_triggered = True

    if game.win_triggered:
        starting_idx = game.players.index(game.starting_player)
        last_in_round_idx = (starting_idx - 1) % len(game.players)
        last_in_round = game.players[last_in_round_idx]
        if player is last_in_round:
            game.winner = winner or check_win_condition(game)
            return True

    idx = game.players.index(player)
    next_player = game.players[(idx + 1) % len(game.players)]
    if next_player is game.starting_player:
        game.round += 1
    game.turn = next_player
    return False
