from pokemon_splendor.engine.env import PokemonSplendorEnv


def make_agent(agent_type: str, env: PokemonSplendorEnv, player_name: str,
               mcts_sims: int = 200, mcts_depth: int = 4):
    """Return an agent object with a `.act(obs, mask) -> int` method, or a callable."""
    import numpy as np

    if agent_type == "random":
        class _Random:
            def act(self, obs, mask):
                return int(np.random.choice(np.where(mask)[0]))
        return _Random()

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
        from pokemon_splendor.agents.mcts import MCTSAgent, make_early_capture_policy
        return MCTSAgent(env, player_name, n_simulations=mcts_sims, depth=mcts_depth,
                         opponent_policy=make_early_capture_policy())

    if agent_type.endswith(".zip"):
        from pokemon_splendor.agents.rl import RLAgent
        return RLAgent(agent_type)

    raise ValueError(f"Unknown agent type: {agent_type!r}")
