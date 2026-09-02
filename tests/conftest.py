"""Shared fixtures for the test suite."""

import pytest

import state
from state import GameState


@pytest.fixture
def game(monkeypatch):
    """Create a game without reading or writing a user's local profile."""
    monkeypatch.setattr(state, "load_t1_masteries", lambda defaults: defaults)
    monkeypatch.setattr(state, "load_coach_messages", lambda: [])
    monkeypatch.setattr(state, "load_draft_order", lambda: None)
    monkeypatch.setattr(state, "load_model_settings", lambda: {})
    monkeypatch.setattr(state, "save_t1_masteries", lambda masteries: None)
    monkeypatch.setattr(state, "save_draft_order", lambda draft_order: None)
    monkeypatch.setattr(state, "save_model_settings", lambda settings: None)
    monkeypatch.setattr(state, "save_coach_messages", lambda messages: None)
    return GameState()
