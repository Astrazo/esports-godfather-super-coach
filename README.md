# Lazy Esports Godfather

This branch contains the local game logic, persistence, draft scoring, and optional AI
integrations for the command-line version of Lazy Esports Godfather. The previous browser and
FastAPI interface are intentionally not included.

## Current entry point

```powershell
py -m pip install -r requirements.txt
py main.py
```

The current entry point loads the shared game state and reports whether an AI model is configured.
The interactive CLI will be built on top of these services.

AI remains optional. Without it, draft recommendations use deterministic graph scores. The core
supports Ollama, OpenAI, Anthropic, and Google Gemini.

Cloud API keys can be supplied through `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GOOGLE_API_KEY`.
Ollama does not require an API key. Provider and model settings remain in
`data/user_data/model_settings.json` during CLI development.

## Packaging

PyInstaller remains available for the eventual CLI build. Packaging will be updated after the
interactive CLI is implemented.
