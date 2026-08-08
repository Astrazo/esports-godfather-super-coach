from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.patch_stdout import patch_stdout
from state import GameState
from core.hero_mastery import POSITIONS
from cli.ui import (
    draft_order,
    draft_summary,
    error,
    heading,
    info,
    masteries,
    recommendation as show_recommendation,
    success,
    tool_call,
    warning,
)


def run_draft(session: PromptSession, game: GameState):
    """Collect opponent proficiencies, then create a new draft state."""
    if not game.draft_order:
        heading("Draft")
        warning("No draft order is configured.")
        configure_now = session.prompt("Configure one now? (y/N)> ").strip().lower()
        if configure_now in {"y", "yes"}:
            from cli.settings import run_draft_order_settings

            run_draft_order_settings(session, game)
        if not game.draft_order:
            return

    heading("Draft Setup")
    draft_order(game.draft_order)
    _collect_t2_masteries(session, game)


def _collect_t2_masteries(session: PromptSession, game: GameState):
    """Collect known enemy masteries in any position, then start immediately."""
    hero_completer = WordCompleter(
        sorted(game.data.hero_names),
        ignore_case=True,
        sentence=True,
    )
    t2_levels = {position: {} for position in POSITIONS}

    heading("Enemy Proficiencies")
    info("Enter: Hero Mastery Position — for example: Wolfgang 7 Mid")
    info("Use Tab to complete the hero name. Add entries in any order.")
    info("Paste multiple entries on separate lines or separate them with semicolons.")
    info("Commands: /show, /start blue, /start red, /cancel")
    info("Example: /start blue begins the draft with you playing Blue.")

    while True:
        entry = session.prompt(
            "Enemy mastery (/start blue)> ",
            completer=hero_completer,
        ).strip()
        command = entry.casefold()

        if command == "/cancel":
            info("Draft setup cancelled.")
            return
        if command == "/show":
            _show_t2_masteries(t2_levels)
            continue

        # If the player has picked a side, begin the draft
        player_side = _parse_start_command(command)
        if player_side:

            # Set masteries
            for position, levels in t2_levels.items():
                game.set_masteries("t2", position, levels)

            # Start draft
            game.start_draft(player_side)
            success(f"Draft started. You are playing {player_side.title()} side.")
            _run_draft_loop(session, game)
            return
        if command.startswith("/start"):
            error("Use /start blue or /start red.")
            continue

        updates, parse_errors = _parse_t2_entries(entry, game)
        if parse_errors:
            for parse_error in parse_errors:
                error(parse_error)
            continue

        for hero, level, position in updates:
            t2_levels[position][hero] = level
        success(f"Added {len(updates)} enemy mastery entr{'y' if len(updates) == 1 else 'ies'}.")


def _parse_start_command(command: str):
    if command in {"/start blue", "/start red"}:
        return command.removeprefix("/start ")
    return None


def _parse_t2_entries(entry: str, game: GameState):
    """Parse one or more 'Hero Mastery Position' records before applying any."""
    records = [record.strip() for record in entry.replace("\n", ";").split(";") if record.strip()]
    if not records:
        return [], ["Enter a hero, mastery, and position; for example: Wolfgang 7 Mid."]

    hero_lookup = {hero.casefold(): hero for hero in game.data.hero_names}
    position_lookup = {position.casefold(): position for position in POSITIONS}
    updates = []
    errors = []

    for record in records:
        parts = record.rsplit(maxsplit=2)
        if len(parts) != 3:
            errors.append(f"Invalid entry '{record}'. Use: Hero Mastery Position.")
            continue

        hero = hero_lookup.get(parts[0].casefold())
        position = position_lookup.get(parts[2].casefold())
        if hero is None:
            errors.append(f"Unknown hero in '{record}'. Use Tab to complete hero names.")
            continue
        if position is None:
            errors.append(f"Unknown position in '{record}'. Use Top, Jungler, Mid, Bot, or Support.")
            continue
        if not parts[1].isdigit() or not 0 <= int(parts[1]) <= 7:
            errors.append(f"Mastery in '{record}' must be a whole number from 0 to 7.")
            continue
        if position not in game.t2_masteries[hero]:
            errors.append(f"{hero} cannot play {position}.")
            continue

        updates.append((hero, int(parts[1]), position))

    return updates, errors


def _show_t2_masteries(t2_levels):
    heading("Entered Enemy Proficiencies")
    for position in POSITIONS:
        heroes = sorted(t2_levels[position].items())
        masteries(position, heroes)


def _run_draft_loop(session: PromptSession, game: GameState):
    """Record each draft action and show advice when it is the player's turn."""
    while game.draft_state.current_step < len(game.draft_state.draft_order):
        draft = game.draft_state
        acting_side, action = draft.draft_order[draft.current_step]

        heading(f"Draft — {acting_side.title()} {action}")
        draft_summary(draft)
        if acting_side == draft.player_side:
            _print_recommendation(game.draft_recommendation, action)
        info("Ask the Coach at any time: /coach Your question")

        if action == "Pick":
            with patch_stdout():
                pick = _prompt_draft_pick(session, game)
            if pick is None:
                game.end_draft()
                info("Draft ended.")
                return

            hero, position = pick
            game.apply_draft_action(hero, position)
        else:
            with patch_stdout():
                hero = _prompt_draft_hero(session, game, action)
            if hero is None:
                game.end_draft()
                info("Draft ended.")
                return

            game.apply_draft_action(hero)

    success("Draft actions complete. Review the final teams before ending.")
    _run_draft_review(session, game)


def _print_recommendation(recommendation, action: str):
    show_recommendation(recommendation, action)


def _prompt_draft_hero(session: PromptSession, game: GameState, action: str):
    heroes = sorted(game.data.hero_names)
    hero_lookup = {hero.casefold(): hero for hero in heroes}
    hero_completer = WordCompleter(heroes, ignore_case=True, sentence=True)

    while True:
        hero_entry = session.prompt(
            f"{action} hero — type a name, then Tab (/end)> ",
            completer=hero_completer,
        ).strip()

        command = hero_entry.casefold()
        if command == "/end":
            return None
        if command == "/coach":
            error("Use /coach followed by a question.")
            continue
        if command.startswith("/coach "):
            _ask_draft_coach(game, hero_entry.split(maxsplit=1)[1])
            continue
        hero = hero_lookup.get(hero_entry.casefold())
        if hero:
            return hero

        error("Unknown hero. Type part of a hero name, press Tab to complete it, then press Enter.")


def _prompt_draft_pick(session: PromptSession, game: GameState):
    """Read a pick as one '<hero> <position>' entry."""
    heroes = sorted(game.data.hero_names)
    hero_lookup = {hero.casefold(): hero for hero in heroes}
    position_lookup = {position.casefold(): position for position in POSITIONS}
    hero_completer = WordCompleter(heroes, ignore_case=True, sentence=True)

    while True:
        entry = session.prompt(
            "Pick — Hero Position, then Enter (/end)> ",
            completer=hero_completer,
        ).strip()

        command = entry.casefold()
        if command == "/end":
            return None
        if command == "/coach":
            error("Use /coach followed by a question.")
            continue
        if command.startswith("/coach "):
            _ask_draft_coach(game, entry.split(maxsplit=1)[1])
            continue
        parts = entry.rsplit(maxsplit=1)
        if len(parts) != 2:
            error("Use Hero Position, for example: Bariel Bot or Zealot Jungler.")
            continue

        hero = hero_lookup.get(parts[0].casefold())
        position = position_lookup.get(parts[1].casefold())
        if hero is None:
            error("Unknown hero. Type part of a hero name, then press Tab to complete it.")
            continue
        if position is None:
            error("Use Top, Jungler, Mid, Bot, or Support.")
            continue
        if position not in game.graph.nodes[hero]["tiers"]:
            error(f"{hero} cannot play {position}.")
            continue

        return hero, position


def _run_draft_review(session: PromptSession, game: GameState):
    """Let the player correct the final draft and ask the coach before ending."""
    info("Commands: /set mine Hero Position, /set enemy Hero Position, /ban Hero, /unban Hero, /coach Question, /show, /end")
    info("Any correction replaces the old value. Use /coach for questions about these teams.")

    while True:
        heading("Draft Review")
        draft_summary(game.draft_state)
        entry = session.prompt("Review> ").strip()
        command = entry.casefold()

        if command == "/end":
            game.end_draft()
            success("Draft ended.")
            return
        if command == "/show":
            continue
        if command.startswith("/set "):
            _apply_pick_correction(entry, game)
            continue
        if command.startswith("/ban "):
            _apply_ban_correction(entry.split(maxsplit=1)[1], game, add=True)
            continue
        if command.startswith("/unban "):
            _apply_ban_correction(entry.split(maxsplit=1)[1], game, add=False)
            continue
        if command == "/coach":
            error("Use /coach followed by a question.")
            continue
        if command.startswith("/coach "):
            _ask_draft_coach(game, entry.split(maxsplit=1)[1])
            continue
        if entry.startswith("/"):
            error("Use /set, /ban, /unban, /coach, /show, or /end.")
            continue
        if not entry:
            continue
        error("Enter a command. Use /coach followed by a question for Coach advice.")


def _apply_pick_correction(entry: str, game: GameState):
    """Parse '/set mine|enemy Hero Position' and make it the current value."""
    parts = entry.split(maxsplit=2)
    if len(parts) != 3 or parts[1].casefold() not in {"mine", "enemy"}:
        error("Use /set mine Hero Position or /set enemy Hero Position.")
        return

    hero_and_position = parts[2].rsplit(maxsplit=1)
    if len(hero_and_position) != 2:
        error("Use /set mine Hero Position, for example: /set mine Bariel Bot.")
        return

    hero = _find_hero(hero_and_position[0], game)
    position = _find_position(hero_and_position[1])
    if hero is None or position is None:
        return

    try:
        team = "t1" if parts[1].casefold() == "mine" else "t2"
        game.set_draft_pick(team, hero, position)
    except ValueError as exception:
        error(str(exception))
        return
    success(f"Set {'your' if team == 't1' else 'enemy'} {position} pick to {hero}.")


def _apply_ban_correction(hero_entry: str, game: GameState, add: bool):
    hero = _find_hero(hero_entry, game)
    if hero is None:
        return

    if add:
        game.set_draft_ban(hero)
        success(f"Set {hero} as banned.")
    else:
        game.remove_draft_ban(hero)
        success(f"Removed ban for {hero}.")


def _find_hero(hero_entry: str, game: GameState):
    hero = {name.casefold(): name for name in game.data.hero_names}.get(hero_entry.casefold())
    if hero is None:
        error("Unknown hero. Use the hero's full name.")
    return hero


def _find_position(position_entry: str):
    position = {name.casefold(): name for name in POSITIONS}.get(position_entry.casefold())
    if position is None:
        error("Unknown position. Use Top, Jungler, Mid, Bot, or Support.")
    return position


def _ask_draft_coach(game: GameState, prompt: str):
    """Answer an on-demand draft question with the current draft context."""
    if not game.ai_enabled:
        warning("Coach is disabled. Configure an AI model in Settings to ask questions here.")
        return

    info("Coach is thinking...")
    printed_text = False
    received_text = False
    for event in game.stream_draft_advice(prompt):
        if event["type"] == "tool_call":
            if printed_text:
                print()
                printed_text = False
            tool_call(event["name"], event["args"])
            continue

        print(event["content"], end="", flush=True)
        printed_text = True
        received_text = True
    if printed_text:
        print()
    if not received_text:
        warning("Coach did not return a written answer. Try the question again or use a smaller model prompt.")
