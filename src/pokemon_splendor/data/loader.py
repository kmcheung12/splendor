import json
from pathlib import Path
from pokemon_splendor.models import Pokemon, Tier, PokeballToken, Bonus, PokeballType


def _expand_token_dict(d: dict, cls: type) -> list:
    tokens = []
    for color, count in d.items():
        try:
            ptype = PokeballType(color)
        except ValueError:
            raise ValueError(f"Invalid token type: {color}")
        tokens.extend([cls(ptype)] * count)
    return tokens


def load_pokemon(path: Path) -> list[Pokemon]:
    pokemon = []
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Line {lineno}: invalid JSON: {e}")

            for field in ("name", "tier", "cost", "point"):
                if field not in data:
                    raise ValueError(f"Missing required field '{field}' on line {lineno}")

            try:
                tier = Tier(data["tier"])
            except ValueError:
                raise ValueError(f"Invalid tier '{data['tier']}' on line {lineno}")

            pokemon.append(Pokemon(
                name=data["name"],
                tier=tier,
                cost=_expand_token_dict(data.get("cost", {}), PokeballToken),
                bonus=_expand_token_dict(data.get("bonus", {}), Bonus),
                evolve=_expand_token_dict(data.get("evolve", {}), Bonus),
                evolve_into=data.get("evolve_into", ""),
                point=data["point"],
            ))
    return pokemon
