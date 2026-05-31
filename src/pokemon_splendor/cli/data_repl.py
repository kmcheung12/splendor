import json
import os
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich import box

from pokemon_splendor.models import PokeballType, Tier

console = Console()

VALID_COLORS = [pt.value for pt in PokeballType]
VALID_TIERS = [t.value for t in Tier]


# ── file I/O ──────────────────────────────────────────────────────────────────

def _read_lines(path: Path) -> list[dict]:
    lines = []
    with open(path) as f:
        for raw in f:
            raw = raw.strip()
            if raw:
                lines.append(json.loads(raw))
    return lines


def _write_lines(path: Path, records: list[dict]) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise


# ── display ───────────────────────────────────────────────────────────────────

def _token_dict_str(d: dict) -> str:
    return " ".join(f"{k}:{v}" for k, v in d.items()) if d else ""


def _list(records: list[dict]) -> None:
    t = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    t.add_column("#", justify="right", style="dim")
    t.add_column("name")
    t.add_column("tier")
    t.add_column("cost")
    t.add_column("bonus")
    t.add_column("evolve")
    t.add_column("evolve_into")
    t.add_column("pts", justify="right")
    for i, r in enumerate(records, 1):
        t.add_row(
            str(i), r["name"], r["tier"],
            _token_dict_str(r.get("cost", {})),
            _token_dict_str(r.get("bonus", {})),
            _token_dict_str(r.get("evolve", {})),
            r.get("evolve_into", ""),
            str(r.get("point", 0)),
        )
    console.print(t)


def _show_record(lineno: int, r: dict) -> None:
    console.print(f"[dim]Line {lineno}:[/] {json.dumps(r)}")


# ── input helpers ─────────────────────────────────────────────────────────────

def _prompt(label: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    val = input(f"  {label}{hint}: ").strip()
    return val or default


def _parse_token_dict(raw: str) -> dict:
    if not raw.strip():
        return {}
    result = {}
    for part in raw.split():
        if ":" not in part:
            raise ValueError(f"Expected color:count, got '{part}'")
        color, count = part.split(":", 1)
        if color not in VALID_COLORS:
            raise ValueError(f"Unknown color '{color}'. Valid: {', '.join(VALID_COLORS)}")
        result[color] = int(count)
    return result


def _pick_line(records: list[dict], prompt: str) -> int | None:
    raw = input(f"  {prompt} (1–{len(records)}): ").strip()
    try:
        n = int(raw)
    except ValueError:
        console.print("[red]Not a number.[/]")
        return None
    if not 1 <= n <= len(records):
        console.print(f"[red]Out of range.[/]")
        return None
    return n


# ── operations ────────────────────────────────────────────────────────────────

def _op_list(records: list[dict]) -> None:
    _list(records)


def _op_show(records: list[dict]) -> None:
    n = _pick_line(records, "Line number")
    if n is None:
        return
    _show_record(n, records[n - 1])


_TEMPLATE = {
    "name": "",
    "tier": "common",
    "cost": {},
    "bonus": {},
    "evolve": {},
    "evolve_into": "",
    "point": 0,
}


def _validate_record(r: dict) -> str | None:
    """Return an error string, or None if valid."""
    if not r.get("name"):
        return "name is required"
    if r.get("tier") not in VALID_TIERS:
        return f"tier must be one of: {', '.join(VALID_TIERS)}"
    for field in ("cost", "bonus", "evolve"):
        for color in r.get(field, {}):
            if color not in VALID_COLORS:
                return f"unknown color '{color}' in {field}. Valid: {', '.join(VALID_COLORS)}"
    if not isinstance(r.get("point", 0), int):
        return "point must be an integer"
    return None


def _open_editor(initial: dict, error: str | None = None) -> dict | None:
    """Open $EDITOR with initial JSON. Returns parsed dict or None if cancelled."""
    editor = os.environ.get("EDITOR", "vi")
    content = json.dumps(initial, indent=2)
    if error:
        comment = f"// ERROR: {error}\n// Fix the JSON below and save, or delete all content to cancel.\n\n"
        content = comment + content

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write(content)
        tmp = f.name

    try:
        subprocess.run([editor, tmp], check=True)
        text = Path(tmp).read_text().strip()
        # Strip comment lines before parsing
        lines = [l for l in text.splitlines() if not l.strip().startswith("//")]
        text = "\n".join(lines).strip()
        if not text:
            return None
        return json.loads(text)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        console.print(f"[red]{e}[/]")
        return None
    finally:
        os.unlink(tmp)


def _op_add(records: list[dict], path: Path) -> None:
    record = dict(_TEMPLATE)
    error = None
    while True:
        result = _open_editor(record, error)
        if result is None:
            console.print("[dim]Cancelled.[/]")
            return
        error = _validate_record(result)
        if error is None:
            record = result
            break
        record = result  # keep edits, re-open with error

    records.append(record)
    _write_lines(path, records)
    console.print(f"[green]Added line {len(records)}:[/] {json.dumps(record)}")


def _op_update(records: list[dict], path: Path) -> None:
    n = _pick_line(records, "Line number to update")
    if n is None:
        return
    r = records[n - 1]
    _show_record(n, r)
    console.print("[dim]Press Enter to keep current value.[/]")

    try:
        updated = dict(r)
        name = _prompt("name", r["name"])
        updated["name"] = name

        tier_raw = _prompt("tier", r["tier"])
        if tier_raw not in VALID_TIERS:
            console.print(f"[red]Invalid tier.[/]")
            return
        updated["tier"] = tier_raw

        cost_raw = _prompt("cost", _token_dict_str(r.get("cost", {})))
        updated["cost"] = _parse_token_dict(cost_raw)

        bonus_raw = _prompt("bonus", _token_dict_str(r.get("bonus", {})))
        updated["bonus"] = _parse_token_dict(bonus_raw)

        evolve_raw = _prompt("evolve", _token_dict_str(r.get("evolve", {})))
        updated["evolve"] = _parse_token_dict(evolve_raw)

        updated["evolve_into"] = _prompt("evolve_into", r.get("evolve_into", ""))
        updated["point"] = int(_prompt("point", str(r.get("point", 0))))
    except (ValueError, KeyboardInterrupt) as e:
        console.print(f"[red]{e}[/]" if isinstance(e, ValueError) else "[dim]Cancelled.[/]")
        return

    records[n - 1] = updated
    _write_lines(path, records)
    console.print(f"[green]Updated line {n}:[/] {json.dumps(updated)}")


def _op_delete(records: list[dict], path: Path) -> None:
    n = _pick_line(records, "Line number to delete")
    if n is None:
        return
    r = records[n - 1]
    _show_record(n, r)
    confirm = input("  Delete? [y/N]: ").strip().lower()
    if confirm != "y":
        console.print("[dim]Cancelled.[/]")
        return
    records.pop(n - 1)
    _write_lines(path, records)
    console.print(f"[green]Deleted line {n}.[/]")


# ── REPL ──────────────────────────────────────────────────────────────────────

MENU = "[bold]l[/]ist  [bold]s[/]how  [bold]a[/]dd  [bold]u[/]pdate  [bold]d[/]elete  [bold]q[/]uit"

def run(path: Path) -> None:
    console.print(f"\n[bold]Pokémon Splendor Data Manager[/] — {path}")
    while True:
        records = _read_lines(path)
        console.print(f"\n[dim]{len(records)} entries[/]  {MENU}")
        try:
            cmd = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd in ("q", "quit"):
            break
        elif cmd in ("l", "list"):
            _op_list(records)
        elif cmd in ("s", "show"):
            _op_show(records)
        elif cmd in ("a", "add"):
            _op_add(records, path)
        elif cmd in ("u", "update"):
            _op_update(records, path)
        elif cmd in ("d", "delete"):
            _op_delete(records, path)
        elif cmd == "":
            pass
        else:
            console.print(f"[red]Unknown command '{cmd}'[/]")
