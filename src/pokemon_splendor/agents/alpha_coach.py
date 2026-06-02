from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
import random
import numpy as np
from pathlib import Path
import torch
import torch.nn.functional as F
from pokemon_splendor.models import Game


def compute_outcomes(game: Game) -> dict[str, float]:
    winner = game.winner
    winner_score = winner.points
    winner_cards = len([c for c in winner.cards if not c.evolved])
    outcomes = {}
    for player in game.players:
        active_cards = len([c for c in player.cards if not c.evolved])
        card_delta = (active_cards - winner_cards) * 0.001
        outcome = player.points / winner_score + card_delta
        outcomes[player.name] = max(0.0, min(1.0, outcome))
    return outcomes


MAX_STEPS = 100000


@dataclass
class SelfPlayRecord:
    obs: np.ndarray
    visit_counts: list[float]
    outcome: float


def run_self_play_game(
    jsonl_path: Path,
    network,
    num_players: int = 2,
    n_simulations: int = 100,
    depth: int = 4,
) -> list[SelfPlayRecord]:
    from pokemon_splendor.engine.env import PokemonSplendorEnv
    from pokemon_splendor.agents.alpha_mcts import AlphaMCTSAgent

    env = PokemonSplendorEnv(jsonl_path, num_players=num_players)
    env.reset()

    agents = {
        name: AlphaMCTSAgent(env, name, network=network,
                             n_simulations=n_simulations, depth=depth)
        for name in env.possible_agents
    }

    move_records: list[tuple[str, np.ndarray, list[float]]] = []

    for _ in range(MAX_STEPS):
        if not env.agents:
            break
        name = env.agent_selection
        obs, _, term, trunc, _ = env.last()
        if term or trunc:
            break
        mask = env.action_mask(name)
        action, visit_counts = agents[name].act(obs, mask)
        move_records.append((name, obs.copy(), visit_counts))
        env.step(action)

    # Determine winner if not already set (env uses check_win_condition internally
    # but does not store the result on game.winner)
    if env.game.winner is None:
        from pokemon_splendor.engine.rules import check_win_condition
        winner = check_win_condition(env.game)
        if winner is None:
            # Truncated game — pick leader by points then card count
            winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
        env.game.winner = winner

    outcomes = compute_outcomes(env.game)
    return [
        SelfPlayRecord(obs=obs, visit_counts=vc, outcome=outcomes[name])
        for name, obs, vc in move_records
    ]
