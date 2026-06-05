# src/pokemon_splendor/agents/human.py
import re
import numpy as np
from rich.console import Console
from rich.table import Table
from rich import box
from pokemon_splendor.agents.base import RuleBasedAgent, describe_action
from pokemon_splendor.cli.renderer import render

_console = Console()


def _words(text: str) -> frozenset[str]:
    return frozenset(re.sub(r"[^a-z0-9]", " ", text.lower()).split())


def _print_actions(valid: list[tuple[int, str]]) -> None:
    groups: dict[str, list[tuple[int, str]]] = {}
    for seq, (_, desc) in enumerate(valid):
        header, _, rest = desc.partition(" ")
        groups.setdefault(header, []).append((seq, rest))

    table = Table(box=box.SIMPLE, show_header=True, pad_edge=False, title="Valid actions")
    for header in groups:
        table.add_column(header)

    max_rows = max(len(rows) for rows in groups.values())
    cols = list(groups.values())
    for i in range(max_rows):
        row = []
        for col in cols:
            if i < len(col):
                seq, rest = col[i]
                row.append(f"[{seq}] {rest}" if rest else f"[{seq}]")
            else:
                row.append("")
        table.add_row(*row)

    _console.print(table)


def _match(user_input: str, valid: list[tuple[int, str]]) -> int | None:
    """Return action_id if user_input unambiguously matches one description, else None."""
    needle = _words(user_input)
    matches = [(action_id, desc) for action_id, desc in valid if needle <= _words(desc)]
    if len(matches) == 1:
        return matches[0][0]
    if len(matches) > 1:
        print("Ambiguous — did you mean:")
        for action_id, desc in matches:
            seq = next(i for i, (a, _) in enumerate(valid) if a == action_id)
            print(f"  [{seq}] {desc}")
    else:
        print("No matching action.")
    return None


class HumanAgent(RuleBasedAgent):
    def act(self, obs: np.ndarray, mask: np.ndarray) -> int:
        game = self._game
        player = self._player
        render(game)
        valid = [(i, describe_action(i, game, player)) for i in np.where(mask)[0]]
        _print_actions(valid)
        while True:
            raw = input("Enter number or action: ").strip()
            if not raw:
                continue
            # Try numeric first
            try:
                choice = int(raw)
                if 0 <= choice < len(valid):
                    return valid[choice][0]
                print(f"Enter 0–{len(valid) - 1}")
                continue
            except ValueError:
                pass
            # Try text match
            action_id = _match(raw, valid)
            if action_id is not None:
                return action_id
