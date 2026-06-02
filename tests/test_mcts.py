# tests/test_mcts.py
import pytest
from collections import Counter
from pokemon_splendor.engine.eval import evaluate_position, WIN_SCORE
from pokemon_splendor.models import (
    Player, Pokemon, Board, Game, Tier, PokeballType, PokeballToken, Bonus,
)


def _token(pt): return PokeballToken(pt)
def _bonus(pt): return Bonus(pt)

def _card(name, tier, point, cost_types=(), bonus_types=()):
    return Pokemon(
        name=name, tier=tier, point=point,
        cost=[_token(pt) for pt in cost_types],
        bonus=[_bonus(pt) for pt in bonus_types],
        evolve=[], evolve_into="",
    )

def _make_game(players, board=None):
    if board is None:
        board = Board()
    return Game(
        players=players, turn=players[0], starting_player=players[0],
        round=1, board=board, tokens={pt: 4 for pt in PokeballType},
    )


def test_evaluate_position_no_board():
    player = Player(name="p1")
    player.points = 3
    opponent = Player(name="p2")
    game = _make_game([player, opponent])
    result = evaluate_position(game, player)
    assert result == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_affordable_now():
    """Card with shortfall=0: rounds=0, contribution = point / 1."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    free_card = _card("free", Tier.Common, point=3)
    board = Board(common_revealed=[free_card, None, None, None])
    game = _make_game([player, opponent], board)
    # alpha = 1.0 / (2-1) = 1.0; val = 0 + 1.0 * (3/1) = 3.0; result = 3/18
    assert evaluate_position(game, player) == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_one_turn_away():
    """Card costs 3 tokens, player has 0: shortfall=3, rounds=ceil(3/3)=1, contribution=point/2."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    card = _card("c", Tier.Common, point=6,
                 cost_types=(PokeballType.Red, PokeballType.Blue, PokeballType.Yellow))
    board = Board(common_revealed=[card, None, None, None])
    game = _make_game([player, opponent], board)
    # rounds = ceil(3/3) = 1; val = 6/2 = 3.0
    assert evaluate_position(game, player) == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_two_turns_away():
    """Shortfall=4 tokens: rounds=ceil(4/3)=2, contribution=point/3."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    card = _card("c", Tier.Common, point=6,
                 cost_types=(PokeballType.Red,) * 4)
    board = Board(common_revealed=[card, None, None, None])
    game = _make_game([player, opponent], board)
    assert evaluate_position(game, player) == pytest.approx(6.0 / 3.0 / WIN_SCORE)


def test_evaluate_position_takes_max_not_sum():
    """Two cards: 2pt affordable now vs 9pt two turns away. max(2/1, 9/3)=3."""
    player = Player(name="p1")
    player.points = 0
    opponent = Player(name="p2")
    cheap = _card("cheap", Tier.Common, point=2)
    expensive = _card("exp", Tier.Common, point=9,
                      cost_types=(PokeballType.Red,) * 4)
    board = Board(common_revealed=[cheap, expensive, None, None])
    game = _make_game([player, opponent], board)
    assert evaluate_position(game, player) == pytest.approx(3.0 / WIN_SCORE)


def test_evaluate_position_epic_requires_master():
    """Epic card with no master token: skipped, max_val stays 0."""
    player = Player(name="p1")
    player.points = 2
    opponent = Player(name="p2")
    epic = _card("epic", Tier.Epic, point=8)
    board = Board(epic_revealed=[epic])
    game = _make_game([player, opponent], board)
    assert evaluate_position(game, player) == pytest.approx(2.0 / WIN_SCORE)


def test_evaluate_position_alpha_scales_with_players():
    """4-player game: alpha = 1/(4-1) = 1/3. Free 3pt card → val = 0 + (1/3)*3 = 1."""
    players = [Player(name=f"p{i}") for i in range(4)]
    free_card = _card("free", Tier.Common, point=3)
    board = Board(common_revealed=[free_card, None, None, None])
    game = _make_game(players, board)
    assert evaluate_position(game, players[0]) == pytest.approx(1.0 / WIN_SCORE, rel=1e-3)


from pathlib import Path
from pokemon_splendor.engine.simulator import game_step
from pokemon_splendor.engine.env import PokemonSplendorEnv
import numpy as np

JSONL = Path("data/pokemon.jsonl")


def _make_env_game():
    env = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
    env.reset()
    return env


def test_game_step_returns_new_game_object():
    """game_step must return a copy, not mutate the original."""
    env = _make_env_game()
    original = env.game
    agent = env.agent_selection
    mask = env.action_mask(agent)
    action = int(np.where(mask)[0][0])
    new_game, _ = game_step(original, action, agent)
    assert new_game is not original


def test_game_step_advances_turn():
    """After a non-terminal action, game.turn should usually change."""
    env = _make_env_game()
    original = env.game
    agent = env.agent_selection
    mask = env.action_mask(agent)
    # Take a token-taking action (always available at game start)
    from pokemon_splendor.engine.actions import TAKE_DIFF_START, TAKE_SAME_START
    token_action = next(
        a for a in range(TAKE_DIFF_START, TAKE_SAME_START) if mask[a]
    )
    new_game, is_terminal = game_step(original, token_action, agent)
    assert not is_terminal
    assert new_game.turn is not None


def test_game_step_terminal_on_18_points():
    """Setting a player to 18 points and having them catch a final card triggers terminal."""
    env = _make_env_game()
    game = env.game
    agent = env.agent_selection
    player = next(p for p in game.players if p.name == agent)

    # Give player enough points and tokens to catch and win
    player.points = 17
    for pt in [PokeballType.Red, PokeballType.Blue, PokeballType.Yellow,
               PokeballType.Pink, PokeballType.Black]:
        player.tokens.extend([PokeballToken(pt)] * 4)

    mask = env.action_mask(agent)
    from pokemon_splendor.engine.actions import CATCH_BOARD_START, CATCH_RESERVED_START

    # Find a catch action for a card worth >=1 point
    catch_action = None
    all_slots = (
        game.board.common_revealed + game.board.uncommon_revealed
        + game.board.rare_revealed + game.board.epic_revealed
        + game.board.legendary_revealed
    )
    for slot_idx, card in enumerate(all_slots):
        a = CATCH_BOARD_START + slot_idx
        if mask[a] and card is not None and card.point >= 1:
            catch_action = a
            break
    if catch_action is None:
        pytest.skip("No catchable point-scoring card in this game state")

    new_game, is_terminal = game_step(game, catch_action, agent)
    # Terminal happens at end of round; check that win_triggered is at least set
    assert new_game.win_triggered or is_terminal


from pokemon_splendor.agents.mcts import MCTSAgent, make_early_capture_policy


def test_mcts_prune_tokens_no_short_combos():
    """Pruned actions must not contain 1- or 2-token TAKE_DIFF combos."""
    from pokemon_splendor.engine.actions import TAKE_DIFF_COMBOS, TAKE_DIFF_START
    env = _make_env_game()
    agent_name = env.agent_selection
    agent = MCTSAgent(env, agent_name, n_simulations=1, depth=1)
    game = env.game
    player = next(p for p in game.players if p.name == agent_name)
    pruned = agent._prune_actions(game, player)
    for action in pruned:
        if TAKE_DIFF_START <= action < TAKE_DIFF_START + len(TAKE_DIFF_COMBOS):
            combo = TAKE_DIFF_COMBOS[action - TAKE_DIFF_START]
            assert len(combo) == 3, f"Found {len(combo)}-token combo in pruned actions"


def test_mcts_prune_reserve_master_preferred():
    """If RESERVE_MASTER is valid for a slot, RESERVE_NO_MASTER for same slot must be excluded."""
    from pokemon_splendor.engine.actions import RESERVE_MASTER_START, RESERVE_NO_MASTER_START
    env = _make_env_game()
    agent_name = env.agent_selection
    agent = MCTSAgent(env, agent_name, n_simulations=1, depth=1)
    game = env.game
    player = next(p for p in game.players if p.name == agent_name)
    pruned = set(agent._prune_actions(game, player))
    for slot_idx in range(12):
        master_action = RESERVE_MASTER_START + slot_idx
        no_master_action = RESERVE_NO_MASTER_START + slot_idx
        if master_action in pruned:
            assert no_master_action not in pruned, (
                f"Both RESERVE_MASTER and RESERVE_NO_MASTER present for slot {slot_idx}"
            )


def test_mcts_prune_reserve_max_five():
    """At most 5 reserve actions in pruned set."""
    from pokemon_splendor.engine.actions import RESERVE_MASTER_START, DISCARD_START
    env = _make_env_game()
    agent_name = env.agent_selection
    agent = MCTSAgent(env, agent_name, n_simulations=1, depth=1)
    game = env.game
    player = next(p for p in game.players if p.name == agent_name)
    pruned = agent._prune_actions(game, player)
    reserve_count = sum(
        1 for a in pruned if RESERVE_MASTER_START <= a < DISCARD_START
    )
    assert reserve_count <= 5


def test_mcts_agent_returns_valid_action():
    """MCTSAgent.act() must always return an action that is valid per the mask."""
    env = _make_env_game()
    agent_name = env.agent_selection
    agent = MCTSAgent(env, agent_name, n_simulations=50, depth=2)
    obs, _, _, _, _ = env.last()
    mask = env.action_mask(agent_name)
    action = agent.act(obs, mask)
    assert mask[action], f"Action {action} is not valid per mask"


def test_mcts_agent_beats_random():
    """MCTSAgent (200 sims, depth 4) should win >60% vs random over 30 games."""
    import random as pyrandom
    wins = 0
    games = 30
    for _ in range(games):
        env = PokemonSplendorEnv(jsonl_path=JSONL, num_players=2)
        env.reset()
        mcts_name = env.possible_agents[0]
        mcts_agent = MCTSAgent(env, mcts_name, n_simulations=200, depth=4)
        for _ in range(10000):
            if not env.agents:
                break
            name = env.agent_selection
            obs, _, term, trunc, _ = env.last()
            if term or trunc:
                break
            mask = env.action_mask(name)
            if name == mcts_name:
                action = mcts_agent.act(obs, mask)
            else:
                action = int(pyrandom.choice(np.where(mask)[0]))
            env.step(action)
        winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
        if winner.name == mcts_name:
            wins += 1
    assert wins / games >= 0.60, f"MCTSAgent only won {wins}/{games} vs random"
