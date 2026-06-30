from collections import defaultdict

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

from core.runtime import load_game

RELATIONSHIP_COLORS = {
    "synergy": "#33c481",
    "counter": "#ef6461",
    "countered_by": "#f5a65b",
    "anti_synergy": "#9b72cf",
}

RELATIONSHIP_LABELS = {
    "synergy": "Synergy",
    "counter": "Counters",
    "countered_by": "Countered by",
    "anti_synergy": "Anti-synergy",
}


def _graph_figure(graph, focus_hero, relationship_types):
    visible_edges = [
        (source, target, attributes)
        for source, target, attributes in graph.out_edges(focus_hero, data=True)
        if attributes["type"] in relationship_types
    ]

    visible_nodes = {focus_hero}
    for source, target, _ in visible_edges:
        visible_nodes.add(source)
        visible_nodes.add(target)

    focused_graph = nx.MultiDiGraph()
    focused_graph.add_nodes_from(visible_nodes)
    for source, target, attributes in visible_edges:
        focused_graph.add_edge(source, target, **attributes)

    positions = nx.spring_layout(focused_graph, seed=7, k=1.7)
    figure = go.Figure()

    for relationship_type in relationship_types:
        x_values = []
        y_values = []

        for source, target, attributes in visible_edges:
            if attributes["type"] != relationship_type:
                continue

            source_x, source_y = positions[source]
            target_x, target_y = positions[target]
            x_values.extend([source_x, target_x, None])
            y_values.extend([source_y, target_y, None])

        if x_values:
            figure.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="lines",
                    name=RELATIONSHIP_LABELS[relationship_type],
                    line={
                        "color": RELATIONSHIP_COLORS[relationship_type],
                        "width": 2,
                    },
                    hoverinfo="skip",
                )
            )

    node_x = []
    node_y = []
    node_names = []
    node_colors = []

    for hero in sorted(visible_nodes):
        x_value, y_value = positions[hero]
        node_x.append(x_value)
        node_y.append(y_value)
        node_names.append(hero)
        node_colors.append("#f4c95d" if hero == focus_hero else "#4f6d9b")

    figure.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=node_names,
            textposition="top center",
            hovertext=node_names,
            hoverinfo="text",
            marker={
                "color": node_colors,
                "size": [24 if hero == focus_hero else 16 for hero in node_names],
                "line": {"color": "#ffffff", "width": 1},
            },
            showlegend=False,
        )
    )

    figure.update_layout(
        height=650,
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        xaxis={"visible": False},
        yaxis={"visible": False},
        legend={"orientation": "h"},
        hovermode="closest",
    )
    return figure, visible_edges


def render():
    data, _, _ = load_game()
    graph = st.session_state.graph

    st.header("Master Graph")
    st.write("Explore the relationships originating from a selected hero.")

    focus_hero = st.selectbox("Hero", sorted(data.hero_names))
    relationship_types = st.multiselect(
        "Relationships",
        list(RELATIONSHIP_LABELS),
        default=list(RELATIONSHIP_LABELS),
        format_func=lambda value: RELATIONSHIP_LABELS[value],
    )

    figure, visible_edges = _graph_figure(graph, focus_hero, relationship_types)
    st.plotly_chart(figure, width="stretch")

    st.subheader("Relationships")
    grouped_targets = defaultdict(list)
    for _, target, attributes in visible_edges:
        grouped_targets[attributes["type"]].append(target)

    if not grouped_targets:
        st.info("No matching outgoing relationships.")
        return

    for relationship_type in relationship_types:
        targets = sorted(grouped_targets[relationship_type])
        if targets:
            label = RELATIONSHIP_LABELS[relationship_type]
            st.markdown(f"**{label}:** {', '.join(targets)}")


render()
