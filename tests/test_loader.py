import pytest
from pathlib import Path
from pokemon_splendor.data.loader import load_pokemon
from pokemon_splendor.models import Tier, PokeballType


SAMPLE_JSONL = """\
{"name": "charmander", "tier": "common", "cost": {"red": 2}, "bonus": {"red": 1}, "evolve": {"red": 2}, "evolve_into": "charmeleon", "point": 0}
{"name": "mewtwo", "tier": "epic", "cost": {"master": 1, "red": 3}, "bonus": {}, "evolve": {}, "evolve_into": "", "point": 8}
"""


@pytest.fixture
def jsonl_file(tmp_path):
    f = tmp_path / "pokemon.jsonl"
    f.write_text(SAMPLE_JSONL)
    return f


def test_loads_correct_count(jsonl_file):
    pokemon = load_pokemon(jsonl_file)
    assert len(pokemon) == 2


def test_fields_parsed_correctly(jsonl_file):
    pokemon = load_pokemon(jsonl_file)
    charm = next(p for p in pokemon if p.name == "charmander")
    assert charm.tier == Tier.Common
    assert charm.point == 0
    assert charm.evolve_into == "charmeleon"
    assert charm.evolved is False


def test_cost_expanded_to_list(jsonl_file):
    pokemon = load_pokemon(jsonl_file)
    charm = next(p for p in pokemon if p.name == "charmander")
    types_in_cost = [t.name for t in charm.cost]
    assert types_in_cost.count(PokeballType.Red) == 2


def test_bonus_expanded_to_list(jsonl_file):
    pokemon = load_pokemon(jsonl_file)
    charm = next(p for p in pokemon if p.name == "charmander")
    assert len(charm.bonus) == 1
    assert charm.bonus[0].name == PokeballType.Red


def test_missing_optional_fields_default_empty(tmp_path):
    f = tmp_path / "p.jsonl"
    f.write_text('{"name": "ditto", "tier": "common", "cost": {}, "point": 0}\n')
    pokemon = load_pokemon(f)
    assert pokemon[0].bonus == []
    assert pokemon[0].evolve == []
    assert pokemon[0].evolve_into == ""


def test_invalid_tier_raises(tmp_path):
    f = tmp_path / "p.jsonl"
    f.write_text('{"name": "bad", "tier": "godlike", "cost": {}, "point": 0}\n')
    with pytest.raises(ValueError, match="Invalid tier"):
        load_pokemon(f)


def test_missing_required_field_raises(tmp_path):
    f = tmp_path / "p.jsonl"
    f.write_text('{"name": "bad"}\n')
    with pytest.raises(ValueError, match="Missing required field"):
        load_pokemon(f)
