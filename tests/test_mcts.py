# tests/test_mcts.py
import pytest
from collections import Counter
from pokemon_splendor.engine.eval import evaluate_position, WIN_SCORE
from pokemon_splendor.models import (
    Player, Pokemon, Board, Game, Tier, PokeballType, PokeballToken, Bonus,
)


def _token(pt): return PokeballToken(pt)
def _bonus(pt): return Bonus(pt)

def _card(name, tier, point, cost_types=(), bonus_types=()):
    return Pokemon(
        name=name, tier=tier, point=point,
        cost=[_token(pt) for pt in cost_types],
        bonus=[_bonus(pt) for pt in bonus_types],
        evolve=[], evolve_into="",
    )

def _make_game(players, board=None):
    if board is None:
        board = Board()
    return Game(
        players=players, turn=players[0], starting_player=players[0],
        round=1, board=board, tokens={pt: 4 for pt in PokeballType},
    )


def test_evaluate_position_no_board():
    player = Player(name="p1")
    player.points = 3
    opponent = Player(name="p2")
    game = _make_game([player, opponent])
    result = evaluate_position(game, player)
    assert result == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_affordable_now():
    """Card with shortfall=0: rounds=0, contribution = point / 1."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    free_card = _card("free", Tier.Common, point=3)
    board = Board(common_revealed=[free_card, None, None, None])
    game = _make_game([player, opponent], board)
    # alpha = 1.0 / (2-1) = 1.0; val = 0 + 1.0 * (3/1) = 3.0; result = 3/18
    assert evaluate_position(game, player) == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_one_turn_away():
    """Card costs 3 tokens, player has 0: shortfall=3, rounds=ceil(3/3)=1, contribution=point/2."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    card = _card("c", Tier.Common, point=6,
                 cost_types=(PokeballType.Red, PokeballType.Blue, PokeballType.Yellow))
    board = Board(common_revealed=[card, None, None, None])
    game = _make_game([player, opponent], board)
    # rounds = ceil(3/3) = 1; val = 6/2 = 3.0
    assert evaluate_position(game, player) == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_two_turns_away():
    """Shortfall=4 tokens: rounds=ceil(4/3)=2, contribution=point/3."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    card = _card("c", Tier.Common, point=6,
                 cost_types=(PokeballType.Red,) * 4)
    board = Board(common_revealed=[card, None, None, None])
    game = _make_game([player, opponent], board)
    assert evaluate_position(game, player) == pytest.approx(6.0 / 3.0 / WIN_SCORE)


def test_evaluate_position_takes_max_not_sum():
    """Two cards: 2pt affordable now vs 9pt two turns away. max(2/1, 9/3)=3."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    cheap = _card("cheap", Tier.Common, point=2)
    expensive = _card("exp", Tier.Common, point=9,
                      cost_types=(PokeballType.Red,) * 4)
    board = Board(common_revealed=[cheap, expensive, None, None])
    game = _make_game([player, opponent], board)
    assert evaluate_position(game, player) == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_epic_requires_master():
    """Epic card with no master token: skipped, max_val stays 0."""
    player = Player(name="p1")
    player.points = 2
    opponent = Player(name="p2")
    epic = _card("epic", Tier.Epic, point=8)
    board = Board(epic_revealed=[epic])
    game = _make_game([player, opponent], board)
    assert evaluate_position(game, player) == pytest.approx(2.0 / WIN_SCORE)


def test_evaluate_position_alpha_scales_with_players():
    """4-player game: alpha = 1/(4-1) = 1/3. Free 3pt card → val = 0 + (1/3)*3 = 1."""
    players = [Player(name=f"p{i}") for i in range(4)]
    free_card = _card("free", Tier.Common, point=3)
    board = Board(common_revealed=[free_card, None, None, None])
    game = _make_game(players, board)
    assert evaluate_position(game, players[0]) == pytest.approx(1.0 / WIN_SCORE, rel=1e-3)
