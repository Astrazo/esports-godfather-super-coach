import json

import streamlit as st

from core.agent import DraftRecommendationDecision
from core.draft import (
    ban_hero,
    build_candidate_shortlist,
    build_draft_state,
    build_position_availability,
    pick_hero,
    score_all_positions,
    select_scored_candidate,
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

    recommended_position = None
    if is_player_turn:
        if action == "Pick":
            scoring_team = "t1"
            recommendation_type = "player pick"
            title = "Pick recommendation"
            metric_label = "Best hero to pick"
            empty_message = "No known player picks are available."
        else:
            scoring_team = "t2"
            recommendation_type = "player ban"
            title = "Ban recommendation"
            metric_label = "Best hero to ban"
            empty_message = "No known CPU picks are available to evaluate."

        graph_scores = score_all_positions(
            graph,
            scoring_team,
            draft_state,
            data,
            POSITIONS,
        )

        if not graph_scores:
            st.info(empty_message)
        else:
            shortlist = build_candidate_shortlist(graph_scores)
            analysis_key = (
                draft_state.current_step,
                recommendation_type,
                json.dumps(shortlist, sort_keys=True, default=str),
            )
            cached_result = st.session_state.draft_analysis.get(analysis_key)

            if cached_result:
                recommendation, analysis = cached_result
            else:
                context = {
                    "recommendation_type": recommendation_type,
                    "candidates": shortlist,
                    "player_picks": {
                        hero: sorted(positions) for hero, positions in draft_state.t1_picked.items()
                    },
                    "cpu_picks": {
                        hero: sorted(positions) for hero, positions in draft_state.t2_picked.items()
                    },
                    "banned_heroes": sorted(draft_state.banned),
                }
                prompt = (
                    "Choose the best hero and position for the current draft action. "
                    "Use the graph results as authoritative evidence and consult tools when "
                    "hero-specific information would improve the decision. Explain the choice "
                    "as direct advice to a teammate, using concrete draft-specific reasons. \n"
                    "The analysis must be one or two complete sentences and no more than 80 words. Do not mention numeric scores."
                    "Close all JSON strings and braces before finishing.\n\n"
                    "Return your answer in exactly one raw JSON object using this structure:\n"
                    """
                {
                "recommended_hero": "Exact supplied hero name",
                "position": "Top, Jungler, Mid, Bot, or Support",
                "analysis": "Concise explanation of the decision"
                }
                """
                    "\nDraft context:\n"
                    + json.dumps(context, indent=2, default=str)
                )
                with st.spinner("Coach is reacting to the draft..."):
                    try:
                        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
                        response_text = str(result["messages"][-1].text).strip()
                        print(response_text)
                        decision = DraftRecommendationDecision.model_validate_json(response_text)
                        recommendation = select_scored_candidate(
                            graph_scores,
                            decision.recommended_hero,
                            decision.position,
                        )
                        analysis = decision.analysis
                    except Exception as error:
                        recommendation = max(
                            graph_scores,
                            key=lambda score: score["score"],
                        )
                        analysis = (
                            "The qualitative review failed, so this uses the highest "
                            f"graph score. Details: {error}"
                        )

                st.session_state.draft_analysis[analysis_key] = (
                    recommendation,
                    analysis,
                )

            recommended_position = recommendation["requested_lane"]
            best = recommendation["best_hero"]
            score = recommendation["score"]

            st.subheader(title)
            st.metric(metric_label, best, f"{score:.2f} score")
            if action == "Ban":
                st.caption(f"Strongest projected CPU pick for {recommendation['requested_lane']}.")

            better_position = recommendation["better_position"]
            if better_position:
                alternative_lane = better_position["lane"]
                alternative_score = better_position["score"]
                st.warning(
                    f"If you can, consider {best} for {alternative_lane} instead "
                    f"(scores {alternative_score:.2f} in {alternative_lane} "
                    f"vs {score:.2f} in {recommendation['requested_lane']})"
                )

            for reason, heroes in recommendation["explanation"].items():
                values = ", ".join(str(hero) for hero in heroes)
                st.write(f"**{reason.replace('_', ' ').title()}:** {values}")

            st.info(analysis)
            with st.expander("All candidate scores"):
                for candidate in recommendation["candidates"]:
                    st.write(f"{candidate['hero']}: {candidate['score']:.2f}")

    if action == "Pick":
        default_position_index = (
            POSITIONS.index(recommended_position) if recommended_position in POSITIONS else 0
        )

        position = st.selectbox(
            "Position",
            POSITIONS,
            index=default_position_index,
            key=f"draft_position_{draft_state.current_step}",
        )
    else:
        position = None

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
        if key.startswith(("setup_t2_masteries_", "draft_t2_masteries_", "draft_position_")):
            del st.session_state[key]


def render():
    data, _, _, draft_agent = load_game()
    graph = st.session_state.graph

    st.header("Draft")

    if st.session_state.draft_state is not None:
        render_active_draft(data, graph, draft_agent)
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
