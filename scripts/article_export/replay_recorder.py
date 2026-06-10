import numpy as np
import torch
from pathlib import Path
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.agents.base import describe_action
from pokemon_splendor.agents.rl import RLAgent
from scripts.article_export.models import Replay, TurnRecord

MAX_STEPS = 1000


def _make_opponent(t: str, env, name: str):
    if t == "random":
        return None
    if t == "early-capture":
        from pokemon_splendor.agents.early_capture import EarlyCaptureAgent
        return EarlyCaptureAgent(env, name)
    if t == "denial":
        from pokemon_splendor.agents.denial import DenialAgent
        return DenialAgent(env, name)
    if t == "high-point":
        from pokemon_splendor.agents.high_point import HighPointCaptureAgent
        return HighPointCaptureAgent(env, name)
    if t.endswith(".zip"):
        return RLAgent(t)
    raise ValueError(f"unknown opponent: {t}")


def _policy_top_k(model, obs: np.ndarray, mask: np.ndarray, k: int = 5):
    obs_t = torch.as_tensor(obs).float().unsqueeze(0)
    mask_t = torch.as_tensor(mask).bool().unsqueeze(0)
    with torch.no_grad():
        dist = model.policy.get_distribution(obs_t, action_masks=mask_t)
        probs = dist.distribution.probs.squeeze(0).cpu().numpy()
        value = model.policy.predict_values(obs_t).item()
    top_idx = np.argsort(-probs)[:k]
    return [{"action": int(i), "prob": float(probs[i])} for i in top_idx], value


def record_replay(
    agent_model: Path,
    agent_batch_id: str,
    opponents: list[str],
    data_path: Path,
    out_path: Path,
    replay_id: str,
    seed: int,
) -> None:
    num_players = 1 + len(opponents)
    env = PokemonSplendorEnv(data_path, num_players=num_players)
    env.reset(seed=seed)
    agent = RLAgent(str(agent_model))
    agent_name = env.possible_agents[0]
    opp_map = {
        env.possible_agents[i + 1]: _make_opponent(opponents[i], env, env.possible_agents[i + 1])
        for i in range(len(opponents))
    }

    turns: list[TurnRecord] = []
    for step_idx in range(MAX_STEPS):
        if not env.agents:
            break
        name = env.agent_selection
        obs, _, term, trunc, _ = env.last()
        if term or trunc:
            break
        mask = env.action_mask(name)
        if name == agent_name:
            top_k, value = _policy_top_k(agent.model, obs, mask)
            action = int(agent.act(obs, mask))
            player = next(p for p in env.game.players if p.name == name)
            desc = describe_action(action, env.game, player)
            turns.append(TurnRecord(
                turn=step_idx,
                player=name,
                observation=obs.astype(float).tolist(),
                action=action,
                action_desc=desc,
                value=value,
                policy_top_k=top_k,
            ))
        else:
            opp = opp_map.get(name)
            if opp is None:
                action = int(np.random.choice(np.where(mask)[0]))
            else:
                action = int(opp.act(obs, mask))
        env.step(action)

    winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
    winner_label = agent_batch_id if winner.name == agent_name else next(
        (opponents[i] for i, n in enumerate(env.possible_agents[1:])
         if n == winner.name),
        "unknown",
    )
    rounds = env.game.round

    replay = Replay(
        id=replay_id,
        agent_batch=agent_batch_id,
        opponents=opponents,
        turns=turns,
        winner=winner_label,
        rounds=rounds,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(replay.model_dump_json(indent=2))


def _serialize_card(card) -> dict | None:
    if card is None:
        return None
    from collections import Counter
    return {
        "name": card.name,
        "tier": card.tier.value,
        "point": card.point,
        "cost": dict(Counter(t.name.value for t in card.cost)),
        "bonus": card.bonus[0].name.value if card.bonus else None,
    }


def _serialize_player(player) -> dict:
    from collections import Counter
    return {
        "name": player.name,
        "points": player.points,
        "tokens": dict(Counter(t.name.value for t in player.tokens)),
        "cards": [_serialize_card(c) for c in player.cards],
        "reserved_cards": [_serialize_card(c) for c in player.reserved_cards],
    }


def _serialize_board(env) -> dict:
    game = env.game
    board = game.board
    return {
        "common_revealed": [_serialize_card(c) for c in board.common_revealed],
        "uncommon_revealed": [_serialize_card(c) for c in board.uncommon_revealed],
        "rare_revealed": [_serialize_card(c) for c in board.rare_revealed],
        "epic_revealed": [_serialize_card(c) for c in board.epic_revealed],
        "legendary_revealed": [_serialize_card(c) for c in board.legendary_revealed],
        "tokens": {k.value: v for k, v in game.tokens.items()},
        "players": [_serialize_player(p) for p in game.players],
        "active_player": env.agent_selection if env.agents else "",
    }


def record_replay_with_snapshots(
    agent_model: Path,
    agent_batch_id: str,
    opponents: list[str],
    data_path: Path,
    replay_out: Path,
    snapshot_out: Path,
    replay_id: str,
    seed: int,
) -> None:
    """Run a game and emit both the per-turn replay JSON and the snapshots JSON."""
    import json
    num_players = 1 + len(opponents)
    env = PokemonSplendorEnv(data_path, num_players=num_players)
    env.reset(seed=seed)
    agent = RLAgent(str(agent_model))
    agent_name = env.possible_agents[0]
    opp_map = {
        env.possible_agents[i + 1]: _make_opponent(opponents[i], env, env.possible_agents[i + 1])
        for i in range(len(opponents))
    }

    initial_snap = _serialize_board(env)
    turn_records: list[TurnRecord] = []
    snapshot_turns: list[dict] = []

    for step_idx in range(MAX_STEPS):
        if not env.agents:
            break
        name = env.agent_selection
        obs, _, term, trunc, _ = env.last()
        if term or trunc:
            break
        mask = env.action_mask(name)
        if name == agent_name:
            top_k, value = _policy_top_k(agent.model, obs, mask)
            action = int(agent.act(obs, mask))
            player = next(p for p in env.game.players if p.name == name)
            desc = describe_action(action, env.game, player)
            turn_records.append(TurnRecord(
                turn=step_idx,
                player=name,
                observation=obs.astype(float).tolist(),
                action=action,
                action_desc=desc,
                value=value,
                policy_top_k=top_k,
            ))
        else:
            opp = opp_map.get(name)
            if opp is None:
                action = int(np.random.choice(np.where(mask)[0]))
                desc = "random move"
            else:
                action = int(opp.act(obs, mask))
                player = next(p for p in env.game.players if p.name == name)
                desc = describe_action(action, env.game, player)

        env.step(action)
        snapshot_turns.append({
            "turn": step_idx,
            "snapshot": _serialize_board(env),
            "description": desc if name == agent_name else f"{name}: {desc}",
        })

    winner = max(env.game.players, key=lambda p: (p.points, len(p.cards)))
    winner_label = agent_batch_id if winner.name == agent_name else next(
        (opponents[i] for i, n in enumerate(env.possible_agents[1:])
         if n == winner.name),
        "unknown",
    )
    replay = Replay(
        id=replay_id, agent_batch=agent_batch_id, opponents=opponents,
        turns=turn_records, winner=winner_label, rounds=env.game.round,
    )
    replay_out.parent.mkdir(parents=True, exist_ok=True)
    replay_out.write_text(replay.model_dump_json(indent=2))

    snapshot_out.parent.mkdir(parents=True, exist_ok=True)
    snapshot_out.write_text(json.dumps({
        "initial": initial_snap,
        "turns": snapshot_turns,
    }, indent=2))
