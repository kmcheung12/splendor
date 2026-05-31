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


def test_bonus_engine_prefers_bonus_below_threshold(env, agent_name, player):
    from pokemon_splendor.agents.bonus_engine import BonusEngineAgent

    low_bonus = Pokemon(
        name="low_bonus", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Red)],
        bonus=[Bonus(PokeballType.Red)],  # 1 bonus token
        evolve=[], evolve_into="", point=3,
    )
    high_bonus = Pokemon(
        name="high_bonus", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Blue)],
        bonus=[Bonus(PokeballType.Blue), Bonus(PokeballType.Blue)],  # 2 bonus tokens
        evolve=[], evolve_into="", point=1,
    )
    env.game.board.common_revealed[0] = low_bonus
    env.game.board.common_revealed[1] = high_bonus
    player.tokens = [
        PokeballToken(PokeballType.Red),
        PokeballToken(PokeballType.Blue),
    ]
    player.cards = []  # 0 bonuses so far — below threshold

    agent = BonusEngineAgent(env, agent_name)
    mask = env.action_mask(agent_name)
    action = agent.act(np.zeros(env._obs_size()), mask)
    assert action == CATCH_BOARD_START + 1  # prefers high-bonus card despite lower points


def test_bonus_engine_switches_to_points_above_threshold(env, agent_name, player):
    from pokemon_splendor.agents.bonus_engine import BonusEngineAgent

    low_pts = Pokemon(
        name="low", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Red)],
        bonus=[Bonus(PokeballType.Red), Bonus(PokeballType.Red)],
        evolve=[], evolve_into="", point=1,
    )
    high_pts = Pokemon(
        name="high", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Blue)],
        bonus=[],
        evolve=[], evolve_into="", point=5,
    )
    env.game.board.common_revealed[0] = low_pts
    env.game.board.common_revealed[1] = high_pts
    player.tokens = [
        PokeballToken(PokeballType.Red),
        PokeballToken(PokeballType.Blue),
    ]
    # Give player 5 bonus tokens already (above threshold)
    dummy = Pokemon(
        name="d", tier=Tier.Common, cost=[],
        bonus=[Bonus(PokeballType.Red)] * 5,
        evolve=[], evolve_into="", point=0,
    )
    player.cards = [dummy]

    agent = BonusEngineAgent(env, agent_name)
    mask = env.action_mask(agent_name)
    action = agent.act(np.zeros(env._obs_size()), mask)
    assert action == CATCH_BOARD_START + 1  # switches to points above threshold


def test_evolution_chain_targets_chain_base(env, agent_name, player):
    from pokemon_splendor.agents.evolution_chain import EvolutionChainAgent

    # base has chain value 0+3=3; standalone has value 2 but no chain
    base = Pokemon(
        name="base", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Red)],
        bonus=[Bonus(PokeballType.Red)],
        evolve=[], evolve_into="evolved_form", point=0,
    )
    evolved_form = Pokemon(
        name="evolved_form", tier=Tier.Uncommon,
        cost=[PokeballToken(PokeballType.Red), PokeballToken(PokeballType.Red)],
        bonus=[], evolve=[], evolve_into="", point=3,
    )
    standalone = Pokemon(
        name="standalone", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Blue)],
        bonus=[], evolve=[], evolve_into="", point=2,
    )
    env.game.board.common_revealed[0] = base
    env.game.board.common_revealed[1] = standalone
    env.game.board.uncommon_revealed[0] = evolved_form
    player.tokens = [
        PokeballToken(PokeballType.Red),
        PokeballToken(PokeballType.Blue),
    ]

    agent = EvolutionChainAgent(env, agent_name)
    mask = env.action_mask(agent_name)
    action = agent.act(np.zeros(env._obs_size()), mask)
    # base + evolved_form chain = 3pts vs standalone = 2pts → should pick base
    assert action == CATCH_BOARD_START + 0


def test_denial_reserves_opponent_target(env, agent_name, player):
    from pokemon_splendor.agents.denial import DenialAgent

    opp = next(p for p in env.game.players if p.name != agent_name)

    # Place a card slot 0 that opponent can almost afford
    target_card = Pokemon(
        name="target", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Red)],
        bonus=[], evolve=[], evolve_into="", point=3,
    )
    irrelevant = Pokemon(
        name="irrelevant", tier=Tier.Common,
        cost=[PokeballToken(PokeballType.Red)] * 5,
        bonus=[], evolve=[], evolve_into="", point=1,
    )
    env.game.board.common_revealed[0] = target_card
    env.game.board.common_revealed[1] = irrelevant
    # Opponent has 0 tokens but needs only 1 red (1 round shortfall)
    opp.tokens = []
    # Our player has no tokens but can still reserve
    player.tokens = []
    player.reserved_cards = []

    agent = DenialAgent(env, agent_name)
    mask = env.action_mask(agent_name)
    action = agent.act(np.zeros(env._obs_size()), mask)
    # Should be a RESERVE action for slot 0 (the target card)
    assert action in (RESERVE_MASTER_START, RESERVE_NO_MASTER_START)


def test_single_agent_env_resets():
    from pokemon_splendor.agents.rl import SingleAgentEnv
    wrapped = SingleAgentEnv(JSONL, num_players=2)
    obs, info = wrapped.reset()
    assert isinstance(obs, np.ndarray)


def test_single_agent_env_step():
    from pokemon_splendor.agents.rl import SingleAgentEnv
    wrapped = SingleAgentEnv(JSONL, num_players=2)
    wrapped.reset()
    mask = wrapped.action_masks()
    action = int(np.where(mask)[0][0])
    obs, reward, term, trunc, info = wrapped.step(action)
    assert isinstance(obs, np.ndarray)


def test_rl_agent_acts_after_training(tmp_path):
    from pokemon_splendor.agents.rl import SingleAgentEnv, RLAgent
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.wrappers import ActionMasker

    def mask_fn(env):
        return env.action_masks()

    wrapped = ActionMasker(SingleAgentEnv(JSONL, num_players=2), mask_fn)
    model = MaskablePPO("MlpPolicy", wrapped, verbose=0)
    model.learn(total_timesteps=200)
    model_path = str(tmp_path / "test_model")
    model.save(model_path)

    env = PokemonSplendorEnv(JSONL, num_players=2)
    env.reset()
    agent_name = env.agent_selection
    obs, _, _, _, _ = env.last()
    mask = env.action_mask(agent_name)

    agent = RLAgent(model_path + ".zip")
    action = agent.act(obs, mask)
    assert mask[action]


@pytest.mark.parametrize("agent_type", [
    "random", "early-capture", "high-point",
    "bonus-engine", "evolution-chain", "denial",
])
def test_agent_completes_full_game(agent_type, env):
    """Each rule-based agent plays a full game without error."""
    from pokemon_splendor.__main__ import _make_agent, _call_agent

    agent_name = env.agent_selection
    agent = _make_agent(agent_type, env=env, player_name=agent_name)

    for _ in range(10000):
        if not env.agents:
            break
        current = env.agent_selection
        obs, _, term, trunc, _ = env.last()
        if term or trunc:
            break
        mask = env.action_mask(current)
        if current == agent_name:
            action = _call_agent(agent, obs, mask)
        else:
            action = int(np.where(mask)[0][0])
        env.step(action)

    # Game must end
    assert not env.agents or all(env.terminations.values())
