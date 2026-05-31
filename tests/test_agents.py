# tests/test_agents.py
import pytest
import numpy as np
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.engine.actions import (
    CATCH_BOARD_START, CATCH_RESERVED_START, RESERVE_MASTER_START,
    RESERVE_NO_MASTER_START, DISCARD_START, EVOLVE_START, EVOLVE_PASS,
    TAKE_DIFF_START, TAKE_SAME_START, TAKE_DIFF_COMBOS, DISCARD_ACTION,
)
from pokemon_splendor.models import PokeballType, PokeballToken, Pokemon, Tier, Bonus

JSONL = Path("data/pokemon.jsonl")


@pytest.fixture
def env():
    e = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    e.reset()
    return e


@pytest.fixture
def agent_name(env):
    return env.agent_selection


@pytest.fixture
def player(env, agent_name):
    return next(p for p in env.game.players if p.name == agent_name)


def test_describe_action_take_diff(env, agent_name, player):
    from pokemon_splendor.agents.base import describe_action
    desc = describe_action(TAKE_DIFF_START, env.game, player)
    assert "Take" in desc


def test_describe_action_catch_board(env, agent_name, player):
    from pokemon_splendor.agents.base import describe_action
    # Find a filled board slot
    all_slots = (
        env.game.board.common_revealed + env.game.board.uncommon_revealed +
        env.game.board.rare_revealed + env.game.board.epic_revealed +
        env.game.board.legendary_revealed
    )
    for i, p in enumerate(all_slots):
        if p is not None:
            desc = describe_action(CATCH_BOARD_START + i, env.game, player)
            assert p.name in desc
            break


def test_describe_action_discard(env, agent_name, player):
    from pokemon_splendor.agents.base import describe_action
    desc = describe_action(DISCARD_START, env.game, player)
    assert "Discard" in desc


def test_describe_action_evolve_pass(env, agent_name, player):
    from pokemon_splendor.agents.base import describe_action
    desc = describe_action(EVOLVE_PASS, env.game, player)
    assert "Pass" in desc


def test_random_agent_returns_valid_action(env, agent_name):
    from pokemon_splendor.agents.random import RandomAgent
    agent = RandomAgent()
    mask = env.action_mask(agent_name)
    action = agent.act(np.zeros(env._obs_size()), mask)
    assert mask[action]


def test_human_agent_reads_stdin(env, agent_name, monkeypatch):
    from pokemon_splendor.agents.human import HumanAgent
    agent = HumanAgent(env, agent_name)
    mask = env.action_mask(agent_name)
    # Mock stdin to select action 0
    monkeypatch.setattr("builtins.input", lambda _: "0")
    action = agent.act(np.zeros(env._obs_size()), mask)
    assert mask[action]


def test_human_agent_retries_on_bad_input(env, agent_name, monkeypatch):
    from pokemon_splendor.agents.human import HumanAgent
    agent = HumanAgent(env, agent_name)
    mask = env.action_mask(agent_name)
    responses = iter(["bad", "-1", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(responses))
    action = agent.act(np.zeros(env._obs_size()), mask)
    assert mask[action]
