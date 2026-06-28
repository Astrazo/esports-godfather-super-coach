import json
from pathlib import Path


USER_DATA_DIRECTORY = Path(__file__).parent.parent / "user_data"
T1_MASTERIES_FILE = USER_DATA_DIRECTORY / "t1_masteries.json"
COACH_MESSAGES_FILE = USER_DATA_DIRECTORY / "coach_messages.json"


def load_t1_masteries(default_masteries):
    saved_masteries = _read_json(T1_MASTERIES_FILE, {})
    masteries = {
        hero: positions.copy() for hero, positions in default_masteries.items()
    }

    if not isinstance(saved_masteries, dict):
        return masteries

    for hero, saved_positions in saved_masteries.items():
        if hero not in masteries or not isinstance(saved_positions, dict):
            continue

        for position, level in saved_positions.items():
            if (
                position in masteries[hero]
                and isinstance(level, int)
                and not isinstance(level, bool)
                and 0 <= level <= 7
            ):
                masteries[hero][position] = level

    return masteries


def save_t1_masteries(masteries):
    _write_json(T1_MASTERIES_FILE, masteries)


def load_coach_messages():
    saved_messages = _read_json(COACH_MESSAGES_FILE, [])
    if not isinstance(saved_messages, list):
        return []

    return [
        {"role": message["role"], "content": message["content"]}
        for message in saved_messages
        if isinstance(message, dict)
        and message.get("role") in {"user", "assistant"}
        and isinstance(message.get("content"), str)
    ]


def save_coach_messages(messages):
    _write_json(COACH_MESSAGES_FILE, messages)


def _read_json(path, default):
    if not path.exists():
        return default

    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(value, file, indent=2, ensure_ascii=False)
        file.write("\n")

    temporary_path.replace(path)
