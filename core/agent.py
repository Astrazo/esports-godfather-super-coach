from langchain.agents import create_agent
from langchain.tools import tool

from core.data import (
    read_attribute_info,
    read_build_type_itemisation,
    read_glossary_definition,
    read_hero_info,
    read_team_comp_info,
)

from core.draft import recommend_pick

'''@tool 
def recommend_pick_for_position(position: str):
    """Uses the master graph to find the current highest scoring hero in this position.

    Args:
        position (str): the position to check for: Top, Jungler, Mid, Bot, Support

    Returns:
        dict: Draft recommendation containing:
                recommended_hero: The highest-scoring hero for the requested lane.
                requested_lane: The position being filled.
                score: The recommended hero's draft score.
                explanation: Factors that contributed to the score.
                better_position: Another lane where the recommended hero scores
                    higher, or None.
                candidates: Other potential picks ordered from highest to lowest
                    score, including the recommended hero as the first entry.
    """
    # Recommend a Pick
    res = recommend_pick(
        G_master, 
        "t1",
        position, 
        draft_state,
        global_data
    )

    return res'''

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
def get_item_build_info(build: str) -> str:
    """Get markdown itemisation notes for a build type.

    Args:
        role (str): the role to look up

    Returns:
        str: information on the 
    """
    return read_build_type_itemisation(build)


@tool
def define_game_term(term: str) -> str:
    """Define a game term or abbreviation from the glossary.

    Args:
        term (str): the term or abbreviation to define.

    Returns:
        str: the definition of the term or abbreviation.
    """
    return read_glossary_definition(term)


agent = create_agent(
    model="ollama:qwen3.5",
    tools=[
        get_team_comp_info,
        get_attribute_info,
        get_hero_info,
        get_item_build_info,
        define_game_term,
    ],
    system_prompt=(
        "You are a MOBA team coach. Questions given to you will be about "
        "strategy in drafts and hero playstyles."
    ),
)
