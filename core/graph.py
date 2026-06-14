import networkx as nx
from core.data import GlobalData


# Edge columns types
# - key is what they're called in relationships df
# - value is what they'll be called in the graph edges
EDGE_TYPES = {
    "Synergies": "synergy",
    "Counters": "counter",
    "Countered_By": "countered_by",
    "Anti-Synergy": "anti_synergy",
}

def build_master_graph(data: GlobalData) -> nx.MultiDiGraph:
    """_summary_

    Args:
        data (GlobalData): _description_

    Returns:
        nx.MultiDiGraph: _description_
    """
    # Unpack data
    hero_names = data.hero_names
    hero_tiers = data.hero_tiers
    hero_relationships = data.hero_relationships
    tag_hero_map = data.tag_hero_map

    # Make the graph
    G_master = nx.MultiDiGraph()

    # Make a node for every hero
    G_master.add_nodes_from(hero_names)

    # Add the position tier data
    nx.set_node_attributes(G_master, hero_tiers, name="tiers")

    # Build relationship edges
    for _, row in hero_relationships.iterrows():
        hero = row["Name"]
        for col, edge_type in EDGE_TYPES.items():
            targets = resolve_tags(str(row[col]), tag_hero_map, hero_names)
            for target in targets:
                if target == hero:
                    continue
                G_master.add_edge(hero, target, type=edge_type)

    return G_master

# Applies the hero masteries to the graph
def confirm_hero_masteries(G: nx.MultiDiGraph, t1_masteries: dict[str, dict[str, int]], t2_masteries: dict[str, dict[str, int]]) -> None:
    _clear_hero_masteries(G)
    nx.set_node_attributes(G, t1_masteries, name="t1_masteries")
    nx.set_node_attributes(G, t2_masteries, name="t2_masteries")

# Ensure that the hero masteries are clean
def _clear_hero_masteries(G: nx.MultiDiGraph) -> None:
    for _, attributes in G.nodes(data=True):
        attributes.pop("t1_masteries", None)
        attributes.pop("t2_masteries", None)

# Clears hero signitures from the graph

# Subgraph builder
def build_match_graph(G, team_a_available, team_b_available):
    """_summary_

    Args:
        G (_type_): _description_
        team_a_available (_type_): _description_
        team_b_available (_type_): _description_

    Returns:
        _type_: _description_
    """
    all_available = set().union(*team_a_available.values(), *team_b_available.values())
    return G.subgraph(all_available).copy()

# Resolve tags
def resolve_tags(raw: str, tag_hero_map: dict[str, list[str]], hero_names: set[str]) -> list[str]:
    """_summary_

    Args:
        raw (str): _description_
        tag_hero_map (dict[str, list[str]]): _description_
        hero_names (set[str]): _description_

    Returns:
        list[str]: _description_
    """
    if not raw or raw.strip().lower() == "None":
        return []
    targets = []
    for token in raw.split(","):
        token = token.strip()
        if token in hero_names:
            targets.append(token)
        elif token in tag_hero_map:
            targets.extend(tag_hero_map[token])  # tag -> heroes
    return list(set(targets))  # deduplicate in case hero is named, and caught up in a tag resolve


#nx.set_node_attributes(G_master, t1_masteries, name="t1_masteries") # we'll do this on the match graph (so when a draft starts), not the master graph
    #nx.set_node_attributes(G_master, t2_masteries, name="t2_masteries")

    #G_master.nodes["Aurelio"]["masteries"]["Jungler"] += 1  # TODO build a helpder to rank up a mastery on a hero's postion
    #G_master.nodes["Zealot"]