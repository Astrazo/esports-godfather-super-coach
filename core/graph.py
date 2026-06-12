import networkx as nx

def build_master_graph(heroes: list, tiers: dict, t1_masteries: dict, t2_masteries: dict):
    # Make the graph
    G_master = nx.MultiDiGraph()

    # Make a node for every hero
    G_master.add_nodes_from(heroes)

    # Add the position tier data
    nx.set_node_attributes(G_master, tiers, name="tiers")
    nx.set_node_attributes(G_master, t1_masteries, name="t1_masteries")
    nx.set_node_attributes(G_master, t2_masteries, name="t2_masteries")

    #G_master.nodes["Aurelio"]["masteries"]["Jungler"] += 1  # TODO build a helpder to rank up a mastery on a hero's postion
    #G_master.nodes["Zealot"]