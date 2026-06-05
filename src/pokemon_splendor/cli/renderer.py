from collections import Counter

from rich.console import Console
from rich.columns import Columns
from rich.table import Table
from rich.panel import Panel
from rich import box

from pokemon_splendor.models import Game, PokeballType, GamePhase
from pokemon_splendor.engine.rules import get_player_bonuses

console = Console()

TYPE_COLORS = {
    PokeballType.Red: "red",
    PokeballType.Yellow: "yellow",
    PokeballType.Blue: "blue",
    PokeballType.Pink: "magenta",
    PokeballType.Black: "white",
    PokeballType.Master: "gold1",
}


def _token_str(tokens: dict[PokeballType, int]) -> str:
    return "  ".join(
        f"[{TYPE_COLORS[pt]}]{pt.value}:{count}[/]"
        for pt, count in tokens.items()
        if count > 0
    )


def render(game: Game) -> None:
    console.rule(f"[bold]Round {game.round} — {game.turn.name}'s turn ({game.phase.value})[/]")

    # Board tokens
    console.print(Panel(_token_str(game.tokens), title="Board Tokens"))

    def _make_board_table(title, tier_slots: list[tuple[str, list]]):
        table = Table(title=title, box=box.SIMPLE)
        table.add_column("Tier")
        table.add_column("Slot")
        table.add_column("Name")
        table.add_column("Cost")
        table.add_column("Bonus")
        table.add_column("Evolve")
        table.add_column("Pts")
        for tier_idx, (tier_name, slots) in enumerate(tier_slots):
            if tier_idx > 0:
                table.add_row("", "", "", "", "", "", "")
            for i, p in enumerate(slots):
                if p:
                    cost_str = " ".join(
                        f"[{TYPE_COLORS[t.name]}]{t.name.value}[/]" for t in p.cost
                    )
                    bonus_str = " ".join(
                        f"[{TYPE_COLORS[b.name]}]{b.name.value}[/]" for b in p.bonus
                    )
                    evolve_str = " ".join(
                        f"[{TYPE_COLORS[b.name]}]{b.name.value}[/]" for b in p.evolve
                    )
                    table.add_row(tier_name, str(i), p.name, cost_str, bonus_str, evolve_str, str(p.point))
                else:
                    table.add_row(tier_name, str(i), "—", "", "", "", "")
        return table

    console.print(_make_board_table("Common / Uncommon / Rare", [
        ("Common",   game.board.common_revealed),
        ("Uncommon", game.board.uncommon_revealed),
        ("Rare",     game.board.rare_revealed),
    ]))
    console.print(_make_board_table("Epic / Legendary", [
        ("Epic",      game.board.epic_revealed),
        ("Legendary", game.board.legendary_revealed),
    ]))

    def _player_panel(p) -> Panel:
        token_str = " ".join(
            f"[{TYPE_COLORS[t.name]}]{t.name.value}[/]"
            for t in sorted(p.tokens, key=lambda t: list(PokeballType).index(t.name))
        )
        bonuses = get_player_bonuses(p)
        bonus_str = " ".join(
            f"[{TYPE_COLORS[pt]}]{pt.value}[/]"
            for pt in sorted(bonuses, key=lambda pt: list(PokeballType).index(pt))
            for _ in range(bonuses[pt])
        )

        def _card_str(c):
            if c.evolved or not c.evolve:
                return f"{c.name}{'*' if c.evolved else ''}"
            evolve_cost = " ".join(
                f"[{TYPE_COLORS[b.name]}]{b.name.value}[/]" for b in c.evolve
            )
            return f"{c.name} →{evolve_cost}"

        def _chain_lines(cards):
            by_name = {c.name: c for c in cards}
            chained = {c.evolve_into for c in cards if c.evolve_into in by_name}
            lines = []
            for card in cards:
                if card.name not in chained:
                    chain = [card]
                    cur = card
                    while cur.evolve_into in by_name:
                        cur = by_name[cur.evolve_into]
                        chain.append(cur)
                    lines.append(", ".join(_card_str(c) for c in chain))
            return lines

        card_lines = _chain_lines(p.cards)
        cards_str = ("\n  " + "\n  ".join(card_lines)) if card_lines else " —"

        def _reserved_str(c):
            cost = " ".join(f"[{TYPE_COLORS[t.name]}]{t.name.value}[/]" for t in c.cost)
            return f"{c.name} ({cost})" if cost else c.name

        reserved_str = ("\n  " + "\n  ".join(_reserved_str(c) for c in p.reserved_cards)) if p.reserved_cards else " —"
        marker = "► " if p is game.turn else "  "
        token_count = len(p.tokens)
        return Panel(
            f"Tokens ({token_count}): {token_str}\nBonus:    {bonus_str}\nCards:   {cards_str}\nReserved: {reserved_str}\nPoints:   {p.points}",
            title=f"{marker}{p.name}",
        )

    # Players: two per row
    players = game.players
    for i in range(0, len(players), 2):
        console.print(Columns([_player_panel(p) for p in players[i:i+2]], equal=True, expand=True))


def render_valid_actions(actions: list[tuple[int, str]]) -> None:
    for idx, (action_id, description) in enumerate(actions):
        console.print(f"  [{idx}] {description}")
