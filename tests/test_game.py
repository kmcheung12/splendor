import numpy as np
import pytest
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.engine.actions import TOTAL_ACTIONS
from pathlib import Path

JSONL = Path("data/pokemon.jsonl")


@pytest.fixture
def env():
    e = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    e.reset()
    return e


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
