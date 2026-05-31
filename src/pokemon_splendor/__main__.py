# src/pokemon_splendor/__main__.py
import argparse
import numpy as np
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv

MAX_STEPS = 100000


def main():
    parser = argparse.ArgumentParser(prog="pokemon-splendor")
    parser.add_argument("--players", default="random,random",
                        help="Comma-separated agent types")
    parser.add_argument("--agents", default=None,
                        help="Alias for --players (used in train mode)")
    parser.add_argument("--mode", choices=["play", "train", "benchmark", "data"], default="play")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--episodes", type=int, default=100000)
    parser.add_argument("--save", default="model.zip")
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
        _run_train(jsonl, args.episodes, args.save)
    elif args.mode == "benchmark":
        _run_benchmark(jsonl, agent_types, args.games, render_mode)
    else:
        _run_game(jsonl, agent_types, render_mode)


def _make_agent(agent_type: str, env=None, player_name: str = None):
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
    if agent_type == "rl":
        from pokemon_splendor.agents.rl import RLAgent
        return RLAgent("model.zip")
    raise ValueError(f"Unknown agent type: {agent_type}")


def _call_agent(agent, obs, mask) -> int:
    if callable(agent):
        return agent(obs, mask)
    return agent.act(obs, mask)


def _run_game(jsonl: Path, agent_types: list[str], render_mode: str | None):
    env = PokemonSplendorEnv(jsonl, num_players=len(agent_types), render_mode=render_mode)
    env.reset()
    agents_map = {
        name: _make_agent(atype, env=env, player_name=name)
        for name, atype in zip(env.possible_agents, agent_types)
    }

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
        env.step(_call_agent(agents_map[agent_name], obs, mask))

    from rich.console import Console
    c = Console()
    winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
    c.print(f"\n[bold green]Winner: {winner.name} with {winner.points} points![/]")


def _run_benchmark(jsonl: Path, agent_types: list[str], num_games: int, render_mode):
    wins = {i: 0 for i in range(len(agent_types))}
    for _ in range(num_games):
        env = PokemonSplendorEnv(jsonl, num_players=len(agent_types), render_mode=render_mode)
        env.reset()
        agents_map = {
            name: _make_agent(t, env=env, player_name=name)
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

    print("\nBenchmark Results:")
    for i, atype in enumerate(agent_types):
        print(f"  {atype}: {wins[i]}/{num_games} wins ({100*wins[i]/num_games:.1f}%)")


def _run_train(jsonl: Path, episodes: int, save_path: str):
    from sb3_contrib import MaskablePPO
    from sb3_contrib.common.wrappers import ActionMasker
    from pokemon_splendor.agents.rl import SingleAgentEnv

    def mask_fn(env):
        return env.action_masks()

    env = ActionMasker(SingleAgentEnv(jsonl, num_players=2), mask_fn)
    model = MaskablePPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=episodes)
    model.save(save_path)
    print(f"\nModel saved to {save_path}")


if __name__ == "__main__":
    main()
