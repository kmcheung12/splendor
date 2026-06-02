# tests/server/test_action_events.py
from pathlib import Path
import pytest
from pokemon_splendor.engine.env import PokemonSplendorEnv
from pokemon_splendor.engine.actions import (
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START,
    CATCH_RESERVED_START, RESERVE_MASTER_START, DISCARD_START,
    EVOLVE_START, EVOLVE_PASS,
)
from server.action_events import build_action_event


def _env():
    env = PokemonSplendorEnv(Path("data/pokemon.jsonl"), num_players=2)
    env.reset(seed=42)
    return env


def test_take_diff_tokens():
    env = _env()
    event = build_action_event(env.game, "player_0", TAKE_DIFF_START)  # red only
    assert event["type"] == "take_tokens"
    assert event["player"] == "player_0"
    assert "red" in event["tokens"]


def test_take_same_tokens():
    env = _env()
    event = build_action_event(env.game, "player_0", TAKE_SAME_START)  # 2× red
    assert event["type"] == "take_tokens"
    assert event["tokens"] == ["red", "red"]


def test_catch_board_card():
    env = _env()
    all_slots = (
        env.game.board.common_revealed + env.game.board.uncommon_revealed +
        env.game.board.rare_revealed + env.game.board.epic_revealed +
        env.game.board.legendary_revealed
    )
    slot_idx = next(i for i, c in enumerate(all_slots) if c is not None)
    event = build_action_event(env.game, "player_0", CATCH_BOARD_START + slot_idx)
    assert event["type"] == "catch_card"
    assert event["slot"] == slot_idx
    assert event["card"] == all_slots[slot_idx].name
    assert event["from_reserve"] is False


def test_discard_token():
    env = _env()
    event = build_action_event(env.game, "player_0", DISCARD_START)
    assert event["type"] == "discard_token"
    assert event["token"] == "red"


def test_evolve_pass():
    env = _env()
    event = build_action_event(env.game, "player_0", EVOLVE_PASS)
    assert event["type"] == "pass"


def test_all_events_have_player():
    env = _env()
    for action in [TAKE_DIFF_START, TAKE_SAME_START, DISCARD_START, EVOLVE_PASS]:
        event = build_action_event(env.game, "player_0", action)
        assert event["player"] == "player_0"
