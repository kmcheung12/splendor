# tests/server/test_serializer.py
from pathlib import Path
import pytest
from pokemon_splendor.engine.env import PokemonSplendorEnv
from server.serializer import serialize_game


def _env():
    env = PokemonSplendorEnv(Path("data/pokemon.jsonl"), num_players=2)
    env.reset(seed=42)
    return env


def test_serialize_game_top_level_keys():
    result = serialize_game(_env().game)
    assert set(result.keys()) == {"round", "phase", "turn", "players", "board", "board_tokens"}


def test_board_tokens_all_types():
    result = serialize_game(_env().game)
    assert set(result["board_tokens"].keys()) == {"red", "yellow", "blue", "pink", "black", "master"}
    assert result["board_tokens"]["master"] == 5


def test_board_revealed_slots():
    result = serialize_game(_env().game)
    board = result["board"]
    assert len(board["common_revealed"]) == 4
    assert len(board["uncommon_revealed"]) == 4
    assert len(board["rare_revealed"]) == 4
    assert len(board["epic_revealed"]) == 1
    assert len(board["legendary_revealed"]) == 1


def test_board_deck_counts_positive():
    result = serialize_game(_env().game)
    board = result["board"]
    assert board["common_deck_count"] > 0
    assert board["rare_deck_count"] > 0


def test_player_fields():
    result = serialize_game(_env().game)
    p = result["players"][0]
    assert set(p.keys()) == {"name", "points", "tokens", "cards", "reserved_cards"}
    assert p["points"] == 0
    assert p["tokens"] == {"red": 0, "yellow": 0, "blue": 0, "pink": 0, "black": 0, "master": 0}


def test_serialize_pokemon_fields():
    env = _env()
    board = env.game.board
    card = next(c for c in board.common_revealed if c is not None)
    result = serialize_game(env.game)
    slot = next(c for c in result["board"]["common_revealed"] if c is not None)
    assert set(slot.keys()) == {"name", "tier", "cost", "bonus", "evolve", "evolve_into", "point", "evolved"}
    assert slot["tier"] == "common"
    assert isinstance(slot["cost"], list)


def test_none_slot_serializes_as_none():
    result = serialize_game(_env().game)
    for slot in result["board"]["common_revealed"]:
        assert slot is None or isinstance(slot, dict)
