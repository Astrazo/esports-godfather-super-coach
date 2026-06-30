from collections import defaultdict
from dataclasses import dataclass
from core.data import GlobalData
import warnings

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

def recommend_pick(
    G,
    team: str,
    lane: str,
    draft_state: DraftState,
    data: GlobalData,
) -> dict:

    # Determine enemy and friendly teams and unpack data
    friendly_picked = draft_state.t1_picked if team == "t1" else draft_state.t2_picked
    enemy_picked = draft_state.t2_picked if team == "t1" else draft_state.t1_picked
    friendly_available = draft_state.t1_available if team == "t1" else draft_state.t2_available
    enemy_available = draft_state.t2_available if team == "t1" else draft_state.t1_available


    # Score all candidates for the requested lane
    candidates = friendly_available[lane]
    results = {
        hero: _score_hero(G, team, hero, lane, friendly_available, friendly_picked, enemy_available, enemy_picked, data)
        for hero in candidates
    }
    
    # Get the best pick for this lane, Each value is: (score, explanation)
    best = max(results, key=lambda hero: results[hero][0])
    best_score, best_explanation = results[best]
    
    # Check if best pick scores higher in another lane
    other_results = {
        other_lane: _score_hero(G, team, best, other_lane, friendly_available, friendly_picked, enemy_available, enemy_picked, data)
        for other_lane, pool in friendly_available.items()
        if other_lane != lane and best in pool
    }

    better_position = None

    if other_results :
        best_alt_lane = max(
            other_results,
            key=lambda other_lane: other_results[other_lane][0],
        )
        alt_score, _ = other_results[best_alt_lane]

        if alt_score > best_score:
            better_position = {
                "lane": best_alt_lane,
                "score": alt_score,
            }

    candidates = []
    for hero, (score, explanation) in results.items():
        candidates.append(
            {
                "hero": hero,
                "score": score,
                "explanation": {
                    reason: sorted(values, key=str)
                    for reason, values in explanation.items()
                },
            }
        )

    candidates.sort(key=lambda candidate: candidate["score"], reverse=True)

    return {
        "recommended_hero": best,
        "requested_lane": lane,
        "score": best_score,
        "explanation": {
            reason: sorted(values, key=str)
            for reason, values in best_explanation.items()
        },
        "better_position": better_position,
        "candidates": candidates,
    }


def _score_hero(
        G, 
        team: str,
        candidate,
        position, # for tier and mastery scoring
        friendly_available: set, friendly_picked: set, 
        enemy_available: set, enemy_picked: set,
        data: GlobalData
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
    
    #1. Is there anything that counters this hero that can be picked against it?  
    # TODO for each hero that counteres this one, how good/strong is that counter?  Score reductions should be based on how strong the counter is
    # TODO for each hero that counter's this one, has been picked already?  Heroes that have been picked should carry a stronger importance
    countered_by = {v for _, v, d in G.out_edges(candidate, data=True) if d["type"] == "countered_by"}
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
    # TODO heros that we can counter with higher masteries should carry a higher weight over ones that aren't as strong
    counters = {v for _, v, d in G.out_edges(candidate, data=True) if d["type"] == "counter"}
    for hero in counters:
        if hero in enemy_picked:
            score += w_counter_picked
            explanation["counters"].add(hero)
        elif hero in enemy_available_distinct:
            score += w_counter_available
            explanation["counters_possible"].add(hero)

    # 4. Are there any issues with picking this hero with our current heroes?
    anti_synergy = {v for _, v, d in G.out_edges(candidate, data=True) if d["type"] == "anti_synergy"}
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
def pick_hero(
        G, hero: str, team: str, draft_state: DraftState
    ):

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
        position
        for position, mastery in G.nodes[hero][masteries_text].items()
        if mastery > 0
    }

    changed = True
    while changed:
        changed = False
        
        # See what positions are locked
        locked_positions = {
            next(iter(positions))
            for positions in t_picked.values()
            if len(positions) == 1
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
