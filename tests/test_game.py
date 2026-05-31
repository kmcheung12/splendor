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
