# Lazy Esports Godfather

Lazy Esports Godfather is a local command-line draft assistant for the game *Esports Godfather*. It helps you record your team's hero masteries, run a pick/ban draft, and receive explainable recommendations based on hero tiers, counters, synergies, and player proficiency.

This is an early-access CLI MVP, with the core draft workflow being opeartional.

## What it does

- Stores your team's playable heroes and mastery levels by position.
- Records the opposing team's known proficiencies for each individual draft.
- Supports configurable Blue/Red pick and ban sequences.
- Tracks picks and bans through a draft, including corrections before finalising it.
- Ranks draft picks and bans with deterministic, explainable graph scores. AI is not required for this.
- Optionally provides an AI Coach for general questions and draft-context questions.

The included reference data covers all 65 heroes (as of writing this).

## Requirements

- Python 3.11 or later.
- A terminal that supports interactive input. Windows Terminal on Windows and Terminal on macOS for example.

## Install and run

Clone the repository, then install the Python dependencies:

```powershell
py -m pip install -r requirements.txt
py main.py
```

On macOS or Linux, replace `py` with `python3` if needed.

## Run tests

Install the development dependencies and run the suite from the project root:

```powershell
py -m pip install -r requirements-dev.txt
py -m pytest
```

The tests use isolated in-memory application state and do not read or modify your local profile in `data/user_data/`.

## Setup walkthrough

The app starts at the main menu. Before a useful draft recommendation can be generated, complete these one-time setup steps:

1. Select **My Team** and enter the heroes each player can use in each position, with mastery from 0 to 7. A mastery of `0` removes that hero from the position.
2. Select **Settings** → **Draft Order** and enter the pick/ban sequence used by your game mode. For example, enter `blue ban`, `red ban`, and so on, then use `/done` to save it.
3. Select **Draft**. Enter any known enemy proficiencies in the format `Hero Mastery Position`, such as `Wolfgang 7 Mid`. You can enter several records separated by semicolons.
4. Start the draft with `/start blue` or `/start red`, with red or blue being your teams colour.
5. Enter each pick as `Hero Position` or each ban as `Hero`. The app shows an explainable recommendation whenever it is your side's turn.

Use `/end` to stop a draft, or use the review screen at the end to correct picks and bans before closing it.

## Optional AI Coach

The deterministic draft recommendation works entirely offline. AI Coach is optional and supports Ollama, OpenAI, Anthropic, and Google Gemini.

For cloud providers, set the provider's API key in your environment before launching the app:

```powershell
$env:OPENAI_API_KEY = "your-key"
py main.py
```

Then open **Settings** → **AI Configuration**, set the provider and model name, and return to the main menu. Ollama does not need an API key. The app never displays a configured API key.

Coach conversation history is saved locally. Do not enter secrets or personal information in Coach prompts.

## Current limitations

- The application is terminal-only; there is no web or desktop graphical interface yet, and probably never will be.
- It is not packaged as an installer or standalone executable yet.
- Initial setup is manual; there is no guided import or starter roster.
- The project does not yet have an automated test suite or CI pipeline.
- Recommendations reflect the included reference data and scoring rules; validate them against current game patches and own judgment.

## Project structure

- `cli/` — interactive terminal menus and rendering.
- `core/` — data loading, graph scoring, draft logic, persistence, and AI integration.
- `data/core_data/` — hero, relationship, tier, itemisation, and coaching reference data.
- `data/user_data/` — player masteries, draft order, model settings, and Coach history.
- `state.py` — application state and orchestration for the CLI.

## Licence

This project is licensed under the [MIT License](LICENSE).

## Disclaimer

Lazy Esports Godfather is an unofficial fan-made tool and is not affiliated with, endorsed by, or sponsored by the publisher of *Esports Godfather*. *Esports Godfather* and related game content are the property of their respective owners.
