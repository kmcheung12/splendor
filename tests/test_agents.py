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


def test_early_capture_catches_when_affordable(env, agent_name, player):
    from pokemon_splendor.agents.early_capture import EarlyCaptureAgent

    # Place a 1-red card at board slot 0 and give player exactly 1 red token
    cheap = Pokemon(
        name="cheap", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Red)],
        bonus=[Bonus(PokeballType.Red)],
        evolve=[], evolve_into="", point=1,
    )
    env.game.board.common_revealed[0] = cheap
    player.tokens = [PokeballToken(PokeballType.Red)]

    agent = EarlyCaptureAgent(env, agent_name)
    mask = env.action_mask(agent_name)
    action = agent.act(np.zeros(env._obs_size()), mask)
    assert action == CATCH_BOARD_START + 0


def test_early_capture_picks_cheapest_among_catchable(env, agent_name, player):
    from pokemon_splendor.agents.early_capture import EarlyCaptureAgent

    cheap = Pokemon(
        name="cheap", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Red)],
        bonus=[], evolve=[], evolve_into="", point=1,
    )
    expensive = Pokemon(
        name="expensive", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Red), PokeballToken(PokeballType.Blue)],
        bonus=[], evolve=[], evolve_into="", point=3,
    )
    env.game.board.common_revealed[0] = cheap
    env.game.board.common_revealed[1] = expensive
    player.tokens = [
        PokeballToken(PokeballType.Red),
        PokeballToken(PokeballType.Blue),
    ]

    agent = EarlyCaptureAgent(env, agent_name)
    mask = env.action_mask(agent_name)
    action = agent.act(np.zeros(env._obs_size()), mask)
    assert action == CATCH_BOARD_START + 0  # picks cheaper card


def test_high_point_prefers_higher_points(env, agent_name, player):
    from pokemon_splendor.agents.high_point import HighPointCaptureAgent

    low_pts = Pokemon(
        name="low", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Red)],
        bonus=[], evolve=[], evolve_into="", point=1,
    )
    high_pts = Pokemon(
        name="high", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Blue)],
        bonus=[], evolve=[], evolve_into="", point=5,
    )
    env.game.board.common_revealed[0] = low_pts
    env.game.board.common_revealed[1] = high_pts
    player.tokens = [
        PokeballToken(PokeballType.Red),
        PokeballToken(PokeballType.Blue),
    ]

    agent = HighPointCaptureAgent(env, agent_name)
    mask = env.action_mask(agent_name)
    action = agent.act(np.zeros(env._obs_size()), mask)
    assert action == CATCH_BOARD_START + 1  # picks higher-point card
