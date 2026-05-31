import pytest
from pokemon_splendor.models import (
    Pokemon, Player, Board, Game, Tier, PokeballType, PokeballToken, Bonus, GamePhase,
)


def make_token(ptype: PokeballType) -> PokeballToken:
    return PokeballToken(ptype)


def make_bonus(ptype: PokeballType) -> Bonus:
    return Bonus(ptype)


def tokens(*types: PokeballType) -> list[PokeballToken]:
    return [make_token(t) for t in types]


def bonuses(*types: PokeballType) -> list[Bonus]:
    return [make_bonus(t) for t in types]


@pytest.fixture
def charmander():
    return Pokemon(
        name="charmander", tier=Tier.Common,
        cost=tokens(PokeballType.Red, PokeballType.Red),
        bonus=bonuses(PokeballType.Red),
        evolve=bonuses(PokeballType.Red, PokeballType.Red),
        evolve_into="charmeleon", point=0,
    )


@pytest.fixture
def charmeleon():
    return Pokemon(
        name="charmeleon", tier=Tier.Uncommon,
        cost=tokens(PokeballType.Red, PokeballType.Red, PokeballType.Red),
        bonus=bonuses(PokeballType.Red, PokeballType.Red),
        evolve=bonuses(PokeballType.Red, PokeballType.Red, PokeballType.Red),
        evolve_into="charizard", point=1,
    )


@pytest.fixture
def squirtle():
    return Pokemon(
        name="squirtle", tier=Tier.Common,
        cost=tokens(PokeballType.Blue, PokeballType.Blue),
        bonus=bonuses(PokeballType.Blue),
        evolve=[], evolve_into="", point=0,
    )


@pytest.fixture
def mewtwo():
    return Pokemon(
        name="mewtwo", tier=Tier.Epic,
        cost=tokens(PokeballType.Master, PokeballType.Red, PokeballType.Red, PokeballType.Red),
        bonus=[], evolve=[], evolve_into="", point=8,
    )


@pytest.fixture
def two_player_game(charmander, squirtle):
    p1 = Player(name="Alice")
    p2 = Player(name="Bob")
    board = Board(
        common_revealed=[charmander, squirtle, None, None],
        uncommon_revealed=[None, None, None, None],
    )
    game = Game(
        players=[p1, p2],
        turn=p1,
        starting_player=p1,
        round=1,
        board=board,
        tokens={
            PokeballType.Red: 4,
            PokeballType.Yellow: 4,
            PokeballType.Blue: 4,
            PokeballType.Pink: 4,
            PokeballType.Black: 4,
            PokeballType.Master: 5,
        },
    )
    return game, p1, p2
