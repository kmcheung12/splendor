# src/pokemon_splendor/__main__.py
import argparse
import numpy as np
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv

MAX_STEPS = 100000


AGENT_TYPES = (
    "random          uniform random valid action\n"
    "human           interactive stdin\n"
    "early-capture   catches cheapest affordable card\n"
    "high-point      maximises points-per-round ratio\n"
    "bonus-engine    builds bonus engine first, then switches to points\n"
    "evolution-chain scores cards by full evolution chain value\n"
    "denial          reserves cards opponents can almost afford\n"
    "mcts            MCTS with shortfall eval, 200 simulations (default)\n"
    "<model>.zip     any .zip path loads that trained RL model\n"
    "alpha:<path>    AlphaZero agent loaded from a .pt checkpoint"
)


def main():
    parser = argparse.ArgumentParser(
        prog="pokemon-splendor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available agent/opponent types:\n{AGENT_TYPES}",
    )
    parser.add_argument("--players", default="random,random",
                        help="Comma-separated agent types for play/benchmark (see below)")
    parser.add_argument("--agents", default=None,
                        help="Alias for --players (used in train mode)")
    parser.add_argument("--mode", choices=["play", "train", "benchmark", "data", "alpha-train"], default="play")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--episodes", type=int, default=100000)
    parser.add_argument("--save", default="model.zip")
    parser.add_argument("--opponents", default="random",
                        help="Comma-separated opponent types for train mode (1 opponent=2p, 2=3p, 3=4p; see below)")
    parser.add_argument("--resume", default=None,
                        help="Path to existing model.zip to continue training")
    parser.add_argument("--lr", type=float, default=0.0001,
                        help="Learning rate (default 0.0001)")
    parser.add_argument("--mcts-sims", type=int, default=200,
                        help="MCTS simulations per move (default 200)")
    parser.add_argument("--mcts-depth", type=int, default=4,
                        help="MCTS cutoff depth in agent turns (default 4)")
    parser.add_argument("--mcts-opponent", default=None,
                        help="Opponent model for MCTS simulations: 'early-capture' (default) or a .zip model path")
    parser.add_argument("--alpha-iters", type=int, default=100,
                        help="Alpha training: number of self-play iterations")
    parser.add_argument("--alpha-games", type=int, default=20,
                        help="Alpha training: self-play games per iteration")
    parser.add_argument("--alpha-sims", type=int, default=100,
                        help="Alpha training: MCTS simulations per move")
    parser.add_argument("--alpha-depth", type=int, default=4,
                        help="Alpha training: MCTS cutoff depth")
    parser.add_argument("--alpha-checkpoint-dir", default="alpha_checkpoints",
                        help="Alpha training: directory for .pt checkpoint files")
    parser.add_argument("--alpha-resume", default=None,
                        help="Alpha training: .pt checkpoint to resume from")
    parser.add_argument("--alpha-start-iter", type=int, default=1,
                        help="Alpha training: iteration number to resume from (default 1)")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--data", default="data/pokemon.jsonl")
    args = parser.parse_args()

    players_str = args.agents or args.players
    agent_types = [a.strip() for a in players_str.split(",")]
    render_mode = "human" if (args.render or args.mode == "play") else None
    jsonl = Path(args.data)

    if args.mode == "data":
        from pokemon_splendor.cli.data_repl import run as run_data_repl
        run_data_repl(jsonl)
    elif args.mode == "train":
        opponent_types = [a.strip() for a in args.opponents.split(",")]
        _run_train(jsonl, args.episodes, args.save, opponent_types, args.resume, args.lr)
    elif args.mode == "benchmark":
        _run_benchmark(jsonl, agent_types, args.games, render_mode, args.mcts_sims, args.mcts_depth, args.mcts_opponent)
    elif args.mode == "alpha-train":
        _run_alpha_train(
            jsonl, args.alpha_iters, args.alpha_games,
            args.alpha_sims, args.alpha_depth,
            len(agent_types), args.alpha_checkpoint_dir,
            args.alpha_resume, args.alpha_start_iter,
        )
    else:
        _run_game(jsonl, agent_types, render_mode, args.mcts_sims, args.mcts_depth, args.mcts_opponent)


def _make_agent(agent_type: str, env=None, player_name: str = None,
                mcts_sims: int = 200, mcts_depth: int = 4, mcts_opponent: str | None = None):
    if agent_type == "random":
        return lambda obs, mask: int(np.random.choice(np.where(mask)[0]))
    if agent_type == "human":
        from pokemon_splendor.agents.human import HumanAgent
        return HumanAgent(env, player_name)
    if agent_type == "early-capture":
        from pokemon_splendor.agents.early_capture import EarlyCaptureAgent
        return EarlyCaptureAgent(env, player_name)
    if agent_type == "high-point":
        from pokemon_splendor.agents.high_point import HighPointCaptureAgent
        return HighPointCaptureAgent(env, player_name)
    if agent_type == "bonus-engine":
        from pokemon_splendor.agents.bonus_engine import BonusEngineAgent
        return BonusEngineAgent(env, player_name)
    if agent_type == "evolution-chain":
        from pokemon_splendor.agents.evolution_chain import EvolutionChainAgent
        return EvolutionChainAgent(env, player_name)
    if agent_type == "denial":
        from pokemon_splendor.agents.denial import DenialAgent
        return DenialAgent(env, player_name)
    if agent_type == "mcts":
        from pokemon_splendor.agents.mcts import MCTSAgent, make_early_capture_policy, make_rl_policy
        if mcts_opponent and mcts_opponent.endswith(".zip"):
            opponent_policy = make_rl_policy(mcts_opponent)
        else:
            opponent_policy = make_early_capture_policy()
        return MCTSAgent(env, player_name, n_simulations=mcts_sims, depth=mcts_depth,
                         opponent_policy=opponent_policy)
    if agent_type.startswith("alpha:"):
        model_path = agent_type.split(":", 1)[1]
        from pokemon_splendor.agents.alpha_net import AlphaNet
        from pokemon_splendor.agents.alpha_mcts import AlphaMCTSAgent
        net = AlphaNet.load(model_path)
        return AlphaMCTSAgent(env, player_name, network=net,
                              n_simulations=mcts_sims, depth=mcts_depth)
    if agent_type.endswith(".zip"):
        from pokemon_splendor.agents.rl import RLAgent
        return RLAgent(agent_type)
    raise ValueError(f"Unknown agent type: {agent_type}")


def _call_agent(agent, obs, mask) -> int:
    if callable(agent):
        return agent(obs, mask)
    return int(agent.act(obs, mask))


def _print_round_summary(possible_agents, current_agent, last_desc):
    from rich.console import Console
    c = Console()
    c.rule("[dim]Last actions[/]")
    for name in possible_agents:
        if name == current_agent:
            c.print(f"  [bold]{name}[/] (next turn)")
        else:
            desc = last_desc.get(name)
            c.print(f"  [dim]{name}[/] {desc}" if desc else f"  [dim]{name}[/] —")


def _run_game(jsonl: Path, agent_types: list[str], render_mode: str | None,
              mcts_sims: int = 200, mcts_depth: int = 4, mcts_opponent: str | None = None):
    from pokemon_splendor.agents.base import describe_action
    env = PokemonSplendorEnv(jsonl, num_players=len(agent_types), render_mode=render_mode)
    env.reset()
    agents_map = {
        name: _make_agent(atype, env=env, player_name=name, mcts_sims=mcts_sims, mcts_depth=mcts_depth, mcts_opponent=mcts_opponent)
        for name, atype in zip(env.possible_agents, agent_types)
    }
    human_agents = {name for name, atype in zip(env.possible_agents, agent_types) if atype == "human"}
    last_desc: dict[str, str | None] = {name: None for name in env.possible_agents}

    for _ in range(MAX_STEPS):
        if not env.agents:
            break
        agent_name = env.agent_selection
        obs, _, term, trunc, _ = env.last()
        if term or trunc:
            break
        mask = env.action_mask(agent_name)
        if render_mode == "human":
            env.render()
            if agent_name in human_agents and any(v is not None for v in last_desc.values()):
                _print_round_summary(env.possible_agents, agent_name, last_desc)
        player = next(p for p in env.game.players if p.name == agent_name)
        action = _call_agent(agents_map[agent_name], obs, mask)
        last_desc[agent_name] = describe_action(action, env.game, player)
        env.step(action)

    from collections import Counter
    from rich.console import Console
    from rich.table import Table
    from rich import box
    from pokemon_splendor.models import Tier
    c = Console()
    winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
    c.print(f"\n[bold green]Winner: {winner.name} with {winner.points} points! ({env.game.round} rounds)[/]")

    table = Table(title="End-Game Stats", box=box.SIMPLE)
    table.add_column("Player")
    table.add_column("Pts")
    for t in Tier:
        table.add_column(t.value.capitalize())
    table.add_column("Cards")
    table.add_column("Tokens")

    for p in env.game.players:
        active = [c for c in p.cards if not c.evolved]
        tier_counts = Counter(c.tier for c in active)
        token_counts = Counter(t.name.value for t in p.tokens)
        token_str = " ".join(f"{v}×{k}" for k, v in sorted(token_counts.items()))
        marker = "► " if p is winner else "  "
        table.add_row(
            f"{marker}{p.name}",
            str(p.points),
            *[str(tier_counts.get(t, 0)) for t in Tier],
            str(len(active)),
            token_str,
        )
    c.print(table)


def _run_benchmark(jsonl: Path, agent_types: list[str], num_games: int, render_mode,
                   mcts_sims: int = 200, mcts_depth: int = 4, mcts_opponent: str | None = None):
    wins = {i: 0 for i in range(len(agent_types))}
    completed = 0

    def _print_results():
        played = completed
        print(f"\nBenchmark Results ({played}/{num_games} games):")
        for i, atype in enumerate(agent_types):
            pct = 100 * wins[i] / played if played else 0.0
            print(f"  {atype}: {wins[i]}/{played} wins ({pct:.1f}%)")

    try:
        for game_num in range(1, num_games + 1):
            env = PokemonSplendorEnv(jsonl, num_players=len(agent_types), render_mode=render_mode)
            env.reset()
            agents_map = {
                name: _make_agent(t, env=env, player_name=name, mcts_sims=mcts_sims, mcts_depth=mcts_depth, mcts_opponent=mcts_opponent)
                for name, t in zip(env.possible_agents, agent_types)
            }
            for _ in range(MAX_STEPS):
                if not env.agents:
                    break
                name = env.agent_selection
                obs, _, term, trunc, _ = env.last()
                if term or trunc:
                    break
                mask = env.action_mask(name)
                env.step(_call_agent(agents_map[name], obs, mask))
            winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
            idx = env.possible_agents.index(winner.name)
            wins[idx] += 1
            completed += 1
            print(f"\r  {game_num}/{num_games} ({100*game_num/num_games:.0f}%)", end="", flush=True)
    except KeyboardInterrupt:
        pass

    _print_results()


def _run_train(jsonl: Path, episodes: int, save_path: str,
               opponent_types: list[str] | None = None,
               resume_path: str | None = None,
               learning_rate: float = 0.0001):
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.wrappers import ActionMasker
    from pokemon_splendor.agents.rl import SingleAgentEnv

    opponent_types = opponent_types or ["random"]
    num_players = len(opponent_types) + 1

    def mask_fn(env):
        return env.action_masks()

    env = ActionMasker(SingleAgentEnv(jsonl, num_players=num_players, opponent_types=opponent_types), mask_fn)

    if resume_path:
        model = MaskablePPO.load(resume_path, env=env,
                                 custom_objects={"learning_rate": learning_rate})
        print(f"Resuming from {resume_path} (lr={learning_rate})")
    else:
        model = MaskablePPO("MlpPolicy", env, verbose=1,
                            learning_rate=learning_rate,
                            vf_coef=0.5,
                            policy_kwargs={"net_arch": dict(pi=[128, 128], vf=[128, 128])})

    model.learn(total_timesteps=episodes)
    model.save(save_path)
    print(f"\nModel saved to {save_path}")


def _run_alpha_train(
    jsonl: Path, n_iterations: int, games_per_iteration: int,
    n_simulations: int, depth: int, num_players: int, checkpoint_dir: str,
    resume_from: str | None = None, start_iteration: int = 1,
):
    from pokemon_splendor.agents.alpha_coach import AlphaCoach
    coach = AlphaCoach(
        jsonl_path=jsonl,
        num_players=num_players,
        n_iterations=n_iterations,
        games_per_iteration=games_per_iteration,
        n_simulations=n_simulations,
        depth=depth,
        checkpoint_dir=checkpoint_dir,
        resume_from=resume_from,
        start_iteration=start_iteration,
    )
    coach.run()


if __name__ == "__main__":
    main()
