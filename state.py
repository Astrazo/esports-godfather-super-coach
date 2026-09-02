"""State of the app.

Raises:
    ValueError: _description_
    ValueError: _description_
    ValueError: _description_
    ValueError: _description_
    ValueError: _description_
    ValueError: _description_
    ValueError: _description_
    ValueError: _description_

Returns:
    _type_: _description_

Yields:
    _type_: _description_
"""

import copy
import json
import os
from collections import defaultdict

from langchain.messages import AIMessageChunk

from core.agent import build_chat_model, build_coach_agent
from core.data import build_global_data
from core.draft import (
    build_candidate_shortlist,
    build_draft_state,
    build_position_availability,
    get_scored_candidate,
    score_all_positions,
)
from core.graph import build_master_graph, confirm_hero_masteries
from core.hero_mastery import POSITIONS, create_default_masteries, set_mastery
from core.persistence import (
    load_coach_messages,
    load_draft_order,
    load_model_settings,
    load_t1_masteries,
    save_coach_messages,
    save_draft_order,
    save_model_settings,
    save_t1_masteries,
)

PROVIDERS = {
    "ollama": {
        "label": "Ollama",
        "api_key_env_vars": (),
        "default_model": "qwen3.5",
        "supports_base_url": True,
    },
    "openai": {
        "label": "OpenAI",
        "api_key_env_vars": ("OPENAI_API_KEY",),
        "default_model": "gpt-5-mini",
        "supports_base_url": True,
    },
    "anthropic": {
        "label": "Anthropic",
        "api_key_env_vars": ("ANTHROPIC_API_KEY",),
        "default_model": "claude-sonnet-4-6",
        "supports_base_url": True,
    },
    "google_genai": {
        "label": "Google Gemini",
        "api_key_env_vars": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
        "default_model": "gemini-2.5-flash",
        "supports_base_url": False,
    },
}


class GameState:
    """Own all authoritative state for the one local user of the application."""

    def __init__(self):
        """
        Build graph, 
        Build and load masteries (apply to graph), 
        Load coach messages, 
        Grab data to configure model
        """
        # Init data and build the graph from it
        self.data = build_global_data()
        self.default_graph = build_master_graph(self.data)
        self.graph = copy.deepcopy(self.default_graph)

        # Setup masteries and apply to the graph
        empty_masteries = create_default_masteries(self.graph)
        self.t1_masteries = load_t1_masteries(empty_masteries)
        self.t2_masteries = create_default_masteries(self.graph)
        confirm_hero_masteries(self.graph, self.t1_masteries, self.t2_masteries)

        # Setup draft data
        self.draft_order = load_draft_order()
        self.draft_state = None
        self.draft_recommendation = None

        # Load in coach messages
        self.coach_messages = load_coach_messages()

        # Setup model configuration
        saved_settings = load_model_settings()
        self.provider = saved_settings.get("provider")
        self.model_name = saved_settings.get("model")
        self.base_url = saved_settings.get("base_url", "")
        self.api_key = self.get_key_from_env_vars()
        self.chat_model = None
        self.coach_agent = None

 
    ###
    # Model configuration and optional AI services
    ###
    @property
    def ai_enabled(self):

        # If we haven't setup a provider or model name, it's not enabled
        if self.provider not in PROVIDERS or not self.model_name:
            return False

        # Otherwise if we have a api key, or the provider is ollama, it's enabled
        if bool(self.api_key) or self.provider == "ollama":
            return True

        return False

    def get_model_settings(self):
        provider_config = PROVIDERS.get(self.provider, {})
        return {
            "provider": self.provider,
            "model": self.model_name,
            "base_url": self.base_url,
            "api_key_configured": bool(self.api_key),
            "enabled": self.ai_enabled,
            "api_key_env_vars": provider_config.get("api_key_env_vars"),
        }

    def configure_model(self, provider, model_name, base_url="", api_key=""):
        # If no provider, 
        if not provider:
            self.provider = ""
            self.model_name = ""
            self.base_url = ""
            self.api_key = ""
            save_model_settings({})
            self.chat_model = None
            self.coach_agent = None
            return self.get_model_settings()

        # Strip prodived data
        provider = provider.strip()
        model_name = model_name.strip()
        base_url = base_url.strip()
        api_key = api_key.strip()

        # Check provided is valid
        if provider not in PROVIDERS:
            raise ValueError("Unknown model provider.")
        if not model_name:
            raise ValueError("A model name is required.")

        # Set provider and model name
        self.provider = provider
        self.model_name = model_name

        # Handle optionals like base url and api keys
        self.base_url = base_url if PROVIDERS[provider]["supports_base_url"] else "" 
        if provider == "ollama":
            self.api_key = ""
        elif api_key.strip():
            self.api_key = api_key.strip()
        else:
            self.api_key = self.get_key_from_env_vars() # try and get API key from environment vars

        # Save model settings to file
        save_model_settings({
            "provider": self.provider,
            "model": self.model_name,
            "base_url": self.base_url,
        })

        # Clear cached object references so they're recreated when next needed
        self.chat_model = None
        self.coach_agent = None

        return self.get_model_settings()

    def _get_or_create_chat_model(self):
        """A function to get/setup the configured model.

        Returns:
            BaseChatModel: a configured langchain chat model.
        """

        # If we already have one, just return it
        if self.chat_model is not None:
            return self.chat_model

        # If not, setup options
        model_options = {}
        if self.api_key:
            model_options["api_key"] = self.api_key
        if self.base_url and PROVIDERS[self.provider]["supports_base_url"]:
            model_options["base_url"] = self.base_url

        # Build the actual langchain chat object
        self.chat_model = build_chat_model(
            provider=self.provider,
            model=self.model_name,
            options=model_options,
        )

        # Return the configured chat object
        return self.chat_model

    def _get_or_create_coach_agent(self):
        """Get or create a coach agent langchain object

        Returns:
            _type_: _description_
        """

        # If ai_enabled property is not True, return None
        if not self.ai_enabled:
            return None

        # If we don't have an agent currently built, make one
        if self.coach_agent is None:
            model = self._get_or_create_chat_model()
            self.coach_agent = build_coach_agent(self.data, self.graph_relationships, model)

        # Otherwise, just return built agent
        return self.coach_agent

    def get_key_from_env_vars(self):
        """Helper function to check env vars for an API key

        Returns:
            str: a found API key or ""
        """
        provider_config = PROVIDERS.get(self.provider, {})
        for env_var in provider_config.get("api_key_env_vars", ()):
            api_key = os.getenv(env_var, "")
            if api_key:
                return api_key

        return ""

    ###
    # Team masteries and draft lifecycle 
    ###
    def set_masteries(self, team, position, levels):
        # Set masteries of either t1 or t2
        masteries = self.t1_masteries if team == "t1" else self.t2_masteries
        for hero, level in levels.items():
            set_mastery(masteries, hero, position, level)

        # If T1, save to json
        if team == "t1":
            save_t1_masteries(self.t1_masteries)
       
        # Write the updated masteries to the graph
        confirm_hero_masteries(self.graph, self.t1_masteries, self.t2_masteries)

    def set_draft_order(self, steps: list[tuple[str, str]]):
        # Confirm steps format is correct
        for side, action in steps:
            if side not in {"blue", "red"} or action not in {"Pick", "Ban"}:
                raise ValueError("Draft steps must use blue/red and Pick/Ban.")

        # Set and save draft order if all correct
        self.draft_order = steps
        save_draft_order(self.draft_order)

    def start_draft(self, player_side):

        # Build a draft state
        draft = build_draft_state(self.draft_order, player_side)

        # Build position availability based on the current t1 and t2 masteries
        draft.t1_available = build_position_availability(self.t1_masteries)
        draft.t2_available = build_position_availability(self.t2_masteries)

        # Apply draft to this object
        self.draft_state = draft

    def apply_draft_action(self, hero, position=None):
        """Apply either a plyer pick or player ban.

        Args:
            hero (_type_): _description_
            position (_type_, optional): _description_. Defaults to None.

        Raises:
            ValueError: _description_
            ValueError: _description_
        """

        # Get current draft state and relevant properties
        draft = self.draft_state
        acting_side, action = draft.draft_order[draft.current_step]
        team = "t1" if acting_side == draft.player_side else "t2"

        if action == "Pick":
            self.set_draft_pick(team, hero, position)
        else:
            self.set_draft_ban(hero)

        # Move draft step forward and refresh recomendation
        draft.current_step += 1
        self.refresh_recommendation()

    def set_draft_pick(self, team, hero, position):
        """Direction functions for setting a draft pick."""
        if team not in {"t1", "t2"}:
            raise ValueError("Team must be t1 or t2.")
        if position not in POSITIONS:
            raise ValueError("A valid position is required.")

        if hero not in self.graph:
            raise ValueError(f"Unknown hero: {hero}")

        if position not in self.graph.nodes[hero]["tiers"]:
            raise ValueError(f"{hero} cannot play {position}.")

        self._record_draft_pick(team, hero, position)
    
        
    def set_draft_ban(self, hero):
        """Validate and toggle a ban without advancing the draft."""
        if hero not in self.graph:
            raise ValueError(f"Unknown hero: {hero}")
        return self._record_draft_ban(hero)

    def _record_draft_pick(self, team, hero, position):
            """Replace one team's lane assignment and rebuild the remaining pools."""
            # Get draft and ensure valid data 
            draft = self.draft_state
    
            # Update picks
            team_picks = draft.t1_picked if team == "t1" else draft.t2_picked
            other_picks = draft.t2_picked if team == "t1" else draft.t1_picked
    
            # A hero can only appear once across both teams, and a lane can only
            # contain one hero for the team. The newest entered value is authoritative.
            team_picks.pop(hero, None)
            other_picks.pop(hero, None)
            for picked_hero, positions in list(team_picks.items()):
                if position in positions:
                    del team_picks[picked_hero]
    
            team_picks[hero] = {position}
            draft.banned.discard(hero) # if this hero was previously banned, discard it
            self._rebuild_draft_availability()

    def _record_draft_ban(self, hero):
        """Toggle a ban and return whether the hero is now banned."""
        draft = self.draft_state

        if hero in draft.banned:
            draft.banned.remove(hero)
            self._rebuild_draft_availability()
            return False

        draft.t1_picked.pop(hero, None)
        draft.t2_picked.pop(hero, None)
        draft.banned.add(hero)
        self._rebuild_draft_availability()
        return True

    def _rebuild_draft_availability(self):
            """Recreate remaining pools from masteries and the current draft truth."""
            draft = self.draft_state
            draft.t1_available = build_position_availability(self.t1_masteries)
            draft.t2_available = build_position_availability(self.t2_masteries)
            unavailable = set(draft.t1_picked) | set(draft.t2_picked) | draft.banned
    
            for available in (draft.t1_available, draft.t2_available):
                for pool in available.values():
                    pool.difference_update(unavailable)
    
            for positions in draft.t1_picked.values():
                for position in positions:
                    draft.t1_available[position].clear()
            for positions in draft.t2_picked.values():
                for position in positions:
                    draft.t2_available[position].clear()

    def end_draft(self):
        self.draft_state = None
        self.draft_recommendation = None
        self.t2_masteries = create_default_masteries(self.graph)
        confirm_hero_masteries(self.graph, self.t1_masteries, self.t2_masteries)

    def refresh_recommendation(self):
        """Publish the best deterministic graph recommendation for this draft step."""
        self.draft_recommendation = None
        draft = self.draft_state
        if draft is None or draft.current_step >= len(draft.draft_order):
            return

        acting_side, action = draft.draft_order[draft.current_step]

        # If this isn't a player action, simply skip
        if acting_side != draft.player_side:
            return

        # Decide what team to score (if action is pick, score player team, if action is ban, score enemy team)
        scoring_team = "t1" if action == "Pick" else "t2"

        # Score all positions to find the best possible pick currently
        position_scores = score_all_positions(
            self.graph,
            scoring_team,
            draft,
            self.data,
            POSITIONS,
        )
        if not position_scores:
            return

        # Build shortlist (only take the top n heroes for consideration)
        shortlist = build_candidate_shortlist(position_scores)

        # Publish the deterministic result before any optional AI work begins.
        best = max(shortlist, key=lambda candidate: candidate["score"])
        scored = get_scored_candidate(position_scores, best["hero"], best["position"])
        self.draft_recommendation = {
            **scored,
            "analysis": "This is the strongest deterministic graph score for the current draft.",
            "source": "graph",
        }

    # Graph queries

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

    # Coach conversation

    def stream_coach_reply(self, prompt: str, during_draft: bool = False):
        """Stream a saved Coach chat reply or an independent draft reply."""
        if during_draft:
            messages = [{"role": "user", "content": self._build_draft_prompt(prompt)}]
            yield from self._stream_agent_reply(messages, persist_history=False)
        else:
            self.coach_messages.append({"role": "user", "content": prompt.strip()})
            save_coach_messages(self.coach_messages)
            yield from self._stream_agent_reply(self.coach_messages, persist_history=True)

    def _build_draft_prompt(self, question: str):
        """Build the temporary context for a question asked during a draft."""
        draft = self.draft_state
        next_action = "Draft complete"
        if draft.current_step < len(draft.draft_order):
            side, action = draft.draft_order[draft.current_step]
            next_action = f"{side.title()} {action}"
        return (
            f"Current Graph Suggestion: {_format_graph_suggestion(self.draft_recommendation)}\n"
            f"Current Action: {next_action}\n\n"
            f"Current Player Question: {question.strip()}"
        )

    def _stream_agent_reply(self, messages, persist_history: bool):
        """Stream one Coach reply, optionally retaining it as normal chat history."""
        final_messages = None

        agent = self._get_or_create_coach_agent()
        emitted_tool_calls = set()

        try:
            for part in agent.stream(
                {"messages": messages},
                stream_mode=["messages", "values"], 
                version="v2",
            ):
                # If a message (chunk), append the token and yield
                if part["type"] == "messages":
                    token, _ = part["data"]
                    if isinstance(token, AIMessageChunk):
                        # For any tool calls in this token, grab it's data
                        for tool_call in token.tool_calls:
                            call_id = tool_call.get("id")
                            call_key = call_id or (
                                tool_call["name"],
                                json.dumps(tool_call.get("args", {}), sort_keys=True),
                            )
                            # If already seen, don't yield
                            if call_key in emitted_tool_calls:
                                continue

                            # Many more chunks will probably come from this tool call, only yield the first one
                            emitted_tool_calls.add(call_key)
                            yield {
                                "type": "tool_call",
                                "name": tool_call["name"],
                                "args": tool_call.get("args", {}),
                            }

                        if token.text:
                            yield {"type": "text", "content": token.text}
                # Otherwise if it's value, add it to the final messages for serialisation at the end
                elif part["type"] == "values":
                    final_messages = part["data"]["messages"]
        finally:
            if persist_history and final_messages is not None:
                self.coach_messages = _serialise_agent_messages(final_messages)
                save_coach_messages(self.coach_messages)

    def clear_coach_messages(self):
        self.coach_messages = []
        save_coach_messages([])

def _format_graph_suggestion(recommendation):
    """Format graph suggestion to be fed to coach if a question is asked regarding it.

    Args:
        recommendation (_type_): _description_

    Returns:
        _type_: _description_
    """
    if recommendation is None:
        return "None available"

    reasons = recommendation.get("explanation", {})
    reason_text = "; ".join(
        f"{reason.replace('_', ' ')}: {', '.join(map(str, values))}"
        for reason, values in reasons.items()
        if values
    ) or "No graph reasons recorded"
    alternatives = ", ".join(
        f"{candidate['hero']} ({candidate['score']:g})"
        for candidate in recommendation.get("candidates", [])[1:4] # don't show the top one(that's thre recomendation)
    )
    suggestion_text = (
        f"{recommendation['hero']} {recommendation['position']} "
        f"(score {recommendation['score']:g}). Reasons: {reason_text}. "
        f"Top alternatives in this position: {alternatives or 'None'}"
    )
    return suggestion_text


def _serialise_agent_messages(messages):
    """Keep completed chat exchanges without resending raw tool traffic."""
    outputs = []
    for message in messages:
        if message.type == "human":
            outputs.append({"role": "human", "content": str(message.text)})
        elif message.type == "ai" and not message.tool_calls and message.text:
            outputs.append({"role": "ai", "content": str(message.text)})
    return outputs
