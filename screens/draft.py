import json

import streamlit as st

from core.draft import (
    ban_hero,
    build_draft_state,
    build_position_availability,
    pick_hero,
    recommend_pick,
)
from core.graph import confirm_hero_masteries
from core.hero_mastery import POSITIONS, create_empty_masteries
from core.runtime import load_game
from screens.common import mastery_editor


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


def start_draft(graph, player_side):
    confirm_hero_masteries(
        graph,
        st.session_state.t1_masteries,
        st.session_state.t2_masteries,
    )

    draft_state = build_draft_state(st.session_state.draft_order, player_side)
    draft_state.t1_available = build_position_availability(st.session_state.t1_masteries)
    draft_state.t2_available = build_position_availability(st.session_state.t2_masteries)
    st.session_state.draft_state = draft_state
    st.session_state.draft_analysis = {}


def render_team_picks(title, picked):
    st.markdown(f"**{title}**")
    if not picked:
        st.caption("No picks yet.")
        return

    for hero, positions in picked.items():
        position_text = ", ".join(sorted(positions)) or "No known position"
        st.write(f"{hero}: {position_text}")


def render_recommendation(data, graph, draft_state, team, position, agent):
    try:
        recommendation = recommend_pick(graph, team, position, draft_state, data)
    except (KeyError, ValueError):
        st.info(f"No known {team.upper()} heroes are available for {position}.")
        return

    render_recommendation_result(
        recommendation,
        title="Pick recommendation",
        metric_label="Best pick",
    )
    render_agent_analysis(
        agent,
        recommendation,
        draft_state,
        recommendation_type="player pick",
    )


def render_ban_recommendation(data, graph, draft_state, agent):
    recommendations = []

    for position in POSITIONS:
        try:
            recommendation = recommend_pick(
                graph,
                "t2",
                position,
                draft_state,
                data,
            )
        except (KeyError, ValueError):
            continue

        recommendations.append(recommendation)

    if not recommendations:
        st.info("No known CPU picks are available to use for a ban recommendation.")
        return

    strongest_cpu_pick = max(
        recommendations,
        key=lambda recommendation: recommendation["score"],
    )
    render_recommendation_result(
        strongest_cpu_pick,
        title="Ban recommendation",
        metric_label="Best hero to ban",
    )
    render_agent_analysis(
        agent,
        strongest_cpu_pick,
        draft_state,
        recommendation_type="player ban",
    )


def render_agent_analysis(agent, recommendation, draft_state, recommendation_type):
    position = recommendation["requested_lane"]
    recommended_hero = recommendation["recommended_hero"]
    analysis_key = (
        draft_state.current_step,
        recommendation_type,
        position,
        recommended_hero,
    )

    if st.button(
        "Ask coach to explain",
        key=f"draft_coach_{'_'.join(str(value) for value in analysis_key)}",
    ):
        context = {
            "recommendation_type": recommendation_type,
            "recommended_hero": recommended_hero,
            "position": position,
            "score": recommendation["score"],
            "reasons": recommendation["explanation"],
            "player_picks": {
                hero: sorted(positions) for hero, positions in draft_state.t1_picked.items()
            },
            "cpu_picks": {
                hero: sorted(positions) for hero, positions in draft_state.t2_picked.items()
            },
            "banned_heroes": sorted(draft_state.banned),
        }
        prompt = (
            "Explain this draft recommendation concisely. Treat the supplied "
            "recommendation as authoritative. Use your tools if hero-specific "
            "information would improve the explanation.\n\n"
            + json.dumps(context, indent=2, default=str)
        )

        with st.spinner("Coach is reviewing the draft..."):
            try:
                result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
                analysis = result["messages"][-1].content
            except Exception as error:
                st.error(f"The coach could not explain this recommendation: {error}")
            else:
                st.session_state.draft_analysis[analysis_key] = analysis

    analysis = st.session_state.draft_analysis.get(analysis_key)
    if analysis:
        st.info(analysis)


def render_recommendation_result(recommendation, title, metric_label):
    st.subheader(title)
    best = recommendation["recommended_hero"]
    score = recommendation["score"]
    explanation = recommendation["explanation"]
    better_position = recommendation["better_position"]

    st.metric(metric_label, best, f"{score:.2f} score")
    if metric_label == "Best hero to ban":
        st.caption(f"Strongest projected CPU pick for {recommendation['requested_lane']}.")

    if better_position:
        alternative_lane = better_position["lane"]
        alternative_score = better_position["score"]
        st.warning(
            f"If you can, consider {best} for {alternative_lane} instead "
            f"(scores {alternative_score:.2f} in {alternative_lane} "
            f"vs {score:.2f} in {recommendation['requested_lane']})"
        )

    for reason, heroes in explanation.items():
        values = ", ".join(str(hero) for hero in heroes)
        st.write(f"**{reason.replace('_', ' ').title()}:** {values}")

    with st.expander("All candidate scores"):
        for candidate in recommendation["candidates"]:
            st.write(f"{candidate['hero']}: {candidate['score']:.2f}")


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
                draft_state.current_step += 1
                st.rerun()


def render_active_draft(data, graph, agent):
    draft_state = st.session_state.draft_state
    cpu_side = "red" if draft_state.player_side == "blue" else "blue"

    header_columns = st.columns([3, 2, 3])
    with header_columns[0]:
        render_team_picks(
            f"Player Picks ({draft_state.player_side.title()})",
            draft_state.t1_picked,
        )
    with header_columns[1]:
        st.markdown("**Bans**")
        st.write(", ".join(sorted(draft_state.banned)) or "No bans yet.")
    with header_columns[2]:
        render_team_picks(
            f"CPU Picks ({cpu_side.title()})",
            draft_state.t2_picked,
        )

    st.divider()

    if draft_state.current_step >= len(draft_state.draft_order):
        st.success("Draft complete.")
        if st.button("End draft"):
            end_draft(graph)
            st.rerun()
        return

    acting_side, action = draft_state.draft_order[draft_state.current_step]
    is_player_turn = acting_side == draft_state.player_side
    team = "t1" if is_player_turn else "t2"
    actor = "Player" if is_player_turn else "CPU"
    step_number = draft_state.current_step + 1
    st.subheader(f"Step {step_number} of {len(draft_state.draft_order)}")
    side_marker = "🔵" if acting_side == "blue" else "🔴"
    st.info(f"{side_marker} {acting_side.title()} — {actor} {action}")

    if action == "Pick":
        position = st.selectbox("Position", POSITIONS)
        if is_player_turn:
            render_recommendation(
                data,
                graph,
                draft_state,
                team,
                position,
                agent,
            )
    else:
        position = None
        if is_player_turn:
            render_ban_recommendation(data, graph, draft_state, agent)

    search = st.text_input("Filter hero buttons", placeholder="Type a hero name...")
    render_hero_buttons(graph, draft_state, action, team, position, search)

    st.divider()
    with st.expander("Update known T2 masteries"):
        mastery_editor(
            st.session_state.t2_masteries,
            graph,
            "draft_t2_masteries",
            "Add newly discovered T2 heroes, confirm the position, then apply "
            "the updated knowledge.",
            submit_label="Confirm position masteries",
            confirmed_positions=st.session_state.confirmed_t2_positions,
        )
        if st.button("Apply T2 knowledge to draft"):
            apply_t2_knowledge(graph)
            st.success("Updated T2 availability while preserving picks and bans.")
            st.rerun()

    if st.button("End draft"):
        end_draft(graph)
        st.rerun()


def end_draft(graph):
    st.session_state.draft_state = None
    st.session_state.t2_masteries = create_empty_masteries(graph)
    st.session_state.confirmed_t2_positions = set()
    st.session_state.draft_analysis = {}

    for key in list(st.session_state):
        if key.startswith(("setup_t2_masteries_", "draft_t2_masteries_")):
            del st.session_state[key]


def render():
    data, _, agent = load_game()
    graph = st.session_state.graph

    st.header("Draft")

    if st.session_state.draft_state is not None:
        render_active_draft(data, graph, agent)
        return

    st.write(
        "Enter as much of T2's known hero mastery as you have. You can add more "
        "knowledge after the draft starts."
    )
    mastery_editor(
        st.session_state.t2_masteries,
        graph,
        "setup_t2_masteries",
        "Set the known T2 masteries for each position, then confirm that position. "
        "Unconfirmed changes are not added to T2's masteries.",
        submit_label="Confirm position masteries",
        confirmed_positions=st.session_state.confirmed_t2_positions,
    )

    confirmed_positions = st.session_state.confirmed_t2_positions
    st.caption(
        "Confirmed positions: "
        + (
            ", ".join(position for position in POSITIONS if position in confirmed_positions)
            or "None"
        )
    )

    player_side = st.radio(
        "Your side for this game",
        ["blue", "red"],
        format_func=lambda side: f"{'🔵' if side == 'blue' else '🔴'} {side.title()}",
        horizontal=True,
    )

    if st.button("Confirm T2 and start draft", type="primary"):
        start_draft(graph, player_side)
        st.rerun()


render()
