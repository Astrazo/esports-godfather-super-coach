from pathlib import Path
from typing import Callable, Literal

from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph
from langchain.chat_models import init_chat_model
from langchain.tools import tool

from core.data import (
    GlobalData,
    read_attribute_info,
    read_build_type_itemisation,
    read_glossary_definition,
    read_hero_info,
    read_team_comp_info,
)

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
PROMPTS_DIRECTORY = PROJECT_DIRECTORY / "data" / "core_data" / "prompts"

COACH_SYSTEM_PROMPT_FILE = PROMPTS_DIRECTORY / "coach_system_prompt.md"
COACH_SYSTEM_PROMPT = COACH_SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")

def _build_agent(
    data: GlobalData,
    graph_relationships: Callable[[str, list[str]], dict[str, list[str]]],
    system_prompt,
    model: str,
    response_format=None,
) -> CompiledStateGraph:
    """Build an agent with tools.

    Args:
        data (GlobalData): _description_
        graph_relationships: Reads directional relationships from the master graph.
        system_prompt (_type_): _description_
        model (str): _description_
        response_format (_type_, optional): _description_. Defaults to None.

    Returns:
        CompiledStateGraph: an agent object supporting .invoke() and .stream()
    """
    @tool
    def get_hero_best_positions(hero_name: str) -> dict[str, object]:
        """Return every position a hero can play and its numeric tier.

        Use this tool to verify which positions a hero can play or compare their
        position suitability. Tier scores are 5=S, 4=A, 3=B, 2=C, and 1=D.

        Args:
            hero_name: The hero to look up.

        Returns:
            A dictionary with the hero name and a position-to-tier mapping.

        Limits:
            An unlisted position is unsuitable. This tool does not account for
            player masteries, current picks, bans, or draft availability.
        """
        tiers = data.hero_tiers.get(hero_name, {})
        output = {"hero_name": hero_name, "positions": tiers}
        return output

    @tool
    def get_position_best_heroes(
        position_name: Literal["Top", "Jungler", "Mid", "Bot", "Support"],
        tier: Literal[1, 2, 3, 4, 5] = 5,
    ) -> dict[str, object]:
        """Return heroes at one exact tier for a requested position.

        Use this tool to find strong heroes for a position. The default tier is
        5 (S tier); use 4=A, 3=B, 2=C, or 1=D when the question asks for them.

        Args:
            position_name: The position to search.
            tier: The exact numeric tier to match. Defaults to 5 (S tier).

        Returns:
            A dictionary with the position, requested tier, and matching heroes.

        Limits:
            This tool returns only exact tier matches. It does not account for
            player masteries, current picks, bans, or draft availability.
        """
        hero_tiers = data.hero_tiers
        heroes = {
            hero: positions[position_name]
            for hero, positions in hero_tiers.items()
            if position_name in positions
        }
        matched_heroes = []
        for hero, score in heroes.items():
            if score == tier:
                matched_heroes.append(hero)

        output = {"position_name": position_name, "heroes": matched_heroes}
        return output

    @tool
    def get_hero_relationships(
        hero_name: str,
        relationship_type: Literal[
            "counter",
            "countered_by",
            "synergy",
            "anti_synergy",
        ],
    ) -> list[str]:
        """Return heroes connected by one directional graph relationship.

        Use this tool for verified counters, synergies, and anti-synergies.

        Args:
            hero_name: The hero at the source of the relationship.
            relationship_type: The directional relationship to query. `counter`
                means the requested hero is strong against returned heroes;
                `countered_by` reverses that direction; `synergy` and
                `anti_synergy` describe positive and negative team fit.

        Returns:
            A sorted list of directly related heroes.

        Limits:
            Returns an empty list when no direct relationship is recorded. It
            does not account for draft availability, picks, bans, or masteries.
        """
        relationships = graph_relationships(hero_name, [relationship_type])
        return relationships.get(relationship_type, [])

    @tool
    def get_team_comp_info(
        comp_name: Literal[
            "Alpha Strike",
            "Bot Lane Focus",
            "Jungle Focus",
            "Premeditated Murder",
            "Single Hero",
            "Theme",
        ],
    ) -> str:
        """Return the strategy and examples for one named team composition approach.

        Use this tool when a player asks how to build around a recognised team
        composition approach or wants examples of that approach.

        Args:
            comp_name: The composition approach to look up.

        Returns:
            Verified strategy notes and example hero compositions.

        Limits:
            This describes a general composition approach, not the current
            draft's availability or a recommendation for a specific team.
        """
        return read_team_comp_info(comp_name)

    @tool
    def get_attribute_info(
        category: Literal["hero_class", "attack_type", "damage_type"],
        instance: str,
    ) -> str:
        """Return verified information about one hero attribute.

        Use this tool to explain a hero class, attack type, or damage type whenever the player asks about it.
        First use a hero's `Hero Analysis` section when you need to identify
        which attribute the hero has.

        Args:
            category: The attribute category to search.
            instance: The attribute value, such as `Fighter`, `Melee`, or
                `Magical`.

        Returns:
            A verified definition and its gameplay implications.

        Limits:
            Returns only information about the requested attribute; it does not
            identify which heroes have that attribute.
        """
        return read_attribute_info(category, instance)

    @tool
    def get_hero_info(
        hero_name: str,
        sections: list[
            Literal[
                "Hero Summary",
                "Hero Analysis",
                "Cards",
                "Variants",
                "Item Build",
                "Funnelling",
                "Interactions",
            ]
        ],
    ) -> str:
        """Return selected top-level reference sections for a specific hero.

        Use this tool for hero-specific facts. Request only the sections needed
        for the question to avoid loading unrelated reference material.

        Args:
            hero_name: The hero to look up.
            sections: Only request the sections needed for the question.
                - Hero Summary: A short role and strength overview.
                - Hero Analysis: Attributes and core gameplay mechanics.
                - Cards: Card descriptions and card-specific strategy.
                - Variants: Variant effects and tradeoffs.
                - Item Build: Hero-specific itemisation guidance.
                - Funnelling: Whether the hero benefits from extra resources.
                - Interactions: Synergies, counters, and special cases.

        Returns:
            The requested verified hero information.

        Limits:
            This returns static reference information only; it does not include
            current draft availability, player mastery, or graph relationships.
        """
        return read_hero_info(hero_name, sections)

    @tool
    def get_build_type_itemisation(
        build: Literal[
            "adc",
            "aoe",
            "assassin",
            "bruiser",
            "buffer",
            "mage",
            "multi hitter",
            "one slap clap",
            "pure tank",
            "seat warmer",
            "special case",
            "tank one damage item",
        ],
    ) -> str:
        """Return item recommendations, examples, and caveats for one build type.

        Use this tool after identifying a hero's relevant build type, usually
        from that hero's `Item Build` section.

        Args:
            build: The build archetype to look up.

        Returns:
            Verified recommended items, example builds, and warnings for the
            requested archetype.

        Limits:
            This is archetype-wide guidance. Combine it with hero-specific
            `Item Build` information before recommending a final build.
        """
        return read_build_type_itemisation(build)

    @tool
    def lookup_glossary(term: str) -> str:
        """Return a verified definition for an Esports Godfather term.

        Use this tool when a game term or abbreviation is unfamiliar or its
        meaning matters to the answer.

        Args:
            term: The exact term or abbreviation to define.

        Returns:
            The glossary definition, or a message that no verified definition
            was found.

        Limits:
            Do not infer a missing game-specific definition from general MOBA
            knowledge; ask the player to clarify instead.
        """
        return read_glossary_definition(term)

    agent = create_agent(
        model=model,
        tools=[
            get_hero_info,
            get_build_type_itemisation,
            lookup_glossary,
            get_attribute_info,
            get_team_comp_info,
            get_hero_best_positions,
            get_position_best_heroes,
            get_hero_relationships,
        ],
        system_prompt=system_prompt,
        response_format=response_format,
    )

    return agent

def build_chat_model(provider: str, model: str, options: dict):
    """Build a lanchain instance of the requested chat model.

    Args:
        provider (str): provider of the model.
        model (str): name of the model.
        options (dict): _description_

    Returns:
        _type_: _description_
    """
    return init_chat_model(model=model, model_provider=provider, **options)


def build_coach_agent(
    data: GlobalData,
    graph_relationships: Callable[[str, list[str]], dict[str, list[str]]],
    model: str,
) -> CompiledStateGraph:
    """Build a coach agent langchain object.

    Args:
        data (GlobalData): _description_
        graph_relationships: Reads directional relationships from the master graph.
        model: The configured chat model.

    Returns:
        CompiledStateGraph: an agent object supporting .invoke() and .stream()
    """
    return _build_agent(data, graph_relationships, COACH_SYSTEM_PROMPT, model)
