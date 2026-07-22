from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from core.state import GameState

def run_cli():
    """Load the core services while the interactive CLI is being built."""
    game = GameState()
    session = PromptSession()
    ai_status = "enabled" if game.ai_enabled else "not configured"

    print("Lazy Esports Godfather — CLI")
    print(f"Loaded {len(game.data.hero_names)} heroes.")
    print(f"AI integration: {ai_status}.")

    # Bring up main menu
    while True:
        # Wait for a choice by the user
        choice = _prompt_main_menu(session)

        match (choice):
            case "0":
                return run_settings(session, game)
            case "1":
                _run_coach(session, game)
            case "2":
                _run_settings()
            
        if choice == "1":
            
        elif choice == "0":
            return
        

def _prompt_main_menu(session):
    print()
    print("Lazy Esports Godfather")
    print("1. Coach")
    print("0. Exit")

    while True:
        choice = session.prompt("Choose an option> ").strip()

        if choice in {"1", "0"}:
            return choice

        print("Please enter 1 or 0.")

def _run_coach(session, game):
    print("\nCoach mode. Type /back to return.")

    while True:
        query = session.prompt("Coach> ").strip()

        match query:
            case "/help":
                print("Help list coming soon.")
                continue

            case "/clear":
                print("All coach messages cleared.")
                continue

            case "/back":
                return

            case _ if query.startswith("/"):
                print("Please enter a valid command. Type /help for a command list.")
                continue

            case "":
                continue

        print("Coach thinking: \n", end="", flush=True)

        for chunk in game.stream_coach_message(query):
            print(chunk, end="", flush=True)

def _run_settings(session, game):
    print()
    print("Settings")
    print("1. Configure Coach (AI)")
    print("0. Back")

    while True:
        query = session.prompt("Coach> ").strip()

        match query:
            case "/help":
                print("Help list coming soon.")
                continue

            case "/clear":
                print("All coach messages cleared.")
                continue

            case "/back":
                return

            case _ if query.startswith("/"):
                print("Please enter a valid command. Type /help for a command list.")
                continue

            case "":
                continue

        print("Coach thinking: \n", end="", flush=True)

        for chunk in game.stream_coach_message(query):
            print(chunk, end="", flush=True)

