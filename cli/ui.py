"""Shared Rich rendering helpers for the command-line interface."""

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


# The app is also used in legacy Windows consoles, which display raw ANSI
# escape sequences. Rich's Windows renderer keeps the output readable there.
console = Console(legacy_windows=True)


def heading(title: str):
    """Start a screen with the application's standard title treatment."""
    console.print()
    console.rule(f"[bold cyan]{title}[/bold cyan]")
    console.print()


def menu(options: list[tuple[str, str]], navigation: str):
    """Render a compact, consistently aligned menu."""
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold cyan", justify="right")
    table.add_column()
    for key, label in options:
        table.add_row(key, label)
    table.add_row("", "")
    table.add_row("[dim]Navigation[/dim]", f"[dim]{navigation}[/dim]")
    console.print(table)


def info(message: str):
    console.print(Text(message, style="cyan"))


def success(message: str):
    console.print(Text(message, style="green"))


def warning(message: str):
    console.print(Text(message, style="yellow"))


def error(message: str):
    console.print(Text(message, style="bold red"))


def draft_order(order):
    if not order:
        warning("No draft order configured.")
        return

    table = Table(title="Draft Order", header_style="bold cyan")
    table.add_column("Step", justify="right", style="dim")
    table.add_column("Side")
    table.add_column("Action")
    for number, (side, action) in enumerate(order, start=1):
        table.add_row(str(number), side.title(), action)
    console.print(table)


def draft_summary(draft):
    """Show the current picks and bans as the single source of draft truth."""
    table = Table(title="Current Draft", header_style="bold cyan")
    table.add_column("Team", style="bold cyan")
    table.add_column("Position")
    table.add_column("Hero")

    _add_pick_rows(table, "You", draft.t1_picked)
    _add_pick_rows(table, "Enemy", draft.t2_picked)
    if not draft.t1_picked and not draft.t2_picked:
        table.add_row("", "[dim]No picks yet[/dim]", "")

    console.print(table)
    bans = ", ".join(sorted(draft.banned)) if draft.banned else "[dim]No bans yet[/dim]"
    console.print(f"[bold cyan]Bans:[/bold cyan] {bans}")


def _add_pick_rows(table, team: str, picks: dict[str, set[str]]):
    rows = [
        (position, hero)
        for hero, positions in picks.items()
        for position in positions
    ]
    for position, hero in sorted(rows):
        table.add_row(team, position, hero)


def masteries(position: str, heroes: list[tuple[str, int]]):
    if not heroes:
        warning(f"No {position} heroes configured yet.")
        return

    table = Table(title=f"{position} Masteries", header_style="bold cyan")
    table.add_column("Hero")
    table.add_column("Mastery", justify="right")
    for hero, level in heroes:
        table.add_row(hero, str(level))
    console.print(table)


def recommendation(recommendation, action: str):
    if recommendation is None:
        warning("No recommendation is available for this action.")
        return

    action_text = "Ban" if action == "Ban" else "Pick"
    hero = recommendation["hero"]
    position = recommendation["position"]
    score = recommendation["score"]
    analysis = Text(recommendation["analysis"])
    source = "Graph Suggestion" if recommendation.get("source") == "graph" else "Coach Review"
    title = f"{source} — {action_text}: {hero} — {position} ({score:g})"
    if recommendation.get("source") == "graph":
        content = Group(analysis, _graph_explanation_table(recommendation.get("explanation", {})))
    else:
        content = analysis
    console.print(Panel(content, title=title, border_style="green"))


def _graph_explanation_table(explanation: dict):
    """Translate draft-score explanation keys into player-facing graph reasons."""
    labels = {
        "counters": "Counters picked enemy",
        "counters_possible": "Can counter available enemy",
        "countered_by": "Countered by picked enemy",
        "countered_by_possible": "Could be countered by available enemy",
        "synergy": "Synergy with picked ally",
        "synergy_possible": "Potential synergy",
        "a_synergy": "Anti-synergy with picked ally",
        "a_synergy_possible": "Potential anti-synergy",
        "position_tier": "Position tier",
        "position_mastery": "Position mastery",
    }
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold cyan")
    table.add_column()

    for key, label in labels.items():
        values = explanation.get(key)
        if values:
            table.add_row(label, ", ".join(str(value) for value in values))

    return table


def tool_call(name: str, arguments: dict):
    """Show a compact trace of an AI tool lookup without printing its result."""
    formatted_arguments = ", ".join(
        f"{key}={value!r}" for key, value in arguments.items()
    )
    console.print(f"[dim cyan]Tool:[/dim cyan] [cyan]{name}[/cyan]({formatted_arguments})")
