import copy
import json
import os
from collections import defaultdict
from threading import RLock

from langchain.chat_models import init_chat_model

from core.agent import build_agent, build_draft_agent, build_formatter
from core.data import build_global_data
from core.draft import (
    ban_hero,
    build_candidate_shortlist,
    build_draft_state,
    build_position_availability,
    get_scored_candidate,
    pick_hero,
    score_all_positions,
)
from core.graph import build_master_graph, confirm_hero_masteries
from core.hero_mastery import POSITIONS, create_empty_masteries, set_mastery
from core.persistence import (
    load_coach_messages,
    load_draft_order,
    load_model_settings,
    load_t1_masteries,
    save_model_settings,
    save_t1_masteries,
)

DEFAULT_DRAFT_ORDER = [
    ("blue", "Ban"),
    ("red", "Ban"),
    ("blue", "Ban"),
    ("red", "Ban"),
    ("blue", "Ban"),
    ("red", "Ban"),
    ("blue", "Pick"),
    ("red", "Pick"),
    ("red", "Pick"),
    ("blue", "Pick"),
    ("blue", "Pick"),
    ("red", "Pick"),
    ("red", "Pick"),
    ("blue", "Pick"),
    ("red", "Ban"),
    ("blue", "Ban"),
    ("blue", "Ban"),
    ("red", "Ban"),
    ("blue", "Pick"),
    ("red", "Pick"),
]

PROVIDERS = {
    "ollama": {
        "label": "Ollama",
        "api_key_environment": None,
        "default_model": "qwen3.5",
        "supports_base_url": True,
    },
    "openai": {
        "label": "OpenAI",
        "api_key_environment": "OPENAI_API_KEY",
        "default_model": "gpt-5-mini",
        "supports_base_url": True,
    },
    "anthropic": {
        "label": "Anthropic",
        "api_key_environment": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-6",
        "supports_base_url": False,
    },
    "google_genai": {
        "label": "Google Gemini",
        "api_key_environment": "GOOGLE_API_KEY",
        "default_model": "gemini-2.5-flash",
        "supports_base_url": False,
    },
}


class AppState:
    """Own the state for the one local user of the application."""

    def __init__(self):
        self.lock = RLock()
        self.data = build_global_data()
        self.default_graph = build_master_graph(self.data)
        self.graph = copy.deepcopy(self.default_graph)

        empty_masteries = create_empty_masteries(self.graph)
        self.t1_masteries = load_t1_masteries(empty_masteries)
        self.t2_masteries = create_empty_masteries(self.graph)
        self.confirmed_t2_positions = set()
        self.draft_order = load_draft_order(DEFAULT_DRAFT_ORDER)
        self.draft_state = None
        self.draft_recommendation = None
        self.coach_messages = load_coach_messages()

        saved_settings = load_model_settings()
        legacy_model = os.getenv("LEG_AI_MODEL", "").strip()
        legacy_provider, _, legacy_name = legacy_model.partition(":")
        self.provider = saved_settings.get("provider", legacy_provider if legacy_name else "")
        self.model_name = saved_settings.get("model", legacy_name if legacy_name else legacy_model)
        self.base_url = saved_settings.get("base_url", "")
        self.api_key = self._environment_api_key()
        self.chat_model = None
        self.agent = None
        self.draft_agent = None
        self.formatter = None

        confirm_hero_masteries(self.graph, self.t1_masteries, self.t2_masteries)

    @property
    def ai_enabled(self):
        if self.provider not in PROVIDERS or not self.model_name:
            return False
        return self.provider == "ollama" or bool(self.api_key)

    def model_settings(self):
        provider = PROVIDERS.get(self.provider, {})
        return {
            "provider": self.provider,
            "model": self.model_name,
            "base_url": self.base_url,
            "api_key_configured": bool(self.api_key),
            "enabled": self.ai_enabled,
            "api_key_environment": provider.get("api_key_environment"),
        }

    def configure_model(self, provider, model_name, base_url="", api_key=""):
        if not provider:
            self.provider = ""
            self.model_name = ""
            self.base_url = ""
            self.api_key = ""
            save_model_settings({})
            self.chat_model = None
            self.agent = None
            self.draft_agent = None
            self.formatter = None
            return self.model_settings()

        if provider not in PROVIDERS:
            raise ValueError("Unknown model provider.")
        if not model_name.strip():
            raise ValueError("A model name is required.")

        self.provider = provider
        self.model_name = model_name.strip()
        self.base_url = base_url.strip() if PROVIDERS[provider]["supports_base_url"] else ""
        if api_key.strip():
            self.api_key = api_key.strip()
        elif provider == "ollama":
            self.api_key = ""
        else:
            self.api_key = self._environment_api_key()

        save_model_settings(
            {
                "provider": self.provider,
                "model": self.model_name,
                "base_url": self.base_url,
            }
        )
        self.chat_model = None
        self.agent = None
        self.draft_agent = None
        self.formatter = None
        return self.model_settings()

    def get_chat_model(self):
        if not self.ai_enabled:
            raise ValueError("The configured provider requires an API key.")
        if self.chat_model is not None:
            return self.chat_model

        model_options = {}
        if self.api_key:
            model_options["api_key"] = self.api_key
        if self.base_url and PROVIDERS[self.provider]["supports_base_url"]:
            model_options["base_url"] = self.base_url

        self.chat_model = init_chat_model(
            self.model_name,
            model_provider=self.provider,
            **model_options,
        )
        return self.chat_model

    def get_agent(self):
        if not self.ai_enabled:
            return None
        if self.agent is None:
            self.agent = build_agent(self.data, self.get_chat_model())
        return self.agent

    def get_draft_ai(self):
        if not self.ai_enabled:
            return None, None
        if self.draft_agent is None:
            chat_model = self.get_chat_model()
            self.draft_agent = build_draft_agent(self.data, chat_model)
            self.formatter = build_formatter(chat_model)
        return self.draft_agent, self.formatter

    def _environment_api_key(self):
        provider = PROVIDERS.get(self.provider, {})
        variable = provider.get("api_key_environment")
        if not variable:
            return ""
        if self.provider == "google_genai":
            return os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        return os.getenv(variable, "")

    def set_masteries(self, team, position, levels):
        masteries = self.t1_masteries if team == "t1" else self.t2_masteries
        for hero, level in levels.items():
            set_mastery(masteries, hero, position, level)

        if team == "t1":
            save_t1_masteries(self.t1_masteries)
        else:
            self.confirmed_t2_positions.add(position)

        confirm_hero_masteries(self.graph, self.t1_masteries, self.t2_masteries)

    def start_draft(self, player_side):
        confirm_hero_masteries(self.graph, self.t1_masteries, self.t2_masteries)
        draft = build_draft_state(self.draft_order, player_side)
        draft.t1_available = build_position_availability(self.t1_masteries)
        draft.t2_available = build_position_availability(self.t2_masteries)
        self.draft_state = draft
        self.refresh_recommendation()

    def apply_draft_action(self, hero, position=None):
        draft = self._require_draft()
        acting_side, action = draft.draft_order[draft.current_step]
        team = "t1" if acting_side == draft.player_side else "t2"

        if action == "Pick":
            if position not in POSITIONS:
                raise ValueError("A valid position is required for a pick.")
            available = draft.t1_available if team == "t1" else draft.t2_available
            if hero not in available.get(position, set()):
                raise ValueError(f"{hero} is not available for {position}.")
            pick_hero(self.graph, hero, team, draft)
        else:
            available = set().union(*draft.t1_available.values(), *draft.t2_available.values())
            if hero not in available:
                raise ValueError(f"{hero} is not available to ban.")
            ban_hero(hero, draft)

        draft.current_step += 1
        self.refresh_recommendation()

    def apply_t2_knowledge(self):
        draft = self._require_draft()
        confirm_hero_masteries(self.graph, self.t1_masteries, self.t2_masteries)
        latest_available = build_position_availability(self.t2_masteries)
        unavailable = set(draft.t1_picked) | set(draft.t2_picked) | draft.banned

        for position in POSITIONS:
            draft.t2_available[position] = latest_available[position] - unavailable
        self.refresh_recommendation()

    def end_draft(self):
        self.draft_state = None
        self.draft_recommendation = None
        self.t2_masteries = create_empty_masteries(self.graph)
        self.confirmed_t2_positions.clear()
        confirm_hero_masteries(self.graph, self.t1_masteries, self.t2_masteries)

    def refresh_recommendation(self):
        self.draft_recommendation = None
        draft = self.draft_state
        if draft is None or draft.current_step >= len(draft.draft_order):
            return

        acting_side, action = draft.draft_order[draft.current_step]
        if acting_side != draft.player_side:
            return

        scoring_team = "t1" if action == "Pick" else "t2"
        position_scores = score_all_positions(
            self.graph,
            scoring_team,
            draft,
            self.data,
            POSITIONS,
        )
        if not position_scores:
            return

        shortlist = build_candidate_shortlist(position_scores)
        best = max(shortlist, key=lambda candidate: candidate["score"])
        selected_hero = best["hero"]
        selected_position = best["position"]
        analysis = "This is the strongest deterministic graph score for the current draft."

        if self.ai_enabled:
            try:
                agent, formatter = self.get_draft_ai()
                context = {
                    "action": action.lower(),
                    "candidates": shortlist,
                    "player_picks": _serialise_picks(draft.t1_picked),
                    "cpu_picks": _serialise_picks(draft.t2_picked),
                    "banned_heroes": sorted(draft.banned),
                }
                prompt = (
                    "Recommend one supplied hero and position. Treat the graph scores as "
                    "authoritative evidence, but use your hero tools when qualitative "
                    "information could justify another supplied candidate. Explain the choice "
                    "naturally as advice to a teammate.\n\nDraft context:\n"
                    + json.dumps(context, indent=2)
                )
                result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
                response_text = str(result["messages"][-1].text).strip()
                decision = formatter.invoke(
                    "Extract the recommended hero, position, and analysis from this response:\n\n"
                    + response_text
                )
                selected_hero = decision.recommended_hero
                selected_position = decision.position
                analysis = decision.analysis
                get_scored_candidate(position_scores, selected_hero, selected_position)
            except Exception as error:
                analysis += f" AI review was unavailable: {error}"
                selected_hero = best["hero"]
                selected_position = best["position"]

        scored = get_scored_candidate(position_scores, selected_hero, selected_position)
        self.draft_recommendation = {**scored, "analysis": analysis}

    def draft_payload(self):
        draft = self.draft_state
        if draft is None:
            return None

        complete = draft.current_step >= len(draft.draft_order)
        payload = {
            "player_side": draft.player_side,
            "current_step": draft.current_step,
            "total_steps": len(draft.draft_order),
            "complete": complete,
            "player_picks": _serialise_picks(draft.t1_picked),
            "cpu_picks": _serialise_picks(draft.t2_picked),
            "banned": sorted(draft.banned),
            "recommendation": self.draft_recommendation,
        }
        if complete:
            return payload

        acting_side, action = draft.draft_order[draft.current_step]
        team = "t1" if acting_side == draft.player_side else "t2"
        if action == "Pick":
            available = draft.t1_available if team == "t1" else draft.t2_available
            available_by_position = {
                position: sorted(available.get(position, set())) for position in POSITIONS
            }
        else:
            heroes = set().union(*draft.t1_available.values(), *draft.t2_available.values())
            available_by_position = {"all": sorted(heroes)}

        payload["turn"] = {
            "side": acting_side,
            "action": action,
            "is_player": acting_side == draft.player_side,
            "team": team,
            "available": available_by_position,
        }
        return payload

    def graph_relationships(self, hero, relationship_types):
        if hero not in self.graph:
            raise ValueError(f"Unknown hero: {hero}")

        grouped = defaultdict(list)
        for _, target, attributes in self.graph.out_edges(hero, data=True):
            relationship_type = attributes["type"]
            if relationship_type in relationship_types:
                grouped[relationship_type].append(target)
        return {
            relationship_type: sorted(targets) for relationship_type, targets in grouped.items()
        }

    def _require_draft(self):
        if self.draft_state is None:
            raise ValueError("No draft is currently active.")
        return self.draft_state


def _serialise_picks(picks):
    return {hero: sorted(positions) for hero, positions in picks.items()}
