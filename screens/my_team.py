import streamlit as st

from core.graph import confirm_hero_masteries
from core.persistence import save_t1_masteries
from screens.common import mastery_editor


def render():
    graph = st.session_state.graph

    st.header("My Team")
    st.write(
        "Manage the heroes your team can play. A mastery of zero makes the hero "
        "unavailable for that position."
    )
    saved = mastery_editor(
        st.session_state.t1_masteries,
        graph,
        "t1_masteries",
        "These masteries are used as T1's roster whenever a new draft starts.",
    )
    if saved:
        confirm_hero_masteries(
            graph,
            st.session_state.t1_masteries,
            st.session_state.t2_masteries,
        )
        save_t1_masteries(st.session_state.t1_masteries)


render()
