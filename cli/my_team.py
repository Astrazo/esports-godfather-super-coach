from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

from core.hero_mastery import POSITIONS
from state import GameState
from cli.ui import error, heading, info, masteries, menu, success


def run_my_team(session: PromptSession, game: GameState):
    """Edit the persisted masteries for the player's own team by position."""
    while True:
        heading("My Team")
        options = []
        for number, position in enumerate(POSITIONS, start=1):
            known_heroes = _known_heroes_for_position(game, position)
            options.append((str(number), f"{position} ({len(known_heroes)} heroes configured)"))
        menu(options, "/back")

        choice = session.prompt("Choose a position> ").strip()
        if choice == "/back":
            return
        if not choice.isdigit() or not 1 <= int(choice) <= len(POSITIONS):
            error("Please select a valid position.")
            continue

        _edit_position(session, game, POSITIONS[int(choice) - 1])


def _edit_position(session: PromptSession, game: GameState, position: str):
    hero_completer = WordCompleter(
        sorted(game.data.hero_names),
        ignore_case=True,
        sentence=True,
    )

    heading(f"My Team — {position}")
    _print_position_masteries(game, position)
    info("Enter a hero and mastery level, for example: Babe 3. Use Tab to complete heroes.")
    info("Enter 0 to remove a hero. Commands: /clear resets the position; /back returns.")

    while True:
        entry = session.prompt(
            f"{position} hero and mastery (/back)> ",
            completer=hero_completer,
        ).strip()

        if entry == "/back":
            return
        if entry == "/clear":
            levels = {
                candidate: 0
                for candidate, masteries in game.t1_masteries.items()
                if position in masteries
            }
            game.set_masteries("t1", position, levels)
            success(f"Cleared {position} masteries.")
            continue
        hero, level, parse_error = _parse_hero_mastery(entry, game.data.hero_names)
        if parse_error:
            error(parse_error)
            continue
        if position not in game.t1_masteries[hero]:
            error(f"{hero} cannot play {position}.")
            continue

        game.set_masteries("t1", position, {hero: level})
        success(f"Saved {hero}: {level} mastery in {position}.")


def _known_heroes_for_position(game: GameState, position: str):
    return sorted(
        (hero, levels[position])
        for hero, levels in game.t1_masteries.items()
        if levels.get(position, 0) > 0
    )


def _print_position_masteries(game: GameState, position: str):
    known_heroes = _known_heroes_for_position(game, position)
    if not known_heroes:
        masteries(position, [])
        return

    masteries(position, known_heroes)


def _parse_hero_mastery(entry: str, hero_names):
    """Parse a '<hero name> <0-7>' entry without breaking multi-word names."""
    parts = entry.rsplit(maxsplit=1)
    if len(parts) != 2:
        return None, None, "Enter a hero followed by a mastery level, for example: Babe 3."

    hero_lookup = {hero.lower(): hero for hero in hero_names}
    hero = hero_lookup.get(parts[0].lower())
    if hero is None:
        return None, None, "Choose a hero from the completion list."
    if not parts[1].isdigit() or not 0 <= int(parts[1]) <= 7:
        return None, None, "Mastery must be a whole number from 0 to 7."

    return hero, int(parts[1]), None
