from collections import Counter
from pokemon_splendor.models import Game, Player, Board, Pokemon, PokeballType


def _token_counts(tokens) -> dict[str, int]:
    counts = Counter(t.name.value for t in tokens)
    return {pt.value: counts.get(pt.value, 0) for pt in PokeballType}


def _serialize_pokemon(p: Pokemon | None) -> dict | None:
    if p is None:
        return None
    return {
        "name": p.name,
        "tier": p.tier.value,
        "cost": [t.name.value for t in p.cost],
        "bonus": [b.name.value for b in p.bonus],
        "evolve": [b.name.value for b in p.evolve],
        "evolve_into": p.evolve_into,
        "point": p.point,
        "evolved": p.evolved,
    }


def _serialize_player(p: Player) -> dict:
    return {
        "name": p.name,
        "points": p.points,
        "tokens": _token_counts(p.tokens),
        "cards": [_serialize_pokemon(c) for c in p.cards],
        "reserved_cards": [_serialize_pokemon(c) for c in p.reserved_cards],
    }


def _serialize_board(b: Board) -> dict:
    return {
        "common_revealed":   [_serialize_pokemon(p) for p in b.common_revealed],
        "uncommon_revealed": [_serialize_pokemon(p) for p in b.uncommon_revealed],
        "rare_revealed":     [_serialize_pokemon(p) for p in b.rare_revealed],
        "epic_revealed":     [_serialize_pokemon(p) for p in b.epic_revealed],
        "legendary_revealed":[_serialize_pokemon(p) for p in b.legendary_revealed],
        "common_deck_count":   len(b.common_deck),
        "uncommon_deck_count": len(b.uncommon_deck),
        "rare_deck_count":     len(b.rare_deck),
        "epic_deck_count":     len(b.epic_deck),
        "legendary_deck_count":len(b.legendary_deck),
    }


def serialize_game(game: Game) -> dict:
    return {
        "round": game.round,
        "phase": game.phase.value,
        "turn": game.turn.name,
        "players": [_serialize_player(p) for p in game.players],
        "board": _serialize_board(game.board),
        "board_tokens": {pt.value: game.tokens.get(pt, 0) for pt in PokeballType},
    }
