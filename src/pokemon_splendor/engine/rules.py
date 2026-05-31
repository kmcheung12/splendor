from collections import Counter
from pokemon_splendor.models import (
    Game, Player, Pokemon, Board, PokeballType, Tier, PokeballToken, Bonus,
)


def get_player_bonuses(player: Player) -> Counter:
    bonuses: Counter = Counter()
    for card in player.cards:
        if not card.evolved:
            for b in card.bonus:
                bonuses[b.name] += 1
    return bonuses


def calculate_effective_cost(pokemon: Pokemon, player_bonuses: Counter) -> Counter:
    cost: Counter = Counter()
    for token in pokemon.cost:
        cost[token.name] += 1
    for ptype, count in player_bonuses.items():
        if ptype in cost:
            cost[ptype] = max(0, cost[ptype] - count)
    return cost


def _player_token_counter(player: Player) -> Counter:
    c: Counter = Counter()
    for t in player.tokens:
        c[t.name] += 1
    return c


def _recalculate_points(player: Player) -> None:
    player.points = sum(c.point for c in player.cards if not c.evolved)


def apply_take_different_tokens(game: Game, player: Player, token_types: list[PokeballType]) -> Game:
    if len(token_types) > 3:
        raise ValueError("Cannot take more than 3 tokens")
    if len(set(token_types)) != len(token_types):
        raise ValueError("Cannot take duplicate types")
    if PokeballType.Master in token_types:
        raise ValueError("Master token cannot be taken as a different token")
    for ptype in token_types:
        if game.tokens.get(ptype, 0) == 0:
            raise ValueError(f"{ptype} not available on board")
    for ptype in token_types:
        game.tokens[ptype] -= 1
        player.tokens.append(PokeballToken(ptype))
    return game


def apply_take_same_tokens(game: Game, player: Player, token_type: PokeballType) -> Game:
    if token_type == PokeballType.Master:
        raise ValueError("Master token cannot be taken as same-type pair")
    if game.tokens.get(token_type, 0) < 4:
        raise ValueError(f"Need at least 4 {token_type} on board to take 2")
    game.tokens[token_type] -= 2
    player.tokens.extend([PokeballToken(token_type), PokeballToken(token_type)])
    return game


def _get_board_slot_list(board: Board, tier: Tier) -> list:
    return {
        Tier.Common: board.common_revealed,
        Tier.Uncommon: board.uncommon_revealed,
        Tier.Rare: board.rare_revealed,
        Tier.Epic: board.epic_revealed,
        Tier.Legendary: board.legendary_revealed,
    }[tier]


def _get_deck(board: Board, tier: Tier) -> list:
    return {
        Tier.Common: board.common_deck,
        Tier.Uncommon: board.uncommon_deck,
        Tier.Rare: board.rare_deck,
        Tier.Epic: board.epic_deck,
        Tier.Legendary: board.legendary_deck,
    }[tier]


def refill_board_slot(board: Board, tier: Tier, slot_index: int) -> None:
    deck = _get_deck(board, tier)
    slot_list = _get_board_slot_list(board, tier)
    slot_list[slot_index] = deck.pop(0) if deck else None


def apply_catch_pokemon(
    game: Game,
    player: Player,
    pokemon: Pokemon,
    from_reserved: bool,
    board_slot: int | None,
) -> Game:
    player_bonuses = get_player_bonuses(player)
    effective_cost = calculate_effective_cost(pokemon, player_bonuses)
    player_tokens = _player_token_counter(player)

    # Validate Master token requirement for Epic/Legendary
    master_required = effective_cost.get(PokeballType.Master, 0)
    if pokemon.tier in (Tier.Epic, Tier.Legendary) and master_required == 0:
        master_required = 1
        effective_cost[PokeballType.Master] = master_required

    master_available = player_tokens.get(PokeballType.Master, 0)
    if master_available < master_required:
        raise ValueError(f"Master token required to catch {pokemon.tier.value} Pokémon")

    shortfall = 0
    for ptype, needed in effective_cost.items():
        if ptype == PokeballType.Master:
            continue
        shortfall += max(0, needed - player_tokens.get(ptype, 0))

    if master_available < master_required + shortfall:
        raise ValueError("Not enough tokens to catch this Pokémon")

    # Deduct tokens from player and return to board
    paid: Counter = Counter()
    for ptype, needed in effective_cost.items():
        if ptype == PokeballType.Master:
            paid[PokeballType.Master] += needed
        else:
            available = player_tokens.get(ptype, 0)
            direct = min(available, needed)
            paid[ptype] += direct
            paid[PokeballType.Master] += needed - direct

    new_tokens = []
    paid_remaining = Counter(paid)
    for t in player.tokens:
        if paid_remaining.get(t.name, 0) > 0:
            paid_remaining[t.name] -= 1
            game.tokens[t.name] = game.tokens.get(t.name, 0) + 1
        else:
            new_tokens.append(t)
    player.tokens = new_tokens

    # Remove from board or reserved
    if from_reserved:
        player.reserved_cards.remove(pokemon)
    else:
        tier_offsets = {
            Tier.Common: 0, Tier.Uncommon: 4, Tier.Rare: 8, Tier.Epic: 12, Tier.Legendary: 13,
        }
        tier_list = _get_board_slot_list(game.board, pokemon.tier)
        local_slot = board_slot - tier_offsets[pokemon.tier]
        tier_list[local_slot] = None
        refill_board_slot(game.board, pokemon.tier, local_slot)

    player.cards.append(pokemon)
    _recalculate_points(player)
    return game


def apply_reserve(
    game: Game,
    player: Player,
    pokemon: Pokemon,
    board_slot: int,
    take_master: bool,
) -> Game:
    if pokemon.tier in (Tier.Epic, Tier.Legendary):
        raise ValueError(f"Epic Pokémon cannot be reserved")
    if len(player.reserved_cards) >= 3:
        raise ValueError("Cannot reserve more than 3 Pokémon")
    if take_master and game.tokens.get(PokeballType.Master, 0) == 0:
        raise ValueError("No Master tokens available to take")

    tier_offsets = {Tier.Common: 0, Tier.Uncommon: 4, Tier.Rare: 8}
    tier_list = _get_board_slot_list(game.board, pokemon.tier)
    local_slot = board_slot - tier_offsets[pokemon.tier]
    tier_list[local_slot] = None
    refill_board_slot(game.board, pokemon.tier, local_slot)

    player.reserved_cards.append(pokemon)
    if take_master:
        game.tokens[PokeballType.Master] -= 1
        player.tokens.append(PokeballToken(PokeballType.Master))
    return game


def apply_discard(game: Game, player: Player, token_type: PokeballType) -> Game:
    for i, t in enumerate(player.tokens):
        if t.name == token_type:
            player.tokens.pop(i)
            game.tokens[token_type] = game.tokens.get(token_type, 0) + 1
            return game
    raise ValueError(f"{token_type} not held by player")


def get_evolvable_cards(game: Game, player: Player) -> list[tuple[Pokemon, Pokemon]]:
    player_bonuses = get_player_bonuses(player)
    result = []
    for card in player.cards:
        if card.evolved or not card.evolve_into:
            continue
        needed: Counter = Counter()
        for b in card.evolve:
            needed[b.name] += 1
        if any(player_bonuses.get(ptype, 0) < count for ptype, count in needed.items()):
            continue
        target = _find_pokemon(game, player, card.evolve_into)
        if target:
            result.append((card, target))
    return result


def _find_pokemon(game: Game, player: Player, name: str) -> Pokemon | None:
    all_revealed = (
        game.board.common_revealed
        + game.board.uncommon_revealed
        + game.board.rare_revealed
        + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    for p in all_revealed:
        if p and p.name == name:
            return p
    for p in player.reserved_cards:
        if p.name == name:
            return p
    return None


def apply_evolve(game: Game, player: Player, card_index: int) -> Game:
    card = player.cards[card_index]
    evolvable = get_evolvable_cards(game, player)
    match = next(((c, t) for c, t in evolvable if c is card), None)
    if not match:
        raise ValueError(f"{card.name} cannot be evolved or target not available")
    source, target = match

    all_tier_lists = [
        game.board.common_revealed,
        game.board.uncommon_revealed,
        game.board.rare_revealed,
        game.board.epic_revealed,
        game.board.legendary_revealed,
    ]
    removed = False
    for tier, tier_list in zip(
        [Tier.Common, Tier.Uncommon, Tier.Rare, Tier.Epic, Tier.Legendary], all_tier_lists
    ):
        for i, p in enumerate(tier_list):
            if p is target:
                tier_list[i] = None
                refill_board_slot(game.board, tier, i)
                removed = True
                break
        if removed:
            break
    if not removed:
        if target in player.reserved_cards:
            player.reserved_cards.remove(target)
        else:
            raise ValueError(f"{target.name} not available on board or reserved")

    source.evolved = True
    player.cards.append(target)
    _recalculate_points(player)
    return game


def check_win_condition(game: Game) -> Player | None:
    triggered = [p for p in game.players if p.points >= 18]
    if not triggered:
        return None
    return max(game.players, key=lambda p: (p.points, len(p.cards)))
