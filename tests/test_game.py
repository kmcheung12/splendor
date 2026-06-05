import numpy as np
import pytest
from pokemon_splendor.engine.env import PokemonSplendorEnv, _phi, _shaping, GAMMA_SHAPING, WIN_SCORE
from pokemon_splendor.engine.actions import TOTAL_ACTIONS
from pokemon_splendor.models import (
    Player, Pokemon, Board, Game, Tier, PokeballType, PokeballToken, Bonus,
)
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _token(pt: PokeballType) -> PokeballToken:
    return PokeballToken(pt)

def _bonus(pt: PokeballType) -> Bonus:
    return Bonus(pt)

def _make_game(players, board=None):
    if board is None:
        board = Board()
    return Game(
        players=players,
        turn=players[0],
        starting_player=players[0],
        round=1,
        board=board,
        tokens={pt: 4 for pt in PokeballType},
    )

def _card(name, tier, point, cost_types=(), bonus_types=()):
    return Pokemon(
        name=name, tier=tier, point=point,
        cost=[_token(pt) for pt in cost_types],
        bonus=[_bonus(pt) for pt in bonus_types],
        evolve=[], evolve_into="",
    )


# ---------------------------------------------------------------------------
# _phi tests
# ---------------------------------------------------------------------------

def test_phi_no_affordable_cards():
    """Player with 3 points and no affordable cards on board: Φ = 3."""
    player = Player(name="p1")
    player.points = 3
    opponent = Player(name="p2")
    game = _make_game([player, opponent])
    # Board is empty (all None slots by default)
    assert _phi(player, game) == pytest.approx(3.0)


def test_phi_affordable_card_adds_alpha_times_points():
    """2-player game: α=1.0. Card worth 2 pts is free (no cost). Φ = 3 + 1.0×2 = 5."""
    player = Player(name="p1")
    player.points = 3
    opponent = Player(name="p2")
    free_card = _card("free", Tier.Common, point=2)
    board = Board(common_revealed=[free_card, None, None, None])
    game = _make_game([player, opponent], board)
    assert _phi(player, game) == pytest.approx(5.0)


def test_phi_only_max_not_sum():
    """Two affordable cards worth 2 and 5 pts: Φ = points + α×5 (max, not sum)."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    low = _card("low", Tier.Common, point=2)
    high = _card("high", Tier.Common, point=5)
    board = Board(common_revealed=[low, high, None, None])
    game = _make_game([player, opponent], board)
    assert _phi(player, game) == pytest.approx(5.0)  # 0 + 1.0×5


def test_phi_unaffordable_card_ignored():
    """Card costs 3 red tokens; player has 0 tokens: not affordable, max_pts=0."""
    player = Player(name="p1")
    player.points = 2
    opponent = Player(name="p2")
    expensive = _card("exp", Tier.Common, point=5,
                      cost_types=(PokeballType.Red, PokeballType.Red, PokeballType.Red))
    board = Board(common_revealed=[expensive, None, None, None])
    game = _make_game([player, opponent], board)
    assert _phi(player, game) == pytest.approx(2.0)


def test_phi_bonus_covers_cost():
    """Player has 2 red bonuses; card costs 2 red. Effective cost=0 → affordable."""
    player = Player(name="p1")
    player.points = 1
    player.cards = [
        _card("r1", Tier.Common, point=0, bonus_types=(PokeballType.Red,)),
        _card("r2", Tier.Common, point=0, bonus_types=(PokeballType.Red,)),
    ]
    opponent = Player(name="p2")
    card = _card("target", Tier.Common, point=3,
                 cost_types=(PokeballType.Red, PokeballType.Red))
    board = Board(common_revealed=[card, None, None, None])
    game = _make_game([player, opponent], board)
    assert _phi(player, game) == pytest.approx(4.0)  # 1 + 1.0×3


def test_phi_alpha_diminishes_with_players():
    """4-player game: α = 1/(4-1) ≈ 0.333. Free 3-pt card → Φ = 0 + 0.333×3 = 1."""
    players = [Player(name=f"p{i}") for i in range(4)]
    free_card = _card("free", Tier.Common, point=3)
    board = Board(common_revealed=[free_card, None, None, None])
    game = _make_game(players, board)
    assert _phi(players[0], game) == pytest.approx(1.0, rel=1e-3)


def test_phi_epic_requires_master_token():
    """Epic card needs a Master token; player has none → not affordable."""
    player = Player(name="p1")
    player.points = 0
    # Give enough colour tokens to cover the colour cost
    player.tokens = [_token(PokeballType.Red)] * 3
    opponent = Player(name="p2")
    epic = _card("epic", Tier.Epic, point=8,
                 cost_types=(PokeballType.Red, PokeballType.Red, PokeballType.Red))
    board = Board(epic_revealed=[epic])
    game = _make_game([player, opponent], board)
    assert _phi(player, game) == pytest.approx(0.0)


def test_phi_epic_with_master_token():
    """Epic card; player has Master token and enough colours → affordable."""
    player = Player(name="p1")
    player.points = 0
    player.tokens = [_token(PokeballType.Master), _token(PokeballType.Red),
                     _token(PokeballType.Red), _token(PokeballType.Red)]
    opponent = Player(name="p2")
    epic = _card("epic", Tier.Epic, point=8,
                 cost_types=(PokeballType.Red, PokeballType.Red, PokeballType.Red))
    board = Board(epic_revealed=[epic])
    game = _make_game([player, opponent], board)
    assert _phi(player, game) == pytest.approx(8.0)  # 0 + 1.0×8


# ---------------------------------------------------------------------------
# _shaping tests
# ---------------------------------------------------------------------------

def test_shaping_positive_when_potential_increases():
    """If Φ goes from 2 to 4, shaping should be positive."""
    f = _shaping(2.0, 4.0)
    assert f > 0


def test_shaping_negative_when_potential_decreases():
    """If Φ goes from 5 to 2, shaping should be negative."""
    f = _shaping(5.0, 2.0)
    assert f < 0


def test_shaping_zero_when_no_change():
    """Φ before == Φ after: shaping ≈ -(1-γ)Φ/WIN_SCORE (small negative discount leak)."""
    phi = 3.0
    f = _shaping(phi, phi)
    expected = (GAMMA_SHAPING * phi - phi) / WIN_SCORE
    assert f == pytest.approx(expected)


def test_shaping_magnitude():
    """Manual check: _shaping(5, 7) = (0.99×7 - 5) / 18."""
    expected = (GAMMA_SHAPING * 7.0 - 5.0) / WIN_SCORE
    assert _shaping(5.0, 7.0) == pytest.approx(expected)


def test_shaping_scaled_by_win_score():
    """Max single-step shaping (0 → WIN_SCORE) is at most γ, i.e. < 1."""
    f = _shaping(0.0, WIN_SCORE)
    assert abs(f) < 1.0


JSONL = Path("data/pokemon.jsonl")


@pytest.fixture
def env():
    e = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    e.reset()
    return e


# ---------------------------------------------------------------------------
# Shaping fires on catch only, not on token-taking
# ---------------------------------------------------------------------------

def _take_diff_action(env, agent):
    """Return the first take-different-tokens action index, or None."""
    from pokemon_splendor.engine.actions import TAKE_DIFF_START, TAKE_SAME_START
    mask = env.action_mask(agent)
    for a in range(TAKE_DIFF_START, TAKE_SAME_START):
        if mask[a]:
            return a
    return None


def _catch_board_action(env, agent):
    """Return the first catch-from-board action index, or None."""
    from pokemon_splendor.engine.actions import CATCH_BOARD_START, CATCH_RESERVED_START
    mask = env.action_mask(agent)
    for a in range(CATCH_BOARD_START, CATCH_RESERVED_START):
        if mask[a]:
            return a
    return None


def test_token_taking_yields_no_shaping_reward(env):
    """Taking tokens gives no shaping reward — only catches do."""
    agent = env.agent_selection
    action = _take_diff_action(env, agent)
    if action is None:
        pytest.skip("No take-different-tokens action available in this game state")
    player = next(p for p in env.game.players if p.name == agent)
    env.rewards[agent] = 0.0
    env._apply_action(player, action)
    assert env.rewards[agent] == pytest.approx(0.0)


def test_catch_yields_nonzero_shaping_reward():
    """Catching an affordable card must produce a non-zero shaping reward."""
    from pokemon_splendor.engine.env import PokemonSplendorEnv
    from pokemon_splendor.engine.actions import CATCH_BOARD_START, CATCH_RESERVED_START

    e = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    e.reset()
    agent = e.agent_selection

    # Give the agent enough tokens to guarantee a catch is available
    player = next(p for p in e.game.players if p.name == agent)
    from pokemon_splendor.models import PokeballToken
    for pt in [PokeballType.Red, PokeballType.Blue, PokeballType.Yellow,
               PokeballType.Pink, PokeballType.Black]:
        player.tokens.extend([PokeballToken(pt)] * 4)

    action = _catch_board_action(e, agent)
    if action is None:
        pytest.skip("No catch action available after token injection")

    e.rewards[agent] = 0.0
    # Apply just the action without stepping the full env loop
    e._apply_action(player, action)
    assert e.rewards[agent] != 0.0, "Catching a card should produce a non-zero shaping reward"


def test_env_resets_without_error():
    env = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    env.reset()


def test_action_space_size(env):
    for agent in env.agents:
        assert env.action_space(agent).n == TOTAL_ACTIONS


def test_observation_is_numpy_array(env):
    agent = env.agent_selection
    obs, _, _, _, _ = env.last()
    assert isinstance(obs, np.ndarray)


def test_action_mask_is_boolean_array(env):
    agent = env.agent_selection
    mask = env.action_mask(agent)
    assert mask.dtype == bool
    assert len(mask) == TOTAL_ACTIONS


def test_action_mask_has_at_least_one_valid_action(env):
    agent = env.agent_selection
    mask = env.action_mask(agent)
    assert mask.any()


def test_random_game_terminates():
    import random
    env = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    env.reset()
    for _ in range(10000):
        if not env.agents:
            break
        agent = env.agent_selection
        mask = env.action_mask(agent)
        valid = np.where(mask)[0]
        action = random.choice(valid)
        env.step(action)
    assert not env.agents, "Game did not terminate within 10000 steps"


def test_winner_declared_at_end():
    import random
    env = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    env.reset()
    for _ in range(10000):
        if not env.agents:
            break
        agent = env.agent_selection
        mask = env.action_mask(agent)
        valid = np.where(mask)[0]
        env.step(random.choice(valid))
    rewards = env.rewards
    assert any(r == 1.0 for r in rewards.values())
    assert any(r == -1.0 for r in rewards.values())


def test_win_deferred_until_round_complete():
    """Game must not end until all players finish the round after 18-pt trigger."""
    import copy
    env = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    env.reset()
    game = env.game

    # Give player_0 enough points to trigger win condition
    player_0 = next(p for p in game.players if p.name == "player_0")
    player_1 = next(p for p in game.players if p.name == "player_1")
    player_0.points = 18

    # Ensure it's player_0's turn and player_1 hasn't gone yet this round
    game.turn = player_0
    game.starting_player = player_0
    # Re-sync the agent selector so it points at player_0
    from pettingzoo.utils.agent_selector import agent_selector
    env._agent_selector = agent_selector(["player_0", "player_1"])
    env.agent_selection = env._agent_selector.reset()
    assert env.agent_selection == "player_0"

    # player_0 takes a valid action (take 1 red token if available, else any valid action)
    mask = env.action_mask("player_0")
    assert mask.any(), "player_0 must have a valid action"
    action = int(np.where(mask)[0][0])
    env.step(action)

    # After player_0's turn, game should NOT be terminated (player_1 still needs to go)
    assert env.agents, "Game should not end until all players complete the round"
    assert not env.terminations.get("player_0", False)

    # player_1 takes their turn
    assert env.agent_selection == "player_1"
    mask = env.action_mask("player_1")
    action = int(np.where(mask)[0][0])
    env.step(action)

    # Now the round is complete — game should be terminated
    assert not env.agents or all(env.terminations.values()), \
        "Game should end after all players complete the round"
