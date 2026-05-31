import argparse
import random
import numpy as np
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv

MAX_STEPS = 100000


def main():
    parser = argparse.ArgumentParser(prog="pokemon-splendor")
    parser.add_argument("--players", default="random,random",
                        help="Comma-separated agent types: random, human")
    parser.add_argument("--mode", choices=["play", "train", "benchmark"], default="play")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--data", default="data/pokemon.jsonl")
    args = parser.parse_args()

    agent_types = [a.strip() for a in args.players.split(",")]
    num_players = len(agent_types)
    render_mode = "human" if (args.render or args.mode == "play") else None
    jsonl = Path(args.data)

    if args.mode == "benchmark":
        _run_benchmark(jsonl, agent_types, args.games, render_mode)
    else:
        _run_game(jsonl, agent_types, render_mode)


def _make_agent(agent_type: str):
    if agent_type == "random":
        return lambda obs, mask: int(np.random.choice(np.where(mask)[0]))
    if agent_type == "human":
        from pokemon_splendor.agents.human import HumanAgent
        return HumanAgent()
    raise ValueError(f"Unknown agent type: {agent_type}")


def _call_agent(agent, obs, mask) -> int:
    if callable(agent):
        return agent(obs, mask)
    return agent.act(obs, mask)


def _run_game(jsonl: Path, agent_types: list[str], render_mode: str | None):
    env = PokemonSplendorEnv(jsonl, num_players=len(agent_types), render_mode=render_mode)
    env.reset()
    agents_map = {name: _make_agent(atype) for name, atype in zip(env.possible_agents, agent_types)}

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
        agents_map = {name: _make_agent(t) for name, t in zip(env.possible_agents, agent_types)}
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


if __name__ == "__main__":
    main()
