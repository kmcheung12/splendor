from collections import Counter

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from pokemon_splendor.models import Game, PokeballType, GamePhase

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

    # Revealed cards per tier
    all_revealed = {
        "Common": game.board.common_revealed,
        "Uncommon": game.board.uncommon_revealed,
        "Rare": game.board.rare_revealed,
        "Epic": game.board.epic_revealed,
        "Legendary": game.board.legendary_revealed,
    }
    for tier_name, slots in all_revealed.items():
        table = Table(title=tier_name, box=box.SIMPLE)
        table.add_column("Slot")
        table.add_column("Name")
        table.add_column("Cost")
        table.add_column("Bonus")
        table.add_column("Pts")
        for i, p in enumerate(slots):
            if p:
                cost_str = " ".join(f"{t.name.value}" for t in p.cost)
                bonus_str = " ".join(f"{b.name.value}" for b in p.bonus)
                table.add_row(str(i), p.name, cost_str, bonus_str, str(p.point))
            else:
                table.add_row(str(i), "—", "", "", "")
        console.print(table)

    # Players
    for p in game.players:
        tc = Counter(t.name for t in p.tokens)
        token_str = "  ".join(f"{pt.value}:{tc[pt]}" for pt in PokeballType if tc[pt] > 0)
        cards_str = ", ".join(
            f"{c.name}{'*' if c.evolved else ''}" for c in p.cards
        )
        reserved_str = ", ".join(c.name for c in p.reserved_cards)
        marker = "► " if p is game.turn else "  "
        console.print(
            Panel(
                f"Tokens: {token_str}\nCards: {cards_str}\nReserved: {reserved_str}\nPoints: {p.points}",
                title=f"{marker}{p.name}",
            )
        )


def render_valid_actions(actions: list[tuple[int, str]]) -> None:
    for idx, (action_id, description) in enumerate(actions):
        console.print(f"  [{idx}] {description}")
