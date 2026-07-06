import json

import streamlit as st

from core.draft import (
    ban_hero,
    build_candidate_shortlist,
    build_draft_state,
    build_position_availability,
    get_scored_candidate,
    pick_hero,
    score_all_positions,
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


def render_active_draft(data, graph, agent, formatter):
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
            recommendation_type = "pick - this is a hero we are picking for our lineup"
            title = "Pick Recommendation"
            metric_label = "Suggested hero to pick."
            empty_message = "No known player picks are available."
        else:
            scoring_team = "t2"
            recommendation_type = (
                "ban - this is a hero we are banning to remove them for both teams"
            )
            title = "Ban Recommendation"
            metric_label = "Suggested hero to ban."
            empty_message = "No known CPU picks are available to evaluate."

        # Get the positions scores using the graph
        position_scores = score_all_positions(
            graph,
            scoring_team,
            draft_state,
            data,
            POSITIONS,
        )
        print(f"Position Scores: {position_scores}\n")

        if not position_scores:
            st.info(empty_message)
        else:
            # From the position scores, build a shortlist of the heroes the agent should consider
            shortlist = build_candidate_shortlist(position_scores)
            print(f"Shortlist: {shortlist}\n")

            # Store analysis so it doesn't redo itself cause streamlit is stupid
            analysis_key = (
                "candidate_lists_v2",
                draft_state.current_step,
                recommendation_type,
                json.dumps(shortlist, sort_keys=True, default=str),
            )
            cached_result = st.session_state.draft_analysis.get(analysis_key)

            # Check if analysis exists due to above reasons
            if cached_result:
                recommendation, analysis = cached_result
            else:
                # Build draft context for the agent
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
                    "Suggest the best hero and position for the current draft action. "
                    "Use the graph results as authoritative evidence and consult tools "
                    "when hero-specific information would improve the decision. You may "
                    "override the graph when verified hero information justifies it. "
                    "Explain the choice as direct advice to a teammate using concrete "
                    "draft-specific and hero-based reasons.\n\n"
                    "Draft context:\n" + json.dumps(context, indent=2, default=str)
                )
                print(f"Prompt: {prompt}\n")

                with st.spinner("Coach is reacting to the draft..."):
                    try:
                        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
                        response_text = str(result["messages"][-1].text).strip()
                        print(f"AI Response: {response_text}\n")

                        for index, message in enumerate(result["messages"]):
                            print(
                                index,
                                type(message).__name__,
                                repr(str(message.text)),
                                getattr(message, "tool_calls", None),
                                getattr(message, "invalid_tool_calls", None),
                            )

                        # Parse with formatter to get a decision
                        final_decision = formatter.invoke(
                            "Extract the recommended hero name, position, and analysis "
                            f"from this answer:\n\n{response_text}"
                        )
                        print(f"Final Decision: {final_decision}\n")

                        # Grab the candidate's graph info for UI
                        recommendation = get_scored_candidate(
                            position_scores,
                            final_decision.recommended_hero,
                            final_decision.position,
                        )

                        analysis = final_decision.analysis
                    except Exception as error:
                        best_candidate = max(
                            shortlist,
                            key=lambda candidate: candidate["score"],
                        )
                        recommendation = get_scored_candidate(
                            position_scores,
                            best_candidate["hero"],
                            best_candidate["position"],
                        )
                        analysis = (
                            "The qualitative review failed, so this uses the highest "
                            f"graph score. Details: {error}"
                        )

                st.session_state.draft_analysis[analysis_key] = (
                    recommendation,
                    analysis,
                )

            # Extract
            recommended_position = recommendation["position"]
            best = recommendation["hero"]
            score = recommendation["score"]

            st.subheader(title)
            st.metric(metric_label, best, f"{score:.2f} score")
            if action == "Ban":
                st.caption(f"Strongest projected CPU pick for {recommendation['position']}.")

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
    data, _, _, draft_agent, formatter = load_game()
    graph = st.session_state.graph

    st.header("Draft")

    if st.session_state.draft_state is not None:
        render_active_draft(data, graph, draft_agent, formatter)
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
