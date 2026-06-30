import streamlit as st

from core.hero_mastery import POSITIONS, set_mastery


def mastery_editor(
    masteries,
    graph,
    editor_key,
    description,
    submit_label="Save masteries",
    confirmed_positions=None,
):
    st.caption(description)

    position = st.selectbox("Position", POSITIONS, key=f"{editor_key}_position")
    search = st.text_input(
        "Filter heroes",
        key=f"{editor_key}_search",
        placeholder="Type a hero name...",
    )

    all_position_heroes = sorted(hero for hero in graph.nodes if position in masteries[hero])
    visible_heroes = [hero for hero in all_position_heroes if search.lower() in hero.lower()]

    if not visible_heroes:
        st.info("No heroes match this position and filter.")
        return False

    pending_key = f"{editor_key}_pending_{position}"
    if pending_key not in st.session_state:
        st.session_state[pending_key] = {
            hero: masteries[hero][position] for hero in all_position_heroes
        }

    pending_levels = st.session_state[pending_key]
    columns = st.columns(3)

    for index, hero in enumerate(visible_heroes):
        with columns[index % len(columns)]:
            pending_levels[hero] = st.number_input(
                hero,
                min_value=0,
                max_value=7,
                value=pending_levels[hero],
                step=1,
                key=f"{editor_key}_{position}_{hero}",
            )

    has_changes = any(
        pending_levels[hero] != masteries[hero][position] for hero in all_position_heroes
    )
    if has_changes:
        st.caption("You have unsaved mastery changes for this position.")

    submitted = st.button(
        submit_label,
        type="primary",
        disabled=not has_changes and confirmed_positions is None,
        key=f"{editor_key}_save_{position}",
    )

    if submitted:
        for hero, level in pending_levels.items():
            set_mastery(masteries, hero, position, level)
        if confirmed_positions is not None:
            confirmed_positions.add(position)
            st.success(f"Confirmed {position} masteries.")
        else:
            st.success(f"Saved {position} masteries.")

    return submitted
