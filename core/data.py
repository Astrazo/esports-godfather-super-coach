from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class GlobalData:
    hero_names: set[str]  # for building master graph
    tier_map: dict[str, int]  # in case of logging or ad-hoc conversions
    tier_map_rev: dict[int, str]  # in case of logging or ad-hoc conversions
    hero_relationships: pd.DataFrame  # for global helpers
    hero_tiers: dict[str, dict[str, int]]  # for building master graph e.g. {Frank: {top: 5, mid: 4}, Peter: {support: 5}
    tag_hero_map: dict[str, list[str]]  # for importing hero names for tags


class InvalidDataError(Exception):
    pass


DATA_DIRECTORY = Path(__file__).parent.parent / "data"


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

        # Build static class for globals
        return GlobalData(
            hero_names=hero_names,
            tier_map=tier_map,
            tier_map_rev=tier_map_rev,
            hero_relationships=relationships,
            hero_tiers=hero_tiers,
            tag_hero_map=tag_hero_map,
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
