from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from state import GameState
from cli.settings import run_ai_settings, run_draft_order_settings
from cli.draft import run_draft
from cli.my_team import run_my_team
from cli.ui import error, heading, info, menu, success, tool_call, warning
import sys

def run_cli():
    """Load the core services while the interactive CLI is being built."""
    game = GameState()
    session = PromptSession()
    ai_status = "enabled" if game.ai_enabled else "not configured"

    info(f"Loaded {len(game.data.hero_names)} heroes.")
    info(f"AI integration: {ai_status}.")

    # Bring up main menu
    while True:
        _prompt_main_menu(session, game)
        sys.exit(0)

        

def _prompt_main_menu(session, game):
    # Wait for choice, then handle it
    while True:
        heading("Lazy Esports Godfather")
        menu(
            [
                ("1", "Coach"),
                ("2", "My Team"),
                ("3", "Draft"),
                ("4", "Settings"),
            ],
            "/exit",
        )

        choice = session.prompt("Choose an option> ").strip()

        match (choice):
            case "/exit":
                return
            case "1":
                _run_coach(session, game)
            case "2":
                run_my_team(session, game)
            case "3":
                run_draft(session, game)
            case "4":
                _run_settings(session, game)
            case _:
                error("Please select a valid choice.")

def _run_coach(session, game: GameState):

    if not game.ai_enabled:
        warning("AI is not enabled. Configure it in Settings to use Coach.")
        return

    heading("Coach")
    info("Commands: /help, /clear, /back")

    while True:
        prompt = session.prompt("\nCoach> ").strip()

        match prompt:
            case "/help":
                info("Commands: /clear removes conversation history; /back returns to the main menu.")
                continue

            case "/clear":
                game.clear_coach_messages()
                success("All coach messages cleared.")
                continue

            case "/back":
                return

            # If invalid command
            case _ if prompt.startswith("/"):
                error("Unknown command. Type /help for the command list.")
                continue

            # If prompt is empty
            case "":
                continue

        info("Coach is thinking...")

        streaming_text = False
        for event in game.stream_coach_chat(prompt):
            if event["type"] == "tool_call":
                if streaming_text:
                    print()
                    streaming_text = False
                tool_call(event["name"], event["args"])
            else:
                print(event["content"], end="", flush=True)
                streaming_text = True

        # Finish the streamed reply before prompt_toolkit draws the next
        # input prompt, so its redraw cannot occupy the reply's final line.
        print()

def _run_settings(session, game):
    while True:
        heading("Settings")
        menu(
            [("1", "AI Configuration"), ("2", "Draft Order")],
            "/back",
        )

        choice = session.prompt("Choose an option> ").strip()

        match choice:
            case "1":
                run_ai_settings(session, game)
            case "2":
                run_draft_order_settings(session, game)
            case "/back":
                return
            case _:
                error("Please select a valid choice.")
