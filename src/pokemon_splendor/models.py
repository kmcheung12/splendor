from dataclasses import dataclass, field
from enum import Enum


class PokeballType(Enum):
    Red = "red"
    Yellow = "yellow"
    Blue = "blue"
    Pink = "pink"
    Black = "black"
    Master = "master"


@dataclass
class PokeballToken:
    name: PokeballType


@dataclass
class Bonus(PokeballToken):
    pass


class Tier(Enum):
    Common = "common"
    Uncommon = "uncommon"
    Rare = "rare"
    Epic = "epic"
    Legendary = "legendary"


class GamePhase(Enum):
    MAIN = "main"
    DISCARD = "discard"
    EVOLVE = "evolve"


@dataclass
class Pokemon:
    name: str
    tier: Tier
    cost: list[PokeballToken]
    bonus: list[Bonus]
    evolve: list[Bonus]
    evolve_into: str
    point: int
    evolved: bool = False


@dataclass
class Player:
    name: str
    tokens: list[PokeballToken] = field(default_factory=list)
    cards: list[Pokemon] = field(default_factory=list)
    reserved_cards: list[Pokemon] = field(default_factory=list)
    points: int = 0


@dataclass
class Board:
    common_deck: list[Pokemon] = field(default_factory=list)
    uncommon_deck: list[Pokemon] = field(default_factory=list)
    rare_deck: list[Pokemon] = field(default_factory=list)
    epic_deck: list[Pokemon] = field(default_factory=list)
    legendary_deck: list[Pokemon] = field(default_factory=list)
    common_revealed: list[Pokemon | None] = field(default_factory=lambda: [None] * 4)
    uncommon_revealed: list[Pokemon | None] = field(default_factory=lambda: [None] * 4)
    rare_revealed: list[Pokemon | None] = field(default_factory=lambda: [None] * 4)
    epic_revealed: list[Pokemon | None] = field(default_factory=lambda: [None] * 1)
    legendary_revealed: list[Pokemon | None] = field(default_factory=lambda: [None] * 1)


@dataclass
class Game:
    players: list[Player]
    turn: Player
    starting_player: Player
    round: int
    board: Board
    tokens: dict[PokeballType, int]
    phase: GamePhase = GamePhase.MAIN
    evolved_this_turn: bool = False
    win_triggered: bool = False
    winner: Player | None = None
