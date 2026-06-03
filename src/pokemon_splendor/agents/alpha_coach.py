from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
import copy
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


def _self_play_worker(args: tuple) -> list[SelfPlayRecord]:
    jsonl_path, network, num_players, n_simulations, depth = args
    return run_self_play_game(jsonl_path, network, num_players, n_simulations, depth)


def _eval_game(args: tuple) -> float:
    """Returns candidate's outcome (0–1) in one game against best."""
    jsonl_path, candidate_state, best_state, num_players, n_simulations, depth = args
    from pokemon_splendor.engine.env import PokemonSplendorEnv
    from pokemon_splendor.agents.alpha_mcts import AlphaMCTSAgent

    candidate = AlphaNet()
    candidate.load_state_dict(candidate_state)
    candidate.eval()
    best = AlphaNet()
    best.load_state_dict(best_state)
    best.eval()

    env = PokemonSplendorEnv(jsonl_path, num_players=num_players)
    env.reset()

    agents = {
        env.possible_agents[0]: AlphaMCTSAgent(env, env.possible_agents[0],
                                               network=candidate, n_simulations=n_simulations, depth=depth),
    }
    for name in env.possible_agents[1:]:
        agents[name] = AlphaMCTSAgent(env, name, network=best,
                                      n_simulations=n_simulations, depth=depth)

    for _ in range(MAX_STEPS):
        if not env.agents:
            break
        name = env.agent_selection
        obs, _, term, trunc, _ = env.last()
        if term or trunc:
            break
        mask = env.action_mask(name)
        action = agents[name].act(obs, mask)
        env.step(action)

    if env.game.winner is None:
        from pokemon_splendor.engine.rules import check_win_condition
        winner = check_win_condition(env.game)
        if winner is None:
            winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
        env.game.winner = winner

    outcomes = compute_outcomes(env.game)
    return outcomes[env.possible_agents[0]]


def evaluate_candidate(
    candidate: AlphaNet,
    best: AlphaNet,
    jsonl_path: Path,
    num_players: int,
    n_games: int,
    n_simulations: int,
    depth: int,
    n_workers: int = 1,
) -> float:
    """Returns candidate's average outcome over n_games against best."""
    candidate_state = {k: v.cpu() for k, v in candidate.state_dict().items()}
    best_state = {k: v.cpu() for k, v in best.state_dict().items()}
    args = [
        (jsonl_path, candidate_state, best_state, num_players, n_simulations, depth)
    ] * n_games

    if n_workers > 1:
        from multiprocessing import get_context
        ctx = get_context("spawn")
        with ctx.Pool(processes=n_workers) as pool:
            outcomes = pool.map(_eval_game, args)
    else:
        outcomes = [_eval_game(a) for a in args]

    return float(np.mean(outcomes))


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
        buffer_size: int = 20000,
        lr: float = 0.001,
        checkpoint_dir: str = "checkpoints",
        resume_from: str | None = None,
        start_iteration: int = 1,
        n_workers: int = 1,
        eval_games: int = 40,
        accept_threshold: float = 0.45,
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
        self._n_workers = n_workers
        self._eval_games = eval_games
        self._accept_threshold = accept_threshold

    def _run_self_play_iteration(self, network: AlphaNet) -> list[list[SelfPlayRecord]]:
        args = [
            (self._jsonl_path, network, self._num_players,
             self._n_simulations, self._depth)
        ] * self._games_per_iteration

        if self._n_workers > 1:
            from multiprocessing import get_context
            ctx = get_context("spawn")
            with ctx.Pool(processes=self._n_workers) as pool:
                return pool.map(_self_play_worker, args)
        else:
            return [_self_play_worker(a) for a in args]

    def run(self) -> None:
        if self._resume_from:
            best_network = AlphaNet.load(self._resume_from)
            print(f"Resumed from {self._resume_from}")
        else:
            best_network = AlphaNet()
        best_network.eval()
        replay_buffer: deque[SelfPlayRecord] = deque(maxlen=self._buffer_size)

        for iteration in range(self._start_iteration, self._n_iterations + 1):
            print(f"\n[Iteration {iteration}/{self._n_iterations}]")

            # Self-play against best accepted network
            all_game_records = self._run_self_play_iteration(best_network)
            for game_num, records in enumerate(all_game_records, 1):
                if records:
                    replay_buffer.extend(records)
                print(f"  game {game_num}/{self._games_per_iteration} — {len(records)} records", flush=True)
            print(f"  buffer size: {len(replay_buffer)}")

            # Train a candidate from a fresh copy of best
            if len(replay_buffer) >= self._batch_size:
                candidate = copy.deepcopy(best_network)
                optimizer = torch.optim.Adam(candidate.parameters(), lr=self._lr)
                batch = random.sample(list(replay_buffer), self._batch_size)
                policy_loss, value_loss = train_step(candidate, optimizer, batch)
                print(f"  policy_loss={policy_loss:.4f}  value_loss={value_loss:.4f}")

                # Evaluate candidate against best
                avg_outcome = evaluate_candidate(
                    candidate, best_network,
                    self._jsonl_path, self._num_players,
                    self._eval_games, self._n_simulations, self._depth,
                    self._n_workers,
                )
                accepted = avg_outcome >= self._accept_threshold
                print(f"  eval avg_outcome={avg_outcome:.3f} threshold={self._accept_threshold} → {'ACCEPTED' if accepted else 'rejected'}")
                if accepted:
                    best_network = candidate
                    best_network.eval()

            # Always checkpoint the current best
            path = self._checkpoint_dir / f"alpha_{iteration:04d}.pt"
            best_network.save(str(path))
            print(f"  saved {path}")
