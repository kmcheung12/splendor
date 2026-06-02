# src/pokemon_splendor/engine/eval.py
from collections import Counter
from pokemon_splendor.models import Game, Player, PokeballType, Tier
from pokemon_splendor.engine.rules import get_player_bonuses, calculate_effective_cost

BASE_ALPHA = 1.0
WIN_SCORE = 18.0


def evaluate_position(game: Game, player: Player) -> float:
    """
    Shortfall-based position value normalised to ~[0, 1].
    Returns player.points/WIN_SCORE + alpha * max(card.point / (rounds_to_catch + 1))
    where rounds_to_catch = ceil(shortfall / 3) and alpha = BASE_ALPHA / (num_players - 1).
    """
    bonuses = get_player_bonuses(player)
    ptokens = Counter(t.name for t in player.tokens)
    all_slots = (
        game.board.common_revealed + game.board.uncommon_revealed
        + game.board.rare_revealed + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    max_val = 0.0
    for card in all_slots:
        if card is None:
            continue
        ec = calculate_effective_cost(card, bonuses)
        master_req = max(
            ec.get(PokeballType.Master, 0),
            1 if card.tier in (Tier.Epic, Tier.Legendary) else 0,
        )
        if ptokens.get(PokeballType.Master, 0) < master_req:
            continue
        shortfall = sum(
            max(0, ec.get(pt, 0) - ptokens.get(pt, 0))
            for pt in PokeballType if pt != PokeballType.Master
        )
        rounds = (shortfall + 2) // 3
        max_val = max(max_val, card.point / (rounds + 1))
    alpha = BASE_ALPHA / max(1, len(game.players) - 1)
    return (player.points + alpha * max_val) / WIN_SCORE
