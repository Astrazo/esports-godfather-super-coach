# Esports Godfather - Super Coach

Welcome to the Esports Godfather - Super Coach.

The idea of this tool is to help bad players like myself beat the higher levels of the game by contextualising existing knowledge into a compact and easily navigable format.

The primary (and original) intent of this tool was to help you draft better lineups based on what your team can play. It takes into account the strengths and weaknesses of each hero in the pool, then deterministically determines (heh) the best course of action, be it a pick or ban. It also layers things like mastery levels and hero/position tiers on top, suggesting that it might not matter if your one-trick Wukong player is countered by five enemy heroes as long as they're Legend tier on him.

This is a simple CLI MVP. It is useful, it is opinionated, and it is not pretending to have solved the game.

## Why this exists

Like most MOBAs, this game is hard. You can sort of breeze through the easier difficulties by picking Frank every game, but that cannot be said for something like Hell mode. I wanted to help even the odds.

The result is this tool, and absolutely no guarantee that this was an efficient way to improve.

It also goes without saying that I am an ML/AI Engineer, and like any good engineer, I spent more time building this tool to help me get good at the game than it would have taken to simply get good at the game organically . But that's neither here nor there.

## Credit where it is due

As mentioned several times now, the game-specific knowledge in this project could not have come from my brain. The hero tiers, relationships, team-composition notes, itemisation guidance, glossary, and much of the Coach's factual grounding are structured from [Yippo the Clown's in-depth *Esports Godfather* guide on Steam](https://steamcommunity.com/sharedfiles/filedetails/?id=3292023160).

The graph and software are mine, but the reason why it is useful at all is because of that guide. The Coach uses these reference files as tools, then the model supplies the synthesis and wording. If the Coach gives you useful advice, credit the guide. If it gives you questionable advice, please blame my graph weights, the model, and then Yippo, in approximately that order.

## How it works

There are two separate brains involved here. The draft recommendation is deterministic code. The (optional) AI Coach is the conversational layer that can explain the recommendation, answer questions, and look up supporting information. This distinction is deliberate: the language model is not trusted to invent the draft decision from scratch... obviously.

### 1. Build the graph

The files in `data/core_data/` are loaded when the app starts.

- `hero_tiers.csv` gives each hero a tier for each position. S, A, B, C, and D become numeric scores from 5 down to 1.
- `hero_relationships.csv` records directional `Synergies`, `Counters`, `Countered_By`, and `Anti-Synergy` relationships. Some entries use tags such as `Armour` or `Assassin`; those tags are expanded into the matching heroes when the graph is built.
- The graph stores each hero's position tiers and the current player/enemy mastery data on its nodes.

In other words, a counter is not automatically mutual. If A counters B, that is an edge from A's point of view. The scoring code keeps that direction intact.

### 2. Work out what is actually available

Only heroes with mastery above 0 are considered playable for a team's position pool. Picks and bans are removed from both teams' available pools, and a confirmed pick fills that team's position. This stops the recommendation from suggesting a hero who has already been picked, banned, or assigned somewhere impossible.

### 3. Score each candidate

At the player's turn, every available hero is scored for every unfilled position they can play. The current weights are intentionally simple and visible in `core/draft.py`:

| Factor | Picked relationship | Still-available relationship |
| --- | ---: | ---: |
| Candidate counters an enemy hero | +2 | +1 |
| Candidate is countered by an enemy hero | -3 | -1.5 |
| Candidate synergises with an allied hero | +1 | +0.5 |
| Candidate has anti-synergy with an allied hero | -0.5 | -0.25 |

Two more pieces are added to that relationship score:

- **Position tier:** numeric tier × 2. An S-tier position is therefore worth 10 points before relationships and mastery are considered.
- **Position mastery:** mastery level × 1. A mastery of 7 contributes 7 points.

The candidate with the highest resulting score becomes the graph recommendation. The app also keeps the reasons that contributed to the score, so it can say “this is strong into the picked enemy and your player is highly proficient here” instead of producing a mysterious number and walking away.

The weights are a first-pass model, not sacred mathematics. They are deliberately easy to inspect and change while the project is still learning what good recommendations should look like.

### 4. Let the Coach look things up

The markdown files are primarily reference material for the AI Coach rather than direct inputs to the numeric draft score:

- `hero_info/` contains hero summaries, analysis, cards, variants, item builds, funnelling notes, and interactions.
- `role_itemisation/` contains guidance for broader build types such as ADC, mage, assassin, and tank.
- `team_comp_approaches/` contains named composition ideas and examples.
- `glossary.csv` and `types.csv` contain game terminology and attribute definitions.

When a player asks the Coach a question, the model is given a small set of deliberately scoped tools. It can request the relevant hero sections, a build archetype, a team-comp approach, a glossary definition, an attribute definition, a tier lookup, or a directional relationship lookup. The system prompt tells it to use those tools for game facts, to avoid recommending unavailable heroes, and to answer plainly after looking something up.

During a draft, the Coach also receives the current graph suggestion and draft step as context. It can explain or challenge the suggestion, but the deterministic graph remains the source of truth for the recommendation itself.

## Requirements

- Python 3.11 or later.
- A terminal that supports interactive input. Windows Terminal on Windows and Terminal on macOS are good examples.

## Install and run

Clone the repository, install the dependencies, and launch the thing:

```powershell
py -m pip install -r requirements.txt
py main.py
```

On macOS or Linux, replace `py` with `python3` if needed.

## Run tests

If you would like to check that I have not broken the important bits, install the development dependencies and run the suite from the project root:

```powershell
py -m pip install -r requirements-dev.txt
py -m pytest
```

The tests use isolated in-memory application state. They do not read or modify your local profile in `data/user_data/`, so running them should not erase your lovingly curated mastery levels.

## Setup walkthrough

The app starts at the main menu. Before the Coach can confidently judge your draft choices, complete these one-time setup steps:

1. Select **My Team** and enter the heroes each player can use in each position, with mastery from 0 to 7. A mastery of `0` removes that hero from the position, which is useful for heroes you have tried once and would rather not discuss.
2. Select **Settings** → **Draft Order** and enter the pick/ban sequence used by your game mode. For example, enter `blue ban`, `red ban`, and so on, then use `/done` to save it.
3. Select **Draft**. Enter any known enemy proficiencies in the format `Hero Mastery Position`, such as `Wolfgang 7 Mid`. You can enter several records separated by semicolons.
4. Start the draft with `/start blue` or `/start red`, depending on your team's colour.
5. Enter each pick as `Hero Position` or each ban as `Hero`. The app shows an explainable recommendation whenever it is your side's turn.

Use `/end` to stop a draft, or use the review screen at the end to correct picks and bans before closing it. This is the part where you can confirm that the tool's idea of your plan matches the plan you thought you had.

## Optional AI Coach

The deterministic draft recommendation works entirely offline. AI Coach is optional and supports Ollama, OpenAI, Anthropic, and Google Gemini.

The graph is the authority for recommendations. The language model is there to answer questions, explain trade-offs, and make the results less like reading a spreadsheet at 2 a.m.

For cloud providers, set the provider's API key in your environment before launching the app:

```powershell
$env:OPENAI_API_KEY = "your-key"
py main.py
```

Then open **Settings** → **AI Configuration**, set the provider and model name, and return to the main menu. Ollama does not need an API key. The app never displays a configured API key.

Coach conversation history is saved locally. Do not enter secrets or personal information in Coach prompts. The Coach is an enthusiastic assistant, not a vault.

## Current limitations

- The application is terminal-only; there is no web or desktop graphical interface yet. The terminal is currently the interface, for better or worse.
- It is not packaged as an installer or standalone executable yet. You will need to own a Python installation before you can blame the model.
- Initial setup is manual; there is no guided import or starter roster.
- Pick positions are treated as final during a live draft. You can correct a completed draft in review, but on-the-fly position swapping is not supported yet.
- The reference data is not patch-aware yet. Balance changes require a manual update to the included data files; you cannot select or update to a game patch from within the application yet.
- The project has a small automated smoke-test suite but no CI pipeline yet.
- Recommendations reflect the included reference data and scoring rules; validate them against current game patches and your own judgment. The Coach is not a substitute for playing the game, although that was the original problem this project was meant to avoid.

## Project structure

- `cli/` — interactive terminal menus and rendering.
- `core/` — data loading, graph scoring, draft logic, persistence, and AI integration.
- `data/core_data/` — hero, relationship, tier, itemisation, and coaching reference data.
- `data/user_data/` — player masteries, draft order, model settings, and Coach history.
- `state.py` — application state and orchestration for the CLI.

## Licence

This project is licensed under the [MIT License](LICENSE).

## Disclaimer

Esports Godfather - Super Coach is an unofficial fan-made tool and is not affiliated with, endorsed by, or sponsored by the publisher of *Esports Godfather*. *Esports Godfather* and related game content are the property of their respective owners.
