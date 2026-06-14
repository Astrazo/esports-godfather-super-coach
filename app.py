from collections import defaultdict

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

from core.data import build_global_data
from core.draft import (
    ban_hero,
    build_draft_state,
    build_position_availability,
    pick_hero,
    recommend_pick,
)
from core.graph import build_master_graph, confirm_hero_masteries
from core.hero_mastery import POSITIONS, create_empty_masteries, set_mastery

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


def enable_page_scroll_over_inputs():
    st.html(
        """
        <script>
        const listenerKey = "__lazyGodfatherInputWheelScroll";

        if (!window[listenerKey]) {
            document.addEventListener(
                "wheel",
                (event) => {
                    if (event.ctrlKey) {
                        return;
                    }

                    const target = event.target;
                    const input = target.closest?.(
                        'input, textarea, [role="combobox"], ' +
                        '[data-testid="stNumberInput"], ' +
                        '[data-testid="stTextInput"], ' +
                        '[data-testid="stSelectbox"]'
                    );

                    if (!input || target.closest?.('[role="listbox"]')) {
                        return;
                    }

                    event.preventDefault();
                    const scrollContainer = document.querySelector(
                        '[data-testid="stMain"]'
                    );

                    if (scrollContainer) {
                        scrollContainer.scrollBy(event.deltaX, event.deltaY);
                    } else {
                        window.scrollBy(event.deltaX, event.deltaY);
                    }
                },
                { capture: true, passive: false }
            );
            window[listenerKey] = true;
        }
        </script>
        """,
        unsafe_allow_javascript=True,
    )


@st.cache_resource
def load_game():
    data = build_global_data()
    graph = build_master_graph(data)
    return data, graph


def initialise_session(graph):
    if "t1_masteries" not in st.session_state:
        st.session_state.t1_masteries = create_empty_masteries(graph)

    if "t2_masteries" not in st.session_state:
        st.session_state.t2_masteries = create_empty_masteries(graph)

    if "draft_state" not in st.session_state:
        st.session_state.draft_state = None


def mastery_editor(masteries, graph, editor_key, description):
    st.caption(description)

    position = st.selectbox(
        "Position",
        POSITIONS,
        key=f"{editor_key}_position",
    )
    search = st.text_input(
        "Filter heroes",
        key=f"{editor_key}_search",
        placeholder="Type a hero name...",
    )

    heroes = sorted(
        hero
        for hero in graph.nodes
        if position in masteries[hero] and search.lower() in hero.lower()
    )

    if not heroes:
        st.info("No heroes match this position and filter.")
        return

    with st.form(f"{editor_key}_form"):
        columns = st.columns(3)
        pending_levels = {}

        for index, hero in enumerate(heroes):
            with columns[index % len(columns)]:
                pending_levels[hero] = st.number_input(
                    hero,
                    min_value=0,
                    max_value=7,
                    value=masteries[hero][position],
                    step=1,
                    key=f"{editor_key}_{position}_{hero}",
                )

        submitted = st.form_submit_button("Save masteries", type="primary")

    if submitted:
        for hero, level in pending_levels.items():
            set_mastery(masteries, hero, position, level)
        st.success(f"Saved {position} masteries.")


def render_my_team(graph):
    st.header("My Team")
    st.write(
        "Manage the heroes your team can play. A mastery of zero makes the hero "
        "unavailable for that position."
    )
    mastery_editor(
        st.session_state.t1_masteries,
        graph,
        "t1_masteries",
        "These masteries are used as T1's roster whenever a new draft starts.",
    )


def graph_figure(graph, focus_hero, relationship_types):
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


def render_graph_explorer(data, graph):
    st.header("Master Graph")
    st.write("Explore the relationships originating from a selected hero.")

    focus_hero = st.selectbox("Hero", sorted(data.hero_names))
    relationship_types = st.multiselect(
        "Relationships",
        list(RELATIONSHIP_LABELS),
        default=list(RELATIONSHIP_LABELS),
        format_func=lambda value: RELATIONSHIP_LABELS[value],
    )

    figure, visible_edges = graph_figure(graph, focus_hero, relationship_types)
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
            st.markdown(f"**{RELATIONSHIP_LABELS[relationship_type]}:** {', '.join(targets)}")


def unavailable_heroes(draft_state):
    return set(draft_state.t1_picked) | set(draft_state.t2_picked) | draft_state.banned


def apply_t2_knowledge(graph):
    draft_state = st.session_state.draft_state
    confirm_hero_masteries(
        graph,
        st.session_state.t1_masteries,
        st.session_state.t2_masteries,
    )

    latest_available = build_position_availability(st.session_state.t2_masteries)
    unavailable = unavailable_heroes(draft_state)

    for position in POSITIONS:
        draft_state.t2_available[position] = latest_available[position] - unavailable


def start_draft(graph):
    confirm_hero_masteries(
        graph,
        st.session_state.t1_masteries,
        st.session_state.t2_masteries,
    )

    draft_state = build_draft_state()
    draft_state.t1_available = build_position_availability(st.session_state.t1_masteries)
    draft_state.t2_available = build_position_availability(st.session_state.t2_masteries)
    st.session_state.draft_state = draft_state


def render_team_picks(title, picked):
    st.markdown(f"**{title}**")
    if not picked:
        st.caption("No picks yet.")
        return

    for hero, positions in picked.items():
        position_text = ", ".join(sorted(positions)) or "No known position"
        st.write(f"{hero}: {position_text}")


def render_recommendation(data, graph, draft_state, team, position):
    st.subheader("Recommendation")
    try:
        best, score, explanation, flag, all_results = recommend_pick(
            graph,
            team,
            position,
            draft_state,
            data,
        )
    except (KeyError, ValueError):
        st.info(f"No known {team.upper()} heroes are available for {position}.")
        return

    st.metric("Best pick", best, f"{score:.2f} score")

    if flag:
        st.warning(flag)

    for reason, heroes in explanation.items():
        values = ", ".join(str(hero) for hero in sorted(heroes, key=str))
        st.write(f"**{reason.replace('_', ' ').title()}:** {values}")

    ranked_results = sorted(
        all_results.items(),
        key=lambda item: item[1][0],
        reverse=True,
    )
    with st.expander("All candidate scores"):
        for hero, result in ranked_results:
            st.write(f"{hero}: {result[0]:.2f}")


def render_hero_buttons(graph, draft_state, action, team, position, search):
    if action == "Pick":
        available = draft_state.t1_available if team == "t1" else draft_state.t2_available
        heroes = available[position]
    else:
        heroes = set().union(
            *draft_state.t1_available.values(),
            *draft_state.t2_available.values(),
        )

    filtered_heroes = sorted(hero for hero in heroes if search.lower() in hero.lower())

    if not filtered_heroes:
        st.info("No heroes match this action and filter.")
        return

    columns = st.columns(4)
    for index, hero in enumerate(filtered_heroes):
        with columns[index % len(columns)]:
            if st.button(hero, key=f"{action}_{team}_{position}_{hero}", width="stretch"):
                if action == "Pick":
                    pick_hero(graph, hero, team, draft_state)
                else:
                    ban_hero(hero, draft_state)
                st.rerun()


def render_active_draft(data, graph):
    draft_state = st.session_state.draft_state

    header_columns = st.columns([3, 2, 3])
    with header_columns[0]:
        render_team_picks("T1 Picks", draft_state.t1_picked)
    with header_columns[1]:
        st.markdown("**Bans**")
        st.write(", ".join(sorted(draft_state.banned)) or "No bans yet.")
    with header_columns[2]:
        render_team_picks("T2 Picks", draft_state.t2_picked)

    st.divider()

    control_columns = st.columns(3)
    with control_columns[0]:
        team = st.selectbox("Team", ["t1", "t2"], format_func=str.upper)
    with control_columns[1]:
        position = st.selectbox("Position", POSITIONS)
    with control_columns[2]:
        action = st.radio("Action", ["Pick", "Ban"], horizontal=True)

    if action == "Pick":
        render_recommendation(data, graph, draft_state, team, position)

    search = st.text_input("Filter hero buttons", placeholder="Type a hero name...")
    render_hero_buttons(graph, draft_state, action, team, position, search)

    st.divider()
    with st.expander("Update known T2 masteries"):
        mastery_editor(
            st.session_state.t2_masteries,
            graph,
            "draft_t2_masteries",
            "Add newly discovered T2 heroes, then apply the updated knowledge.",
        )
        if st.button("Apply T2 knowledge to draft"):
            apply_t2_knowledge(graph)
            st.success("Updated T2 availability while preserving picks and bans.")
            st.rerun()

    if st.button("End draft"):
        st.session_state.draft_state = None
        st.rerun()


def render_draft(data, graph):
    st.header("Draft")

    if st.session_state.draft_state is not None:
        render_active_draft(data, graph)
        return

    st.write(
        "Enter as much of T2's known hero mastery as you have. You can add more "
        "knowledge after the draft starts."
    )
    mastery_editor(
        st.session_state.t2_masteries,
        graph,
        "setup_t2_masteries",
        "T2 heroes with mastery above zero will be available during the draft.",
    )

    if st.button("Confirm T2 and start draft", type="primary"):
        start_draft(graph)
        st.rerun()


def main():
    st.set_page_config(
        page_title="Lazy Esports Godfather",
        page_icon="🎮",
        layout="wide",
    )
    enable_page_scroll_over_inputs()

    data, graph = load_game()
    initialise_session(graph)

    st.sidebar.title("Lazy Esports Godfather")
    page = st.sidebar.radio(
        "Navigate",
        ["My Team", "Master Graph", "Start Draft"],
    )

    if page == "My Team":
        render_my_team(graph)
    elif page == "Master Graph":
        render_graph_explorer(data, graph)
    else:
        render_draft(data, graph)


if __name__ == "__main__":
    main()
