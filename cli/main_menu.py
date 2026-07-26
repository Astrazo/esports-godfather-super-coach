from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from state import GameState
from cli.settings import run_ai_settings
import sys

def run_cli():
    """Load the core services while the interactive CLI is being built."""
    game = GameState()
    session = PromptSession()
    ai_status = "enabled" if game.ai_enabled else "not configured"

    print(f"Loaded {len(game.data.hero_names)} heroes.")
    print(f"AI integration: {ai_status}.")

    # Bring up main menu
    while True:
        _prompt_main_menu(session, game)
        sys.exit(0)

        

def _prompt_main_menu(session, game):
    # Wait for choice, then handle it
    while True:
        print("\nLazy Esports Godfather - CLI\n")
        print("1. Coach")
        print("2. Settings")
        print("0. Exit")

        choice = session.prompt("Choose an option> ").strip()

        match (choice):
            case "0":
                return
            case "1":
                _run_coach(session, game)
            case "2":
                _run_settings(session, game)
            case _:
                print("Please select a valid choice.")

def _run_coach(session, game: GameState):

    if not game.ai_enabled:
        print("AI not enabled.  Configure AI in settings to enable coach.")
        return

    print("\n===Coach===")

    while True:
        prompt = session.prompt("\nCoach> ").strip()

        match prompt:
            case "/help":
                print("Help list coming soon.")
                continue

            case "/clear":
                game.clear_coach_messages()
                print("All coach messages cleared.")
                continue

            case "/back":
                return

            # If invalid command
            case _ if prompt.startswith("/"):
                print("Please enter a valid command. Type /help for a command list.")
                continue

            # If prompt is empty
            case "":
                continue

        print("Coach thinking: \n", end="", flush=True)

        for chunk in game.stream_coach_message(prompt):
            print(chunk, end="", flush=True)

def _run_settings(session, game):
    while True:
        print("\nSettings\n")
        print("1. AI Configuration")
        print("0. Back")

        choice = session.prompt("Choose an option> ").strip()

        match choice:
            case "1":
                run_ai_settings(session, game)
            case "0":
                return
