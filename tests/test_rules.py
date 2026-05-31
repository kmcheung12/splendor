import pytest
from copy import deepcopy
from pokemon_splendor.models import PokeballType, GamePhase, Tier
from pokemon_splendor.engine.rules import (
    get_player_bonuses,
    calculate_effective_cost,
    apply_take_different_tokens,
    apply_take_same_tokens,
    apply_catch_pokemon,
    apply_reserve,
    apply_discard,
    apply_evolve,
    get_evolvable_cards,
    check_win_condition,
    refill_board_slot,
)
from tests.conftest import tokens, bonuses, make_token


# --- Bonus calculation ---

def test_bonuses_from_non_evolved_cards_only(charmander, squirtle):
    from pokemon_splendor.models import Player
    p = Player(name="P", cards=[charmander, squirtle])
    charmander.evolved = True
    bonuses_map = get_player_bonuses(p)
    assert bonuses_map.get(PokeballType.Red, 0) == 0
    assert bonuses_map.get(PokeballType.Blue, 0) == 1


def test_bonuses_summed_across_cards(charmander, squirtle):
    from pokemon_splendor.models import Player
    charmander.evolved = False
    squirtle.evolved = False
    p = Player(name="P", cards=[charmander, squirtle])
    bonuses_map = get_player_bonuses(p)
    assert bonuses_map[PokeballType.Red] == 1
    assert bonuses_map[PokeballType.Blue] == 1


# --- Effective cost ---

def test_effective_cost_reduced_by_bonus(charmander):
    from pokemon_splendor.models import Player
    p = Player(name="P", cards=[charmander])
    player_bonuses = get_player_bonuses(p)
    cost = calculate_effective_cost(charmander, player_bonuses)
    assert cost.get(PokeballType.Red, 0) == 1


def test_effective_cost_never_negative(charmander):
    from pokemon_splendor.models import Player
    extra = deepcopy(charmander)
    extra.evolved = False
    p = Player(name="P", cards=[charmander, extra, extra])
    player_bonuses = get_player_bonuses(p)
    cost = calculate_effective_cost(charmander, player_bonuses)
    assert cost.get(PokeballType.Red, 0) == 0


# --- Take different tokens ---

def test_take_1_different_token(two_player_game):
    game, p1, _ = two_player_game
    game2 = apply_take_different_tokens(game, p1, [PokeballType.Red])
    assert sum(1 for t in game2.turn.tokens if t.name == PokeballType.Red) == 1
    assert game2.tokens[PokeballType.Red] == 3


def test_take_3_different_tokens(two_player_game):
    game, p1, _ = two_player_game
    game2 = apply_take_different_tokens(game, p1, [PokeballType.Red, PokeballType.Blue, PokeballType.Yellow])
    assert len(p1.tokens) == 3
    assert game2.tokens[PokeballType.Red] == 3


def test_cannot_take_master_as_different_token(two_player_game):
    game, p1, _ = two_player_game
    with pytest.raises(ValueError, match="Master"):
        apply_take_different_tokens(game, p1, [PokeballType.Master])


def test_cannot_take_duplicate_types(two_player_game):
    game, p1, _ = two_player_game
    with pytest.raises(ValueError, match="duplicate"):
        apply_take_different_tokens(game, p1, [PokeballType.Red, PokeballType.Red])


def test_cannot_take_more_than_3(two_player_game):
    game, p1, _ = two_player_game
    with pytest.raises(ValueError):
        apply_take_different_tokens(
            game, p1,
            [PokeballType.Red, PokeballType.Blue, PokeballType.Yellow, PokeballType.Pink]
        )


def test_take_fewer_when_limited_types_available(two_player_game):
    game, p1, _ = two_player_game
    for ptype in [PokeballType.Yellow, PokeballType.Pink, PokeballType.Black]:
        game.tokens[ptype] = 0
    game2 = apply_take_different_tokens(game, p1, [PokeballType.Red, PokeballType.Blue])
    assert len(p1.tokens) == 2


def test_cannot_take_token_type_with_zero_on_board(two_player_game):
    game, p1, _ = two_player_game
    game.tokens[PokeballType.Yellow] = 0
    with pytest.raises(ValueError, match="not available"):
        apply_take_different_tokens(game, p1, [PokeballType.Red, PokeballType.Blue, PokeballType.Yellow])


# --- Take 2 same tokens ---

def test_take_2_same_valid(two_player_game):
    game, p1, _ = two_player_game
    game.tokens[PokeballType.Red] = 4
    game2 = apply_take_same_tokens(game, p1, PokeballType.Red)
    assert sum(1 for t in p1.tokens if t.name == PokeballType.Red) == 2
    assert game2.tokens[PokeballType.Red] == 2


def test_take_2_same_requires_4_on_board(two_player_game):
    game, p1, _ = two_player_game
    game.tokens[PokeballType.Red] = 3
    with pytest.raises(ValueError, match="4"):
        apply_take_same_tokens(game, p1, PokeballType.Red)


def test_cannot_take_2_master(two_player_game):
    game, p1, _ = two_player_game
    with pytest.raises(ValueError, match="Master"):
        apply_take_same_tokens(game, p1, PokeballType.Master)


# --- Catch pokemon ---

def test_catch_pays_correct_tokens(two_player_game, charmander):
    game, p1, _ = two_player_game
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    game2 = apply_catch_pokemon(game, p1, charmander, from_reserved=False, board_slot=0)
    assert charmander in p1.cards
    assert sum(1 for t in p1.tokens if t.name == PokeballType.Red) == 0
    assert game2.tokens[PokeballType.Red] == 6  # 4 + 2 returned


def test_catch_uses_bonus_as_discount(two_player_game, charmander, squirtle):
    game, p1, _ = two_player_game
    p1.cards = [squirtle]
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    game2 = apply_catch_pokemon(game, p1, charmander, from_reserved=False, board_slot=0)
    assert charmander in p1.cards


def test_catch_bonus_reduces_cost(two_player_game, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_bonus_card = Pokemon(
        name="dummy", tier=Tier.Common,
        cost=[], bonus=bonuses(PokeballType.Red),
        evolve=[], evolve_into="", point=0,
    )
    p1.cards = [red_bonus_card]
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    game.board.uncommon_revealed[0] = charmeleon
    game2 = apply_catch_pokemon(game, p1, charmeleon, from_reserved=False, board_slot=4)
    assert charmeleon in p1.cards


def test_catch_master_as_wild(two_player_game, charmander):
    game, p1, _ = two_player_game
    p1.tokens = tokens(PokeballType.Red, PokeballType.Master)
    game2 = apply_catch_pokemon(game, p1, charmander, from_reserved=False, board_slot=0)
    assert charmander in p1.cards
    assert len(p1.tokens) == 0


def test_catch_epic_requires_master(two_player_game, mewtwo):
    game, p1, _ = two_player_game
    game.board.epic_revealed[0] = mewtwo
    p1.tokens = tokens(
        PokeballType.Red, PokeballType.Red, PokeballType.Red,
        PokeballType.Red,
    )
    with pytest.raises(ValueError, match="Master"):
        apply_catch_pokemon(game, p1, mewtwo, from_reserved=False, board_slot=12)


def test_catch_epic_with_master_succeeds(two_player_game, mewtwo):
    game, p1, _ = two_player_game
    game.board.epic_revealed[0] = mewtwo
    p1.tokens = tokens(
        PokeballType.Master,
        PokeballType.Red, PokeballType.Red, PokeballType.Red,
    )
    game2 = apply_catch_pokemon(game, p1, mewtwo, from_reserved=False, board_slot=12)
    assert mewtwo in p1.cards


def test_catch_from_reserved_removes_card(two_player_game, charmander):
    game, p1, _ = two_player_game
    p1.reserved_cards = [charmander]
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    game2 = apply_catch_pokemon(game, p1, charmander, from_reserved=True, board_slot=None)
    assert charmander not in p1.reserved_cards
    assert charmander in p1.cards


def test_catch_updates_points(two_player_game, charmeleon):
    game, p1, _ = two_player_game
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red, PokeballType.Red)
    game.board.uncommon_revealed[0] = charmeleon
    apply_catch_pokemon(game, p1, charmeleon, from_reserved=False, board_slot=4)
    assert p1.points == 1


# --- Reserve ---

def test_reserve_adds_to_reserved(two_player_game, charmander):
    game, p1, _ = two_player_game
    apply_reserve(game, p1, charmander, board_slot=0, take_master=False)
    assert charmander in p1.reserved_cards


def test_reserve_with_master_gives_token(two_player_game, charmander):
    game, p1, _ = two_player_game
    apply_reserve(game, p1, charmander, board_slot=0, take_master=True)
    assert any(t.name == PokeballType.Master for t in p1.tokens)
    assert game.tokens[PokeballType.Master] == 4


def test_reserve_without_master_no_token(two_player_game, charmander):
    game, p1, _ = two_player_game
    apply_reserve(game, p1, charmander, board_slot=0, take_master=False)
    assert not any(t.name == PokeballType.Master for t in p1.tokens)


def test_reserve_max_3(two_player_game, charmander, squirtle):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    dummy = Pokemon(name="d", tier=Tier.Common, cost=[], bonus=[], evolve=[], evolve_into="", point=0)
    p1.reserved_cards = [charmander, squirtle, dummy]
    with pytest.raises(ValueError, match="3"):
        apply_reserve(game, p1, charmander, board_slot=0, take_master=False)


def test_cannot_reserve_epic(two_player_game, mewtwo):
    game, p1, _ = two_player_game
    game.board.epic_revealed[0] = mewtwo
    with pytest.raises(ValueError, match="Epic"):
        apply_reserve(game, p1, mewtwo, board_slot=12, take_master=True)


def test_cannot_reserve_when_no_master_and_take_master(two_player_game, charmander):
    game, p1, _ = two_player_game
    game.tokens[PokeballType.Master] = 0
    with pytest.raises(ValueError, match="Master"):
        apply_reserve(game, p1, charmander, board_slot=0, take_master=True)


# --- Discard ---

def test_discard_removes_one_token(two_player_game):
    game, p1, _ = two_player_game
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red, PokeballType.Blue)
    apply_discard(game, p1, PokeballType.Red)
    assert sum(1 for t in p1.tokens if t.name == PokeballType.Red) == 1
    assert game.tokens[PokeballType.Red] == 5


def test_discard_returns_token_to_board(two_player_game):
    game, p1, _ = two_player_game
    p1.tokens = tokens(PokeballType.Blue)
    apply_discard(game, p1, PokeballType.Blue)
    assert game.tokens[PokeballType.Blue] == 5


def test_cannot_discard_token_not_held(two_player_game):
    game, p1, _ = two_player_game
    p1.tokens = tokens(PokeballType.Red)
    with pytest.raises(ValueError, match="not held"):
        apply_discard(game, p1, PokeballType.Blue)


# --- Board refill ---

def test_board_refill_after_catch(two_player_game, charmander):
    from pokemon_splendor.models import Pokemon
    extra = Pokemon(name="extra", tier=Tier.Common, cost=[], bonus=[], evolve=[], evolve_into="", point=0)
    game, p1, _ = two_player_game
    game.board.common_deck = [extra]
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    apply_catch_pokemon(game, p1, charmander, from_reserved=False, board_slot=0)
    assert game.board.common_revealed[0] == extra


def test_board_slot_empty_when_deck_exhausted(two_player_game, charmander):
    game, p1, _ = two_player_game
    game.board.common_deck = []
    p1.tokens = tokens(PokeballType.Red, PokeballType.Red)
    apply_catch_pokemon(game, p1, charmander, from_reserved=False, board_slot=0)
    assert game.board.common_revealed[0] is None


# --- Evolution ---

def test_get_evolvable_cards(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    game.board.uncommon_revealed[0] = charmeleon
    evolvable = get_evolvable_cards(game, p1)
    assert any(card.name == "charmander" for card, _ in evolvable)


def test_evolvable_uses_only_non_evolved_bonuses(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    red_card.evolved = True
    p1.cards = [charmander, red_card]
    game.board.uncommon_revealed[0] = charmeleon
    evolvable = get_evolvable_cards(game, p1)
    assert evolvable == []


def test_evolve_marks_source_as_evolved(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    game.board.uncommon_revealed[0] = charmeleon
    apply_evolve(game, p1, card_index=0)
    assert charmander.evolved is True


def test_evolve_adds_evolved_form_to_collection(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    game.board.uncommon_revealed[0] = charmeleon
    apply_evolve(game, p1, card_index=0)
    assert charmeleon in p1.cards


def test_evolve_is_free(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    p1.tokens = []
    game.board.uncommon_revealed[0] = charmeleon
    apply_evolve(game, p1, card_index=0)
    assert len(p1.tokens) == 0


def test_evolve_excludes_source_from_points(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    game.board.uncommon_revealed[0] = charmeleon
    apply_evolve(game, p1, card_index=0)
    assert p1.points == charmeleon.point


def test_evolve_from_reserved(two_player_game, charmander, charmeleon):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    p1.reserved_cards = [charmeleon]
    game.board.uncommon_revealed[0] = None
    apply_evolve(game, p1, card_index=0)
    assert charmeleon in p1.cards
    assert charmeleon not in p1.reserved_cards


def test_evolve_fails_when_target_not_available(two_player_game, charmander):
    game, p1, _ = two_player_game
    from pokemon_splendor.models import Pokemon
    red_card = Pokemon(name="r", tier=Tier.Common, cost=[], bonus=bonuses(PokeballType.Red, PokeballType.Red), evolve=[], evolve_into="", point=0)
    p1.cards = [charmander, red_card]
    with pytest.raises(ValueError, match="not available"):
        apply_evolve(game, p1, card_index=0)


# --- Win condition ---

def test_win_not_triggered_below_18(two_player_game):
    game, p1, _ = two_player_game
    p1.points = 17
    assert check_win_condition(game) is None


def test_win_triggered_at_18(two_player_game):
    game, p1, _ = two_player_game
    p1.points = 18
    assert check_win_condition(game) is not None


def test_win_tiebreak_by_card_count(two_player_game):
    game, p1, p2 = two_player_game
    from pokemon_splendor.models import Pokemon
    dummy = Pokemon(name="d", tier=Tier.Common, cost=[], bonus=[], evolve=[], evolve_into="", point=0)
    p1.points = 18
    p2.points = 18
    p1.cards = [dummy]
    p2.cards = [dummy, dummy]
    winner = check_win_condition(game)
    assert winner == p2
