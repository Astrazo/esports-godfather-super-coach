from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from state import GameState


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

        print("\nAI Configuration")
        print(f"  Provider: {current_provider}")
        print(f"  Model:    {current_model}")
        print(f"  Base URL: {current_base_url}")
        print(f"  API key:  {api_key_status}")
        print(f"  AI:       {ai_status}\n")
        print("1. Set provider")
        print("2. Set model")
        print("3. Set base url (optional)")
        print("4. Set API key (optional)")
        print("5. Disable AI")
        print("0. Back")


        choice = session.prompt("\nChoose an option> ").strip()

        match choice:
            case "1":
                current_provider = _set_ai_provider(session)
                print("\nProvider updated.")
            case "2":
                current_model = _set_ai_model(session)
                print("\nModel name updated.")
            case "3":
                current_base_url = _set_ai_base_url(session)
                print("\nHost URL updated.")
            case "4":
                current_api_key = _set_ai_api_key(session)
                print("\nAPI key updated.")
            case "5":
                (
                    current_provider,
                    current_model,
                    current_base_url,
                    current_api_key,
                ) = _disable_ai()
                print("\nAI disabled.")
            case "0":
                return

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

