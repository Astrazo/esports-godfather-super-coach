import json
import os
import sys
from pathlib import Path


def _user_data_directory():
    configured_directory = os.getenv("LEG_USER_DATA")
    if configured_directory:
        return Path(configured_directory).expanduser()

    if getattr(sys, "frozen", False):
        local_app_data = Path(os.getenv("LOCALAPPDATA", Path.home()))
        return local_app_data / "Lazy Esports Godfather"

    project_directory = Path(__file__).resolve().parent.parent
    return project_directory / "data" / "user_data"


USER_DATA_DIRECTORY = _user_data_directory()
T1_MASTERIES_FILE = USER_DATA_DIRECTORY / "t1_masteries.json"
COACH_MESSAGES_FILE = USER_DATA_DIRECTORY / "coach_messages.json"
DRAFT_ORDER_FILE = USER_DATA_DIRECTORY / "draft_order.json"
MODEL_SETTINGS_FILE = USER_DATA_DIRECTORY / "model_settings.json"


def load_t1_masteries(default_masteries):
    saved_masteries = _read_json(T1_MASTERIES_FILE, {})
    masteries = {hero: positions.copy() for hero, positions in default_masteries.items()}

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

    if not isinstance(saved_messages, list):
        return []

    return saved_messages


def save_coach_messages(messages):
    _write_json(COACH_MESSAGES_FILE, messages)


def load_draft_order(default_order):
    saved_order = _read_json(DRAFT_ORDER_FILE, None)
    if not isinstance(saved_order, list) or not saved_order:
        return default_order.copy()

    draft_order = []
    for step in saved_order:
        if (
            not isinstance(step, list)
            or len(step) != 2
            or step[0] not in {"blue", "red", "t1", "t2"}
            or step[1] not in {"Pick", "Ban"}
        ):
            return default_order.copy()

        side = {"t1": "blue", "t2": "red"}.get(step[0], step[0])
        draft_order.append((side, step[1]))

    return draft_order


def save_draft_order(draft_order):
    _write_json(DRAFT_ORDER_FILE, draft_order)


def load_model_settings():
    settings = _read_json(MODEL_SETTINGS_FILE, {})
    return settings if isinstance(settings, dict) else {}


def save_model_settings(settings):
    _write_json(MODEL_SETTINGS_FILE, settings)


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
