"""Offline coverage for each supported AI provider configuration.

These tests deliberately replace the LangChain provider factory.  They verify
our configuration and request-construction code without needing an account,
API key, local model, or network connection.
"""

import pytest

import state
from core import agent


CLOUD_PROVIDERS = [
    ("openai", "OPENAI_API_KEY"),
    ("anthropic", "ANTHROPIC_API_KEY"),
    ("google_genai", "GOOGLE_API_KEY"),
]


@pytest.mark.parametrize("provider,key_variable", CLOUD_PROVIDERS)
def test_cloud_provider_uses_its_environment_key(game, monkeypatch, provider, key_variable):
    """Every cloud provider can be enabled from its documented environment key."""
    monkeypatch.setenv(key_variable, "test-key")

    settings = game.configure_model(provider, "test-model")

    assert settings["enabled"] is True
    assert settings["api_key_configured"] is True
    assert game.api_key == "test-key"


@pytest.mark.parametrize(
    ("provider", "api_key", "base_url", "expected_options"),
    [
        ("ollama", "ignored-key", "http://localhost:11434", {"base_url": "http://localhost:11434"}),
        (
            "openai",
            "openai-test-key",
            "http://localhost:8000/v1",
            {"api_key": "openai-test-key", "base_url": "http://localhost:8000/v1"},
        ),
        (
            "anthropic",
            "anthropic-test-key",
            "http://localhost:8001",
            {"api_key": "anthropic-test-key", "base_url": "http://localhost:8001"},
        ),
        (
            "google_genai",
            "google-test-key",
            "http://this-provider-does-not-support-base-urls",
            {"api_key": "google-test-key"},
        ),
    ],
)
def test_provider_model_is_built_with_expected_options(
    game, monkeypatch, provider, api_key, base_url, expected_options
):
    """Check the exact provider options passed to LangChain for every route."""
    captured = {}
    fake_model = object()

    def fake_build_chat_model(provider, model, options):
        captured.update(provider=provider, model=model, options=options)
        return fake_model

    monkeypatch.setattr(state, "build_chat_model", fake_build_chat_model)
    game.configure_model(provider, "test-model", base_url, api_key)

    assert game._get_or_create_chat_model() is fake_model
    assert captured == {
        "provider": provider,
        "model": "test-model",
        "options": expected_options,
    }
    # The configured model is cached; opening Coach again must not rebuild it.
    assert game._get_or_create_chat_model() is fake_model


def test_ollama_is_enabled_without_an_api_key(game):
    """Ollama remains the no-key path for a local end-to-end smoke test."""
    settings = game.configure_model("ollama", "qwen3.5")

    assert settings["enabled"] is True
    assert settings["api_key_configured"] is False


def test_invalid_or_incomplete_cloud_configuration_is_disabled(game):
    """Avoid building a cloud client until a provider, model, and key exist."""
    assert game.ai_enabled is False

    game.configure_model("openai", "test-model")

    assert game.ai_enabled is False
    with pytest.raises(ValueError, match="Unknown model provider"):
        game.configure_model("unsupported-provider", "test-model")
    with pytest.raises(ValueError, match="model name is required"):
        game.configure_model("openai", "")


@pytest.mark.parametrize("provider", ["ollama", "openai", "anthropic", "google_genai"])
def test_langchain_factory_receives_each_provider(provider, monkeypatch):
    """Protect the thin wrapper around LangChain's provider selection API."""
    captured = {}
    expected_model = object()

    def fake_init_chat_model(**kwargs):
        captured.update(kwargs)
        return expected_model

    monkeypatch.setattr(agent, "init_chat_model", fake_init_chat_model)

    actual_model = agent.build_chat_model(provider, "test-model", {"api_key": "test-key"})

    assert actual_model is expected_model
    assert captured == {
        "model": "test-model",
        "model_provider": provider,
        "api_key": "test-key",
    }
