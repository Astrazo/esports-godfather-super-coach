"""Handles extraction of data for agents

Raises:
    InvalidDataError: _description_
    InvalidDataError: _description_

Returns:
    _type_: _description_
"""

from collections import defaultdict
import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class GlobalData:
    hero_names: set[str]  # for building master graph
    tier_map: dict[str, int]  # in case of logging or ad-hoc conversions
    tier_map_rev: dict[int, str]  # in case of logging or ad-hoc conversions
    hero_relationships: pd.DataFrame  # for global helpers
    # For building master graph e.g. {Frank: {top: 5, mid: 4}, Peter: {support: 5}
    hero_tiers: dict[str, dict[str, int]]
    tag_hero_map: dict[str, list[str]]  # for importing hero names for tags
    hero_mastery_choices: dict[list[str]]  # listing all optimal mastery choices


class InvalidDataError(Exception):
    pass


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_DIRECTORY / "data" / "core_data"
HERO_INFO_DIRECTORY = DATA_DIRECTORY / "hero_info"
ROLE_ITEMISATION_DIRECTORY = DATA_DIRECTORY / "role_itemisation"
TEAM_COMP_DIRECTORY = DATA_DIRECTORY / "team_comp_approaches"
GLOSSARY_FILE = DATA_DIRECTORY / "glossary.csv"
TYPES_FILE = DATA_DIRECTORY / "types.csv"
ITEM_BUILDS = DATA_DIRECTORY / "item_builds.md"

ROLE_ITEMISATION_ALIASES = {
    "tank": "pure_tank",
    "pure tank": "pure_tank",
    "full tank": "pure_tank",
    "tank one damage": "tank_one_damage_item",
    "tank one damage item": "tank_one_damage_item",
    "fighter": "bruiser",
    "gladiator": "bruiser",
    "marksman": "adc",
    "bot": "adc",
    "bot laner": "adc",
    "multi hitter": "multi_hitter",
    "multi-hitter": "multi_hitter",
    "multi attacker": "multi_hitter",
    "multi-attacker": "multi_hitter",
    "aoe": "aoe",
    "area of effect": "aoe",
    "one slap chap": "one_slap_chap",
    "buffer": "buffer",
    "support": "buffer",
    "seat warmer": "seat_warmer",
    "special case": "special_case",
}

def read_hero_info(hero_name: str) -> str:
    """Return the markdown notes for a hero."""
    hero_info_path = HERO_INFO_DIRECTORY / _hero_name_to_info_filename(hero_name)

    if not hero_info_path.exists():
        return f"No hero info found for '{hero_name}'. Ask the user to clarify the hero name."
    
    hero_info = hero_info_path.read_text(encoding="utf-8")
    
    # Take apart the headings
    summary = _extract_markdown_section(hero_info, heading="Hero Summary")
    analysis = _extract_markdown_section(hero_info, heading="Hero Analysis")
    description = _extract_markdown_section(hero_info, heading="Hero Description")
    variants = _extract_markdown_section(hero_info, heading="Variants")
    interactions = _extract_markdown_section(hero_info, heading="Interactions")

    sections = [
        ("Hero Summary", summary),
        ("Hero Analysis", analysis),
        ("Hero Description", description),
        ("Variants", variants),
        ("Interactions", interactions),
    ]

    return "\n\n".join(
        f"# {heading}\n{content}"
        for heading, content in sections
        if content
    ) 


def read_build_type_itemisation(role: str) -> str:
    """Return the markdown notes for a role's itemisation."""
    itemisation_path = ROLE_ITEMISATION_DIRECTORY / _role_to_itemisation_filename(role)

    if not itemisation_path.exists():
        return f"No itemisation info found for '{role}'. Ask the user to clarify the role."

    return itemisation_path.read_text(encoding="utf-8")


def read_team_comp_info(comp_name: str) -> str:
    """Return the markdown notes for a team composition approach."""
    comp_filename = f"{_text_to_slug(comp_name)}.md"
    comp_path = TEAM_COMP_DIRECTORY / comp_filename

    if not comp_path.exists():
        return (
            f"No team composition information found for '{comp_name}'. "
            "Ask the user to clarify the team composition name."
        )

    return comp_path.read_text(encoding="utf-8")


def read_glossary_definition(term: str) -> str:
    """Return the definition for a game term."""
    glossary = _load_glossary()
    normalised_term = term.strip().lower()

    for glossary_term, definition in glossary.items():
        if glossary_term.lower() == normalised_term:
            return f"The definition for {glossary_term} is: {definition}"

    return f"No glossary definition found for '{term}'.  Ask the user to clarify the term if you do not know it from general MOBA or card game knowledge."


def read_attribute_info(category: str, instance: str) -> str:
    """Return information about a hero class, attack type, or damage type."""
    normalised_category = category.strip().lower().replace(" ", "_")
    normalised_instance = instance.strip().lower()

    with TYPES_FILE.open(newline="", encoding="utf-8-sig") as file:
        rows = csv.DictReader(file)

        for row in rows:
            row_category = row["category"].strip().lower()
            row_name = row["name"].strip()

            if row_category != normalised_category:
                continue

            if row_name.lower() != normalised_instance:
                continue

            description = row["description"].strip()
            display_category = row_category.replace("_", " ")
            return f"{row_name} is a {display_category}. {description}"

    return (
        f"No attribute information found for '{instance}' in category "
        f"'{category}'. Ask the user to clarify the category or attribute."
    )


def _hero_name_to_info_filename(hero_name: str) -> str:
    """Convert a display hero name into the matching hero info markdown filename."""
    return f"{_text_to_slug(hero_name)}.md"


def _role_to_itemisation_filename(role: str) -> str:
    """Convert a role or role alias into the matching itemisation markdown filename."""
    normalised_role = role.strip().lower()
    slug = ROLE_ITEMISATION_ALIASES.get(normalised_role, _text_to_slug(normalised_role))
    return f"{slug}.md"


def _text_to_slug(text: str) -> str:
    """Convert display text into the snake_case filenames used by markdown data."""
    filename_parts = []
    previous_was_separator = False

    for character in text.strip().lower():
        if character.isalnum():
            filename_parts.append(character)
            previous_was_separator = False
            continue

        if not previous_was_separator:
            filename_parts.append("_")
            previous_was_separator = True

    return "".join(filename_parts).strip("_")


def _load_glossary() -> dict[str, str]:
    """Load glossary terms from the user-editable CSV file."""
    with GLOSSARY_FILE.open(newline="", encoding="utf-8-sig") as file:
        rows = csv.DictReader(file)
        return {
            row["term"].strip(): row["definition"].strip()
            for row in rows
            if row["term"].strip()
        }


def build_global_data() -> GlobalData:
    """_summary_

    Raises:
        InvalidDataError: _description_

    Returns:
        GlobalData: _description_
    """
    # Import both files
    relationships = pd.read_csv(
        DATA_DIRECTORY / "hero_relationships.csv", keep_default_na=False
    ).drop(columns=["Unnamed: 7", "Global Notes"])
    tiers = pd.read_csv(DATA_DIRECTORY / "hero_tiers.csv").drop(columns=["Unnamed: 3"])

    # Validate relationships and tiers
    invalid_heros = _validate_data(hero_tiers=tiers, hero_relationships=relationships)

    if not invalid_heros:
        # Build Tier maps
        tier_map = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
        tier_map_rev = {score: tier for tier, score in tier_map.items()}

        # Build a list of hero names from relationships
        hero_names = set(relationships["Name"].to_list())

        # Add a numeric score to tiers for hero suggestion scoring
        tiers["Tier_Score"] = tiers["Tier"].map(tier_map)

        # Build a tag to hero mapping so heroes can replaced tags when required
        tag_hero_map = _build_tag_hero_map(hero_names, relationships)

        # Build hero tiers dict
        hero_tiers = defaultdict(dict)
        for _, row in tiers.iterrows():
            hero_tiers[row["Name"]][row["Position"]] = row["Tier_Score"]

        # TODO Load in hero mastery choices
        HERO_MASTERY_CHOICES = {
            
        }

        # Build static class for globals
        return GlobalData(
            hero_names=hero_names,
            tier_map=tier_map,
            tier_map_rev=tier_map_rev,
            hero_relationships=relationships,
            hero_tiers=hero_tiers,
            tag_hero_map=tag_hero_map,
            hero_mastery_choices=HERO_MASTERY_CHOICES
        )
    else:
        raise InvalidDataError(f"Hero names in files do not match: {invalid_heros}")


def _validate_data(hero_tiers: pd.DataFrame, hero_relationships: pd.DataFrame) -> list[str]:
    """Simple function to validate the datasheets for the project.

    Args:
        hero_tiers (pd.DataFrame): Pandas Dataframe for hero tiers.
        hero_relationships (pd.DataFrame): Pandas Dataframe for hero relationships.

    Raises:
        InvalidDataError: Custom exception raised if data is not valid.

    Returns:
        list[str]: List of mismatching heroes.  If there's none, returns an empty list.
    """
    # Grab all hero names in both sets of data
    tier_heroes = set(hero_tiers["Name"].unique().tolist())
    relationship_heroes = set(hero_relationships["Name"].tolist())

    # First check if their lengths are the same
    if len(tier_heroes) != len(relationship_heroes):
        raise InvalidDataError("Hero count files do not match.")

    mismatches = []
    for hero in tier_heroes:
        if hero in relationship_heroes:
            continue
        mismatches.append(hero)

    return mismatches


# Build tag -> hero lookup so we can pump in heros if we see tags for synergies etc.
def _build_tag_hero_map(
    hero_names: list[str], hero_relationships: pd.DataFrame
) -> dict[str, list[str]]:
    """Function that builds a tag -> hero mapping.

    In the relationships file, some counters/synergies/etc. are represented with tags.  In order for the graph to work, we need to map to explicit heroes.
    Therefore, this exists as a way to resolve tags to heros so we can connect nodes within the graph.

    Args:
        hero_names (list[str]): List of all hero names.
        hero_relationships (pd.DataFrame): Pandas dataframe consisting of hero relationships.

    Returns:
        dict[str, list[str]]: A lookup for each tag -> heroes that contain that tag.
    """
    lookup = defaultdict(list)
    for hero in hero_names:
        hero_data = hero_relationships[hero_relationships["Name"] == hero]
        hero_tags = hero_data["Tags"].tolist()[0].split(",")
        for tag in hero_tags:
            lookup[tag].append(hero)
    return lookup


def _extract_markdown_section(markdown: str, heading: str, level: int = 1) -> str:
    """Grabs data from a specific markdown section of some text.

    Args:
        markdown (str): _description_
        heading (str): _description_
        level (int, optional): _description_. Defaults to 1.

    Returns:
        str: _description_
    """
    heading_marker = "#" * level
    target = f"{heading_marker} {heading}".casefold()

    section_lines = []
    inside_section = False

    for line in markdown.splitlines():
        stripped = line.strip()

        if stripped.casefold() == target:
            inside_section = True
            continue

        if inside_section and stripped.startswith("#"):
            marker = stripped.split(maxsplit=1)[0]

            if set(marker) == {"#"} and len(marker) <= level:
                break

        if inside_section:
            section_lines.append(line)

    return "\n".join(section_lines).strip()
