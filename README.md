# Lazy Esports Godfather

The application runs entirely on your computer. FastAPI serves a static browser interface on
`127.0.0.1`; graph scoring and saved data remain local.

## Run from source

```powershell
py -m pip install -r requirements.txt
py app.py
```

The application opens `http://127.0.0.1:8765` in your default browser.

AI is optional. Without it, the coach is disabled and draft recommendations use deterministic
graph scores. Use the in-app **Settings** page to select Ollama, OpenAI, Anthropic, or Google
Gemini and enter the provider's model name.

Cloud API keys entered in Settings are kept in memory for the current run and are not written to
the settings JSON file. They can alternatively be supplied through `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, or `GOOGLE_API_KEY`. Ollama does not require an API key.

## Build the Windows application

```powershell
pyinstaller --noconfirm --clean lazy_esports_godfather.spec
```

The distributable folder is created under `dist/Lazy Esports Godfather`. Packaged user data is
stored in `%LOCALAPPDATA%/Lazy Esports Godfather`, outside the application directory.
