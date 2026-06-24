from langchain.agents import create_agent
from langchain.tools import tool

from core.data import read_glossary_definition, read_hero_info, read_role_itemisation


@tool
def get_hero_info(hero_name: str) -> str:
    """Get markdown notes on a specific hero by name.

    Args:
        hero_name (str): the name of the hero you want to look up
    """
    return read_hero_info(hero_name)


@tool
def get_item_build_info(role: str) -> str:
    """Get markdown itemisation notes for a role or item archetype.

    Args:
        role (str): the role or item archetype to look up
    """
    return read_role_itemisation(role)


@tool
def define_game_term(term: str) -> str:
    """Define a game term or abbreviation from the glossary.

    Args:
        term (str): the term or abbreviation to define
    """
    return read_glossary_definition(term)


agent = create_agent(
    model="ollama:qwen3.5",
    tools=[get_hero_info, get_item_build_info, define_game_term],
    system_prompt=(
        "You are a MOBA team coach. Questions given to you will be about "
        "strategy in drafts and hero playstyles."
    ),
)
