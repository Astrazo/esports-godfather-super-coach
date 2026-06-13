from collections import defaultdict
from dataclasses import dataclass

@dataclass
class DraftState:
    t1_available: dict[str, set[str]]
    t2_available: dict[str, set[str]]
    t1_picked: dict[str, set[str]]
    t2_picked: dict[str, set[str]]
    banned: set[str]

def build_draft_state():
    return DraftState(
        t1_available=set(),
        t1_picked=set(),
        t2_available=set(),
        t2_picked=set(),
        banned=set()
    )

def recommend_pick(G, lane, t1_available, t1_picked, t2_available, t2_picked):
    # Score all candidates for the requested lane
    candidates = t1_available[lane]
    results = {
        hero: _score_hero(G, hero, lane, t1_available, t1_picked, t2_available, t2_picked)
        for hero in candidates
    }
    
    # Get the best pick for this lane, Each value is: (score, explanation)
    best = max(results, key=lambda hero: results[hero][0])
    best_score, best_explanation = results[best]
    
    # Check if best pick scores higher in another lane
    other_results = {
        other_lane: _score_hero(G, best, other_lane, t1_available, t1_picked, t2_available, t2_picked)
        for other_lane, pool in t1_available.items()
        if other_lane != lane and best in pool
    }

    flag = None

    if other_results :
        best_alt_lane = max(
            other_results,
            key=lambda other_lane: other_results[other_lane][0],
        )
        alt_score, _ = other_results[best_alt_lane]

        if alt_score > best_score:
            flag = (
                f"If you can, consider {best} for {best_alt_lane} instead "
                f"(scores {alt_score:.2f} in {best_alt_lane} vs {best_score:.2f} in {lane})"
            )
    
    return best, best_score, best_explanation, flag, results


def _score_hero(
        G, 
        candidate,
        position, # for tier and mastery scoring
        t1_available: set, t1_picked: set, 
        t2_available: set, t2_picked: set
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

    t1_available_distinct = set().union(*t1_available.values())
    t2_available_distinct = set().union(*t2_available.values())
    
    #1. Is there anything that counters this hero that can be picked against it?  
    # TODO for each hero that counteres this one, how good/strong is that counter?  Score reductions should be based on how strong the counter is
    # TODO for each hero that counter's this one, has been picked already?  Heroes that have been picked should carry a stronger importance
    countered_by = {v for _, v, d in G.out_edges(candidate, data=True) if d["type"] == "countered_by"}
    for hero in countered_by:
        if hero in t2_picked:
            score -= w_countered_picked
            explanation["countered_by"].add(hero)
        elif hero in t2_available_distinct:
            score -= w_countered_available
            explanation["countered_by_possible"].add(hero)

    # 2. What synergies are available for this hero
    synergies = {v for _, v, d in G.out_edges(candidate, data=True) if d["type"] == "synergy"}
    for hero in synergies:
        if hero in t1_picked:
            score += w_synergy_picked
            explanation["synergy"].add(hero)
        elif hero in t1_available_distinct:
            score += w_synergy_available
            explanation["synergy_possible"].add(hero)

    # 3. Are there opportunities to counter enemy heroes?
    # TODO heros that we can counter with higher masteries should carry a higher weight over ones that aren't as strong
    counters = {v for _, v, d in G.out_edges(candidate, data=True) if d["type"] == "counter"}
    for hero in counters:
        if hero in t2_picked:
            score += w_counter_picked
            explanation["counters"].add(hero)
        elif hero in t2_available_distinct:
            score += w_counter_available
            explanation["counters_possible"].add(hero)

    # 4. Are there any issues with picking this hero with our current heroes?
    anti_synergy = {v for _, v, d in G.out_edges(candidate, data=True) if d["type"] == "anti_synergy"}
    for hero in anti_synergy:
        if hero in t1_picked:
            score -= w_a_synergy_picked
            explanation["a_synergy"].add(hero)
        elif hero in t1_available_distinct:
            score -= w_a_synergy_available
            explanation["a_synergy_possible"].add(hero)

    # 5 - Add weight for tier
    score += G.nodes[candidate]["tiers"][position] * w_tier
    explanation["position_tier"].add(tier_map_rev[G.nodes[candidate]["tiers"][position]])

    # 6 - Add weight for mastery
    score += G.nodes[candidate]["masteries"][position] * w_mastery
    explanation["position_mastery"].add(G.nodes[candidate]["masteries"][position])

    return score, explanation


# Hero set manipulation functions
def pick_hero(
        G, t_picked: dict[str, set[str]], hero: str,
        t1_available: dict[str, set[str]],
        t2_available: dict[str, set[str]]
    ):

    # This hero is no longer available
    for pool in t1_available.values():
        pool.discard(hero)
    for pool in t2_available.values():
        pool.discard(hero)
    
    # Set positions this new hero could play
    t_picked[hero] = {
        position
        for position, mastery in G.nodes[hero]["masteries"].items()
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
                raise ValueError(f"{hero} has no valid remaining positions")

    return t_picked

def ban_hero(t_banned, hero, t1_available, t2_available):
    for pool in t1_available.values():
        pool.discard(hero)
    for pool in t2_available.values():
        pool.discard(hero)
    t_banned.add(hero)
    return t_banned

def see_current_draft(t_picked: set):
    return t_picked

def see_current_banned(t_banned: set):
    return t_banned


# If mastery for hero + position is 0, then that player cannot play that hero at all
def build_position_availability(masteries):
    available = defaultdict(set)

    for hero, position_masteries in masteries.items():
        for position, mastery in position_masteries.items():
            if mastery > 0:
                available[position].add(hero)

    return available