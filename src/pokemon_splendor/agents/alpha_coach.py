from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
import random
import numpy as np
from pathlib import Path
import torch
import torch.nn.functional as F
from pokemon_splendor.models import Game
from pokemon_splendor.agents.alpha_net import AlphaNet, TOTAL_ACTIONS


def compute_outcomes(game: Game) -> dict[str, float]:
    winner = game.winner
    winner_score = winner.points
    if winner_score == 0:
        return {p.name: 1.0 if p is winner else 0.0 for p in game.players}
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
    network: "torch.nn.Module",
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
        action = agents[name].act(obs, mask)
        move_records.append((name, obs.copy(), agents[name].last_visit_counts))
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


def train_step(
    network: "torch.nn.Module",
    optimizer: torch.optim.Optimizer,
    batch: list[SelfPlayRecord],
) -> tuple[float, float]:
    network.train()
    obs_batch = torch.tensor(
        np.stack([r.obs for r in batch]), dtype=torch.float32
    )
    visit_batch = torch.tensor(
        np.array([r.visit_counts for r in batch]), dtype=torch.float32
    )
    outcome_batch = torch.tensor(
        [r.outcome for r in batch], dtype=torch.float32
    )
    mask_batch = (visit_batch > 0)

    policy, value = network(obs_batch, mask_batch)

    policy_loss = -(visit_batch * torch.log(policy.clamp(min=1e-8))).sum(dim=-1).mean()
    value_loss = F.mse_loss(value, outcome_batch)
    loss = policy_loss + value_loss

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    network.eval()
    return policy_loss.item(), value_loss.item()


class AlphaCoach:
    def __init__(
        self,
        jsonl_path: Path,
        num_players: int = 2,
        n_iterations: int = 100,
        games_per_iteration: int = 20,
        n_simulations: int = 100,
        depth: int = 4,
        batch_size: int = 256,
        buffer_size: int = 2000,
        lr: float = 0.001,
        checkpoint_dir: str = "checkpoints",
        resume_from: str | None = None,
        start_iteration: int = 1,
    ):
        self._jsonl_path = jsonl_path
        self._num_players = num_players
        self._n_iterations = n_iterations
        self._games_per_iteration = games_per_iteration
        self._n_simulations = n_simulations
        self._depth = depth
        self._batch_size = batch_size
        self._buffer_size = buffer_size
        self._lr = lr
        self._checkpoint_dir = Path(checkpoint_dir)
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._resume_from = resume_from
        self._start_iteration = start_iteration

    def run(self) -> None:
        if self._resume_from:
            network = AlphaNet.load(self._resume_from)
            print(f"Resumed from {self._resume_from}")
        else:
            network = AlphaNet()
        network.eval()
        optimizer = torch.optim.Adam(network.parameters(), lr=self._lr)
        replay_buffer: deque[SelfPlayRecord] = deque(maxlen=self._buffer_size)

        for iteration in range(self._start_iteration, self._n_iterations + 1):
            print(f"\n[Iteration {iteration}/{self._n_iterations}]")

            # Self-play
            for game_num in range(1, self._games_per_iteration + 1):
                records = run_self_play_game(
                    self._jsonl_path, network,
                    num_players=self._num_players,
                    n_simulations=self._n_simulations,
                    depth=self._depth,
                )
                if records:
                    replay_buffer.extend(records)
                print(f"  game {game_num}/{self._games_per_iteration} — {len(records)} records", flush=True)

            # Train
            if len(replay_buffer) >= self._batch_size:
                batch = random.sample(list(replay_buffer), self._batch_size)
                policy_loss, value_loss = train_step(network, optimizer, batch)
                print(f"  policy_loss={policy_loss:.4f}  value_loss={value_loss:.4f}")

            # Checkpoint
            path = self._checkpoint_dir / f"alpha_{iteration:04d}.pt"
            network.save(str(path))
            print(f"  saved {path}")
