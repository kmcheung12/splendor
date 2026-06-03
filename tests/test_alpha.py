import torch
import numpy as np
import pytest
from pokemon_splendor.agents.alpha_net import AlphaNet

OBS_SIZE = 345
TOTAL_ACTIONS = 108


def test_alpha_net_policy_shape():
    net = AlphaNet()
    obs = torch.zeros(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert policy.shape == (TOTAL_ACTIONS,)


def test_alpha_net_value_shape():
    net = AlphaNet()
    obs = torch.zeros(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert value.shape == ()


def test_alpha_net_policy_sums_to_one():
    net = AlphaNet()
    obs = torch.randn(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    policy, _ = net(obs, mask)
    assert abs(policy.sum().item() - 1.0) < 1e-5


def test_alpha_net_policy_respects_mask():
    net = AlphaNet()
    obs = torch.randn(OBS_SIZE)
    mask = torch.zeros(TOTAL_ACTIONS, dtype=torch.bool)
    mask[0] = True
    mask[1] = True
    policy, _ = net(obs, mask)
    assert policy[2:].sum().item() < 1e-6
    assert abs(policy[:2].sum().item() - 1.0) < 1e-5


def test_alpha_net_value_in_range():
    net = AlphaNet()
    obs = torch.randn(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)
    _, value = net(obs, mask)
    assert 0.0 <= value.item() <= 1.0


def test_alpha_net_batch_forward():
    net = AlphaNet()
    obs = torch.randn(4, OBS_SIZE)
    mask = torch.ones(4, TOTAL_ACTIONS, dtype=torch.bool)
    policy, value = net(obs, mask)
    assert policy.shape == (4, TOTAL_ACTIONS)
    assert value.shape == (4,)


def test_alpha_net_all_masked_raises():
    net = AlphaNet()
    obs = torch.zeros(OBS_SIZE)
    mask = torch.zeros(TOTAL_ACTIONS, dtype=torch.bool)
    with pytest.raises(ValueError, match="all actions are masked"):
        net(obs, mask)


def test_alpha_net_save_load_roundtrip():
    import tempfile
    import os

    net = AlphaNet()
    obs = torch.randn(OBS_SIZE)
    mask = torch.ones(TOTAL_ACTIONS, dtype=torch.bool)

    # Get output from original network
    policy_orig, value_orig = net(obs, mask)

    # Save and load
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_net.pth")
        net.save(path)
        net_loaded = AlphaNet.load(path)

    # Get output from loaded network (should be identical)
    policy_loaded, value_loaded = net_loaded(obs, mask)

    assert torch.allclose(policy_orig, policy_loaded)
    assert torch.allclose(value_orig, value_loaded)


def test_alpha_net_load_sets_eval_mode():
    import tempfile
    import os

    net = AlphaNet()

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_net.pth")
        net.save(path)
        net_loaded = AlphaNet.load(path)

    assert net_loaded.training == False


from pokemon_splendor.agents.alpha_coach import compute_outcomes
from pokemon_splendor.models import Game, Player, Pokemon, Board, PokeballType, Tier, PokeballToken, GamePhase


def _make_player(name: str, points: int, n_cards: int) -> Player:
    cards = []
    for i in range(n_cards):
        p = Pokemon(
            name=f"card_{i}", tier=Tier.Common, cost=[], bonus=[], evolve=[],
            evolve_into=None, point=0,
        )
        cards.append(p)
    player = Player(name=name)
    player.points = points
    player.cards = cards
    return player


def test_compute_outcomes_winner_gets_one():
    p1 = _make_player("player_0", 20, 10)
    p2 = _make_player("player_1", 15, 8)
    game = _make_minimal_game([p1, p2], winner=p1)
    outcomes = compute_outcomes(game)
    assert outcomes["player_0"] == 1.0


def test_compute_outcomes_normalised_by_winner_score():
    p1 = _make_player("player_0", 20, 10)
    p2 = _make_player("player_1", 10, 10)
    game = _make_minimal_game([p1, p2], winner=p1)
    outcomes = compute_outcomes(game)
    assert abs(outcomes["player_1"] - 0.5) < 1e-6


def test_compute_outcomes_card_delta():
    p1 = _make_player("player_0", 20, 10)
    p2 = _make_player("player_1", 20, 12)
    game = _make_minimal_game([p1, p2], winner=p1)
    outcomes = compute_outcomes(game)
    # p2: 20/20 + (12-10)*0.001 = 1.002 → clamped to 1.0
    assert outcomes["player_1"] == 1.0


def test_compute_outcomes_clamped_to_zero():
    p1 = _make_player("player_0", 20, 10)
    p2 = _make_player("player_1", 0, 0)
    game = _make_minimal_game([p1, p2], winner=p1)
    outcomes = compute_outcomes(game)
    assert outcomes["player_1"] == 0.0


from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.agents.alpha_mcts import AlphaMCTSAgent
from pokemon_splendor.agents.alpha_net import AlphaNet as _AlphaNet


def _make_env_and_agent(n_sims=10):
    env = PokemonSplendorEnv(Path("data/pokemon.jsonl"), num_players=2)
    env.reset()
    name = env.agent_selection
    net = _AlphaNet()
    agent = AlphaMCTSAgent(env, name, network=net, n_simulations=n_sims, depth=2)
    return env, agent, name


def test_alpha_mcts_returns_valid_action():
    env, agent, name = _make_env_and_agent()
    obs, _, _, _, _ = env.last()
    mask = env.action_mask(name)
    action = agent.act(obs, mask)
    assert mask[action], "chosen action must be valid"


def test_alpha_mcts_visit_counts_shape():
    env, agent, name = _make_env_and_agent()
    obs, _, _, _, _ = env.last()
    mask = env.action_mask(name)
    agent.act(obs, mask)
    visit_counts = agent.last_visit_counts
    assert len(visit_counts) == 108
    assert abs(sum(visit_counts) - 1.0) < 1e-5


def test_alpha_mcts_visit_counts_only_valid():
    env, agent, name = _make_env_and_agent()
    obs, _, _, _, _ = env.last()
    mask = env.action_mask(name)
    agent.act(obs, mask)
    for i, prob in enumerate(agent.last_visit_counts):
        if not mask[i]:
            assert prob == 0.0, f"invalid action {i} has non-zero visit count"


def _make_minimal_game(players, winner):
    from pokemon_splendor.models import Board, PokeballType, GamePhase
    board = Board()
    game = Game(
        players=players,
        turn=players[0],
        starting_player=players[0],
        round=1,
        board=board,
        tokens={pt: 4 for pt in PokeballType},
    )
    game.winner = winner
    return game


from pokemon_splendor.agents.alpha_coach import run_self_play_game, SelfPlayRecord


def test_self_play_game_returns_records():
    net = AlphaNet()
    records = run_self_play_game(Path("data/pokemon.jsonl"), net, num_players=2, n_simulations=5, depth=1)
    assert len(records) > 0


def test_self_play_record_fields():
    net = AlphaNet()
    records = run_self_play_game(Path("data/pokemon.jsonl"), net, num_players=2, n_simulations=5, depth=1)
    r = records[0]
    assert r.obs.shape == (345,)
    assert len(r.visit_counts) == 108
    assert abs(sum(r.visit_counts) - 1.0) < 1e-5
    assert 0.0 <= r.outcome <= 1.0


def test_self_play_game_produces_moves():
    net = AlphaNet()
    records = run_self_play_game(Path("data/pokemon.jsonl"), net, num_players=2, n_simulations=5, depth=1)
    assert len(records) >= 10


from pokemon_splendor.agents.alpha_coach import train_step


def test_train_step_returns_losses():
    net = AlphaNet()
    optimizer = torch.optim.Adam(net.parameters(), lr=0.001)
    batch = [
        SelfPlayRecord(
            obs=np.random.rand(345).astype(np.float32),
            visit_counts=[1.0 / 108] * 108,
            outcome=0.5,
        )
        for _ in range(8)
    ]
    policy_loss, value_loss = train_step(net, optimizer, batch)
    assert policy_loss >= 0.0
    assert value_loss >= 0.0


def test_train_step_updates_weights():
    net = AlphaNet()
    optimizer = torch.optim.Adam(net.parameters(), lr=0.01)
    batch = [
        SelfPlayRecord(
            obs=np.random.rand(345).astype(np.float32),
            visit_counts=[1.0 / 108] * 108,
            outcome=1.0,
        )
        for _ in range(8)
    ]
    before = net.value_head.weight.data.clone()
    train_step(net, optimizer, batch)
    after = net.value_head.weight.data
    assert not torch.allclose(before, after)


import tempfile
import os
from pokemon_splendor.agents.alpha_coach import AlphaCoach


def test_alpha_coach_runs_one_iteration():
    with tempfile.TemporaryDirectory() as tmpdir:
        coach = AlphaCoach(
            jsonl_path=Path("data/pokemon.jsonl"),
            num_players=2,
            n_iterations=1,
            games_per_iteration=2,
            n_simulations=5,
            depth=1,
            batch_size=4,
            buffer_size=100,
            checkpoint_dir=tmpdir,
        )
        coach.run()
        files = os.listdir(tmpdir)
        assert any(f.endswith(".pt") for f in files)


def test_alpha_coach_saves_checkpoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        coach = AlphaCoach(
            jsonl_path=Path("data/pokemon.jsonl"),
            num_players=2,
            n_iterations=2,
            games_per_iteration=2,
            n_simulations=5,
            depth=1,
            batch_size=4,
            buffer_size=100,
            checkpoint_dir=tmpdir,
        )
        coach.run()
        files = os.listdir(tmpdir)
        pt_files = {f for f in files if f.endswith(".pt")}
        assert pt_files == {"alpha_0001.pt", "alpha_0002.pt"}
