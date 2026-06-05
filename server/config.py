from dataclasses import dataclass, field


@dataclass
class SlotConfig:
    index: int
    agent_type: str  # "random", "mcts", "early-capture", etc.


@dataclass
class GameConfig:
    num_players: int
    slots: list[SlotConfig]
    delay_ms: int = 800
    first_player_index: int | None = None

    def __post_init__(self):
        assert 2 <= self.num_players <= 4
        assert len(self.slots) == self.num_players
        assert self.delay_ms >= 0
