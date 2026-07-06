from pathlib import Path
from typing import Literal

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from pydantic import BaseModel, Field

from core.data import (
    GlobalData,
    read_attribute_info,
    read_build_type_itemisation,
    read_glossary_definition,
    read_hero_info,
    read_team_comp_info,
)

SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent.parent / "system_prompt.md"
SYSTEM_PROMPT = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")

DRAFT_SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent.parent / "draft_system_prompt.md"
DRAFT_SYSTEM_PROMPT = DRAFT_SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")


class DraftRecommendationDecision(BaseModel):
    """The draft agent's choice from the supplied deterministic candidates."""

    recommended_hero: str = Field(description="The exact hero name from the supplied candidates.")
    position: Literal["Top", "Jungler", "Mid", "Bot", "Support"] = Field(
        description="The exact position paired with the selected candidate."
    )
    analysis: str = Field(
        description="A concise explanation of the choice and any qualitative tradeoffs."
    )


def _build_agent(data: GlobalData, system_prompt, model: str, response_format=None):
    @tool
    def get_hero_best_positions(hero_name: str) -> str:
        """Return the position suitabiliy for the requested hero for the requested tier.

        Args:
            hero_name (str): the name of the hero you want to check

        Returns:
            dict[str, str|dict[str, str]]: A lookup for each position and it's tier.
        """
        tiers = data.hero_tiers.get(hero_name, {})
        output = {"hero_name": hero_name, "positions": tiers}
        return output

    @tool
    def get_position_best_heroes(
        position_name: Literal["Top", "Jungler", "Mid", "Bot", "Support"],
        tier: Literal[1, 2, 3, 4, 5] = 5,
    ) -> str:
        """Return heroes whose tier for the given position matches the requested tier.

        Args:
            position_name (str): the name of the position you want to check.
            tier (int, optional): the position tier you want to check. Defaults to 5.

        Returns:
            dict[str, str | list[str]]: Heroes whose score matches the requested
            position tier.
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
    def get_team_comp_info(comp_name: str) -> str:
        """Get notes on a team comp.

        Args:
            comp_name (str): The name of the team comp.

        Returns:
            str: information regarding the team comp.
        """
        return read_team_comp_info(comp_name)

    @tool
    def get_attribute_info(category: str, instance: str) -> str:
        """Get notes on a category of hero attributes.

        Args:
            category (str): The category (hero class, attack type, damage type)
            instance (str): The attribute name, for example (gladiator, melee, magical)

        Returns:
            str: information regarding this attribute
        """
        return read_attribute_info(category, instance)

    @tool
    def get_hero_info(hero_name: str) -> str:
        """Get markdown notes on a specific hero by name.

        Args:
            hero_name (str): the name of the hero you want to look up

        Returns:
            str: information regarding this hero
        """
        return read_hero_info(hero_name)

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
        """Get markdown itemisation notes for a build type.

        Args:
            role (str): the role to look up

        Returns:
            str: information on the
        """
        return read_build_type_itemisation(build)

    @tool
    def lookup_glossary(term: str) -> str:
        """Define a game term or abbreviation from the glossary.

        Args:
            term (str): the term or abbreviation to define.

        Returns:
            str: the definition of the term or abbreviation.
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
        ],
        system_prompt=system_prompt,
        response_format=response_format,
    )

    return agent


def build_agent(data: GlobalData, model: str = "ollama:qwen3.5"):
    return _build_agent(data, SYSTEM_PROMPT, model)


def build_draft_agent(data: GlobalData, model: str = "ollama:qwen3.5"):
    return _build_agent(data, DRAFT_SYSTEM_PROMPT, model)


def build_formatter(model="ollama:qwen3.5"):
    chat_model = init_chat_model(model) if isinstance(model, str) else model
    return chat_model.with_structured_output(
        DraftRecommendationDecision,
        method="json_schema",
    )
