from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from state import GameState
from cli.ui import draft_order, error, heading, info, menu, success


def run_ai_settings(session: PromptSession, game: GameState):
    while True:
        # Keep track of the current settings
        model_settings = game.get_model_settings()
        current_provider = model_settings.get("provider") or "Not set"
        current_model = model_settings.get("model") or "Not set"
        current_base_url = model_settings.get("base_url") or "Default"
        # Keep the key available for later updates, but never print it.
        current_api_key = game.api_key

        # Calculate status bools
        api_key_status = "Configured" if model_settings.get("api_key_configured") else "Not configured"
        ai_status = "Enabled" if model_settings.get("enabled") else "Disabled"

        heading("AI Configuration")
        info(
            f"Provider: {current_provider} | Model: {current_model} | "
            f"Base URL: {current_base_url} | API key: {api_key_status} | AI: {ai_status}"
        )
        menu(
            [
                ("1", "Set provider"),
                ("2", "Set model"),
                ("3", "Set base URL"),
                ("4", "Set API key"),
                ("5", "Disable AI"),
            ],
            "/back",
        )


        choice = session.prompt("\nChoose an option> ").strip()

        match choice:
            case "1":
                current_provider = _set_ai_provider(session)
                success("Provider updated.")
            case "2":
                current_model = _set_ai_model(session)
                success("Model name updated.")
            case "3":
                current_base_url = _set_ai_base_url(session)
                success("Host URL updated.")
            case "4":
                current_api_key = _set_ai_api_key(session)
                success("API key updated.")
            case "5":
                (
                    current_provider,
                    current_model,
                    current_base_url,
                    current_api_key,
                ) = _disable_ai()
                success("AI disabled.")
            case "/back":
                return
            case _:
                error("Please select a valid choice.")
                continue

        # Update model config
        game.configure_model(
            current_provider,
            current_model,
            current_base_url,
            current_api_key
        )

def _set_ai_provider(session):
    while True:
        return session.prompt("\nInput new provider> ").strip()

def _set_ai_model(session):
    while True:
        return session.prompt("\nInput new model name> ").strip()

def _set_ai_base_url(session):
    while True:
        return session.prompt("\nInput new host URL> ").strip()

def _set_ai_api_key(session):
    while True:
        return session.prompt("\nInput new api key> ").strip()

def _disable_ai():
    """Clear the AI configuration and return the cleared menu values."""
    provider = ""
    model_name = ""
    base_url = ""
    api_key = ""
    return provider, model_name, base_url, api_key


def run_draft_order_settings(session: PromptSession, game: GameState):
    """Set or clear the sequence of actions used in a draft."""
    while True:
        heading("Draft Order")
        draft_order(game.draft_order)
        menu(
            [("1", "Set draft order"), ("2", "Clear draft order")],
            "/back",
        )

        choice = session.prompt("Choose an option> ").strip()
        if choice == "1":
            _replace_draft_order(session, game)
        elif choice == "2":
            game.set_draft_order([])
            success("Draft order cleared.")
        elif choice == "/back":
            return
        else:
            error("Please select a valid choice.")


def _replace_draft_order(session: PromptSession, game: GameState):
    step_completer = WordCompleter(
        ["blue", "red", "pick", "ban"],
        ignore_case=True,
    )
    steps = []

    heading("Set Draft Order")
    info("Add steps as '<blue/red> <pick/ban>', for example: red pick.")
    info("Commands: /done saves; /cancel discards changes.")
    while True:
        entry = session.prompt(
            f"Step {len(steps) + 1} (/done)> ",
            completer=step_completer,
        ).strip().lower()

        if entry == "/cancel":
            info("Draft order unchanged.")
            return
        if entry == "/done":
            if not steps:
                error("Add at least one step before saving.")
                continue
            game.set_draft_order(steps)
            success("Draft order saved.")
            return

        parts = entry.split()
        if len(parts) != 2 or parts[0] not in {"blue", "red"} or parts[1] not in {"pick", "ban"}:
            error("Enter a side and action, for example: red pick.")
            continue

        steps.append((parts[0], parts[1].title()))

