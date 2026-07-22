import warnings
from collections import defaultdict
from dataclasses import dataclass

from app.core.data import GlobalData


@dataclass
class DraftState:
    t1_available: dict[str, set[str]]
    t2_available: dict[str, set[str]]
    t1_picked: dict[str, set[str]]
    t2_picked: dict[str, set[str]]
    banned: set[str]
    draft_order: list[tuple[str, str]]
    current_step: int
    player_side: str


def build_draft_state(
    draft_order: list[tuple[str, str]],
    player_side: str,
):
    return DraftState(
        t1_available={},
        t1_picked={},
        t2_available={},
        t2_picked={},
        banned=set(),
        draft_order=draft_order.copy(),
        current_step=0,
        player_side=player_side,
    )


def score_all_positions(
    graph,
    team: str,
    draft_state: DraftState,
    data: GlobalData,
    positions,
) -> dict:
    """Score and rank the available heroes for every supplied position."""
    available = draft_state.t1_available if team == "t1" else draft_state.t2_available
    all_position_scores = {}

    for position in positions:
        if not available.get(position):
            continue

        # Score this position
        position_scores = score_position(
            graph,
            team,
            position,
            draft_state,
            data,
        )

        # Append this score to the position
        all_position_scores[position] = position_scores

    return all_position_scores


def score_position(
    G,
    team: str,
    lane: str,
    draft_state: DraftState,
    data: GlobalData,
) -> list[dict]:
    """Score heroes that are available and can play the requested position.

    Returns:
        Candidates ordered from highest to lowest score.
    """

    # Determine enemy and friendly teams and unpack data
    friendly_picked = draft_state.t1_picked if team == "t1" else draft_state.t2_picked
    enemy_picked = draft_state.t2_picked if team == "t1" else draft_state.t1_picked
    friendly_available = draft_state.t1_available if team == "t1" else draft_state.t2_available
    enemy_available = draft_state.t2_available if team == "t1" else draft_state.t1_available

    # Score all candidates for the requested lane
    candidates = friendly_available[lane]
    results = {
        hero: _score_hero(
            G,
            team,
            hero,
            lane,
            friendly_available,
            friendly_picked,
            enemy_available,
            enemy_picked,
            data,
        )
        for hero in candidates
    }

    candidates = []
    for hero, (score, explanation) in results.items():
        candidates.append(
            {
                "hero": hero,
                "score": score,
                "explanation": {
                    reason: sorted(values, key=str) for reason, values in explanation.items()
                },
            }
        )

    candidates.sort(key=lambda candidate: candidate["score"], reverse=True)
    return candidates


def build_candidate_shortlist(
    position_scores,
    candidates_per_position: int = 3,
) -> list[dict]:
    """Flatten the strongest candidates from each position for agent review."""
    shortlist = []

    for position, candidates in position_scores.items():
        for candidate in candidates[:candidates_per_position]:
            shortlist.append(
                {
                    "hero": candidate["hero"],
                    "position": position,
                    "score": candidate["score"],
                    "reasons": candidate["explanation"],
                }
            )
    return shortlist


def get_scored_candidate(
    position_scores,
    selected_hero: str,
    selected_position: str,
    candidates_per_position: int = 3,
) -> dict:
    """Map an agent selection back to its authoritative graph result."""
    candidates = position_scores[selected_position]

    for candidate in candidates[:candidates_per_position]:
        if candidate["hero"] != selected_hero:
            continue

        return {
            "position": selected_position,
            **candidate,
            "candidates": candidates,
        }

    raise ValueError(
        f"Coach selected {selected_hero} for {selected_position}, "
        "which was not in the supplied shortlist."
    )


def _score_hero(
    G,
    team: str,
    candidate,
    position,  # for tier and mastery scoring
    friendly_available: set,
    friendly_picked: set,
    enemy_available: set,
    enemy_picked: set,
    data: GlobalData,
):

    # Team Comp Weights
    w_countered_picked = 3
    w_countered_available = 1.5

    w_synergy_picked = 1
    w_synergy_available = 0.5

    w_counter_picked = 2
    w_counter_available = 1

    w_a_synergy_picked = 0.5
    w_a_synergy_available = 0.25

    # Mastery weight
    w_mastery = 1

    # Tier Weight
    w_tier = 2

    # Init score
    score = 0
    explanation = defaultdict(set)

    friendly_available_distinct = set().union(*friendly_available.values())
    enemy_available_distinct = set().union(*enemy_available.values())

    # 1. Is there anything that counters this hero that can be picked against it?
    # TODO: Weight score reductions by the strength of each available counter.
    # TODO: Give already-picked counters more importance than available counters.
    countered_by = {
        v for _, v, d in G.out_edges(candidate, data=True) if d["type"] == "countered_by"
    }
    for hero in countered_by:
        if hero in enemy_picked:
            score -= w_countered_picked
            explanation["countered_by"].add(hero)
        elif hero in enemy_available_distinct:
            score -= w_countered_available
            explanation["countered_by_possible"].add(hero)

    # 2. What synergies are available for this hero
    synergies = {v for _, v, d in G.out_edges(candidate, data=True) if d["type"] == "synergy"}
    for hero in synergies:
        if hero in friendly_picked:
            score += w_synergy_picked
            explanation["synergy"].add(hero)
        elif hero in friendly_available_distinct:
            score += w_synergy_available
            explanation["synergy_possible"].add(hero)

    # 3. Are there opportunities to counter enemy heroes?
    # TODO: Give counters with higher player mastery more weight.
    counters = {v for _, v, d in G.out_edges(candidate, data=True) if d["type"] == "counter"}
    for hero in counters:
        if hero in enemy_picked:
            score += w_counter_picked
            explanation["counters"].add(hero)
        elif hero in enemy_available_distinct:
            score += w_counter_available
            explanation["counters_possible"].add(hero)

    # 4. Are there any issues with picking this hero with our current heroes?
    anti_synergy = {
        v for _, v, d in G.out_edges(candidate, data=True) if d["type"] == "anti_synergy"
    }
    for hero in anti_synergy:
        if hero in friendly_picked:
            score -= w_a_synergy_picked
            explanation["a_synergy"].add(hero)
        elif hero in friendly_available_distinct:
            score -= w_a_synergy_available
            explanation["a_synergy_possible"].add(hero)

    # 5 - Add weight for tier
    score += G.nodes[candidate]["tiers"][position] * w_tier
    explanation["position_tier"].add(data.tier_map_rev[G.nodes[candidate]["tiers"][position]])

    # 6 - Add weight for mastery
    masteries_text = "t1_masteries" if team == "t1" else "t2_masteries"
    score += G.nodes[candidate][masteries_text][position] * w_mastery
    explanation["position_mastery"].add(G.nodes[candidate][masteries_text][position])

    return score, explanation


# Hero set manipulation functions
def pick_hero(G, hero: str, team: str, draft_state: DraftState):

    # Unpack data
    t1_available = draft_state.t1_available
    t2_available = draft_state.t2_available
    t_picked = draft_state.t1_picked if team == "t1" else draft_state.t2_picked

    # This hero is no longer available
    for pool in t1_available.values():
        pool.discard(hero)
    for pool in t2_available.values():
        pool.discard(hero)

    # Set positions this new hero could play
    masteries_text = "t1_masteries" if team == "t1" else "t2_masteries"
    t_picked[hero] = {
        position for position, mastery in G.nodes[hero][masteries_text].items() if mastery > 0
    }

    changed = True
    while changed:
        changed = False

        # See what positions are locked
        locked_positions = {
            next(iter(positions)) for positions in t_picked.values() if len(positions) == 1
        }

        for possible_positions in t_picked.values():
            if len(possible_positions) == 1:
                continue

            previous_positions = possible_positions.copy()
            possible_positions.difference_update(locked_positions)

            if possible_positions != previous_positions:
                changed = True

            if not possible_positions:
                warnings.warn(
                    f"It seems {hero} has no valid remaining positions based on the "
                    "availabilities provided. This may be okay if you did not provide "
                    "all of T2's availabilities.",
                    UserWarning,
                    stacklevel=2,
                )


def ban_hero(hero: str, draft_state: DraftState):

    t1_available = draft_state.t1_available
    t2_available = draft_state.t2_available

    for pool in t1_available.values():
        pool.discard(hero)
    for pool in t2_available.values():
        pool.discard(hero)
    draft_state.banned.add(hero)


def see_current_draft(team: str, draft_state: DraftState):
    return draft_state.t1_picked if team == "t1" else draft_state.t2_picked


def see_current_banned(draft_state: DraftState):
    return draft_state.banned


# If mastery for hero + position is 0, then that player cannot play that hero at all
def build_position_availability(masteries) -> dict[str, set[str]]:
    available = defaultdict(set)

    for hero, position_masteries in masteries.items():
        for position, mastery in position_masteries.items():
            if mastery > 0:
                available[position].add(hero)

    return available
