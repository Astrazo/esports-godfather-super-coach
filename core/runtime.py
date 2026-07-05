import copy

import streamlit as st

from core.agent import build_agent, build_draft_agent
from core.data import build_global_data
from core.graph import build_master_graph, confirm_hero_masteries
from core.hero_mastery import create_empty_masteries
from core.persistence import load_coach_messages, load_draft_order, load_t1_masteries

DEFAULT_DRAFT_ORDER = [
    ("blue", "Ban"),
    ("red", "Ban"),
    ("blue", "Ban"),
    ("red", "Ban"),
    ("blue", "Ban"),
    ("red", "Ban"),
    ("blue", "Pick"),
    ("red", "Pick"),
    ("red", "Pick"),
    ("blue", "Pick"),
    ("blue", "Pick"),
    ("red", "Pick"),
    ("red", "Pick"),
    ("blue", "Pick"),
    ("red", "Ban"),
    ("blue", "Ban"),
    ("blue", "Ban"),
    ("red", "Ban"),
    ("blue", "Pick"),
    ("red", "Pick"),
]


# This survives browser refreshes, but not a Streamlit server restart.
@st.cache_resource
def load_game():
    data = build_global_data()
    graph = build_master_graph(data)
    agent = build_agent(data)
    draft_agent = build_draft_agent(data)
    return data, graph, agent, draft_agent


def initialise_session(default_graph):
    if "graph" not in st.session_state:
        st.session_state.graph = copy.deepcopy(default_graph)

    graph = st.session_state.graph

    if "t1_masteries" not in st.session_state:
        empty_masteries = create_empty_masteries(graph)
        st.session_state.t1_masteries = load_t1_masteries(empty_masteries)

    if "t2_masteries" not in st.session_state:
        st.session_state.t2_masteries = create_empty_masteries(graph)

    if "draft_state" not in st.session_state:
        st.session_state.draft_state = None
    elif st.session_state.draft_state is not None and not hasattr(
        st.session_state.draft_state, "player_side"
    ):
        st.session_state.draft_state = None

    if "confirmed_t2_positions" not in st.session_state:
        st.session_state.confirmed_t2_positions = set()

    if "draft_order" not in st.session_state:
        st.session_state.draft_order = load_draft_order(DEFAULT_DRAFT_ORDER)
    else:
        st.session_state.draft_order = [
            ({"t1": "blue", "t2": "red"}.get(side, side), action)
            for side, action in st.session_state.draft_order
        ]

    if "draft_analysis" not in st.session_state:
        st.session_state.draft_analysis = {}

    if "coach_messages" not in st.session_state:
        st.session_state.coach_messages = load_coach_messages()

    confirm_hero_masteries(
        graph,
        st.session_state.t1_masteries,
        st.session_state.t2_masteries,
    )
