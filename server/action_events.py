from pokemon_splendor.models import Game, PokeballType
from pokemon_splendor.engine.actions import (
    TAKE_DIFF_COMBOS, NORMAL_TYPES,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START, CATCH_RESERVED_START,
    RESERVE_MASTER_START, RESERVE_NO_MASTER_START, DISCARD_START,
    EVOLVE_START, EVOLVE_PASS,
)


def build_action_event(game: Game, player_name: str, action: int) -> dict:
    action = int(action)
    base = {"player": player_name}

    if TAKE_DIFF_START <= action < TAKE_SAME_START:
        combo = TAKE_DIFF_COMBOS[action - TAKE_DIFF_START]
        return {**base, "type": "take_tokens", "tokens": [pt.value for pt in combo]}

    if TAKE_SAME_START <= action < CATCH_BOARD_START:
        pt = NORMAL_TYPES[action - TAKE_SAME_START]
        return {**base, "type": "take_tokens", "tokens": [pt.value, pt.value]}

    if CATCH_BOARD_START <= action < CATCH_RESERVED_START:
        slot_idx = action - CATCH_BOARD_START
        all_slots = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed + game.board.epic_revealed +
            game.board.legendary_revealed
        )
        card = all_slots[slot_idx]
        return {
            **base,
            "type": "catch_card",
            "card": card.name if card else None,
            "slot": slot_idx,
            "tier": card.tier.value if card else None,
            "from_reserve": False,
        }

    if CATCH_RESERVED_START <= action < RESERVE_MASTER_START:
        idx = action - CATCH_RESERVED_START
        player = next(p for p in game.players if p.name == player_name)
        card = player.reserved_cards[idx] if idx < len(player.reserved_cards) else None
        return {
            **base,
            "type": "catch_card",
            "card": card.name if card else None,
            "slot": idx,
            "tier": card.tier.value if card else None,
            "from_reserve": True,
        }

    if RESERVE_MASTER_START <= action < RESERVE_NO_MASTER_START:
        slot_idx = action - RESERVE_MASTER_START
        reservable = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed
        )
        card = reservable[slot_idx] if slot_idx < len(reservable) else None
        return {
            **base,
            "type": "reserve_card",
            "card": card.name if card else None,
            "slot": slot_idx,
            "tier": card.tier.value if card else None,
            "took_master": True,
        }

    if RESERVE_NO_MASTER_START <= action < DISCARD_START:
        slot_idx = action - RESERVE_NO_MASTER_START
        reservable = (
            game.board.common_revealed + game.board.uncommon_revealed +
            game.board.rare_revealed
        )
        card = reservable[slot_idx] if slot_idx < len(reservable) else None
        return {
            **base,
            "type": "reserve_card",
            "card": card.name if card else None,
            "slot": slot_idx,
            "tier": card.tier.value if card else None,
            "took_master": False,
        }

    if DISCARD_START <= action < EVOLVE_START:
        pt = list(PokeballType)[action - DISCARD_START]
        return {**base, "type": "discard_token", "token": pt.value}

    if EVOLVE_START <= action < EVOLVE_PASS:
        player = next(p for p in game.players if p.name == player_name)
        idx = action - EVOLVE_START
        card = player.cards[idx] if idx < len(player.cards) else None
        return {**base, "type": "evolve_card", "card": card.name if card else None, "card_index": idx}

    return {**base, "type": "pass"}
