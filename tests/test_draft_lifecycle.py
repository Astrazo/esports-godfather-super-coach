"""Smoke tests for the public draft workflow."""


def _hero_for_position(game, position, excluded=()):
    """Return a hero that can fill the requested position."""
    return next(
        hero
        for hero in game.data.hero_names
        if hero not in excluded and position in game.graph.nodes[hero]["tiers"]
    )


def test_draft_recommendation_tracks_picks_and_bans(game):
    top_hero = _hero_for_position(game, "Top")
    mid_hero = _hero_for_position(game, "Mid", excluded={top_hero})
    enemy_hero = _hero_for_position(game, "Jungler", excluded={top_hero, mid_hero})

    game.set_masteries("t1", "Top", {top_hero: 7})
    game.set_masteries("t1", "Mid", {mid_hero: 5})
    game.set_masteries("t2", "Jungler", {enemy_hero: 6})
    game.set_draft_order(
        [("blue", "Pick"), ("red", "Ban"), ("blue", "Pick")]
    )

    game.start_draft("blue")
    game.refresh_recommendation()

    assert game.draft_recommendation["hero"] == top_hero
    assert game.draft_recommendation["position"] == "Top"
    assert game.draft_recommendation["source"] == "graph"

    game.apply_draft_action(top_hero, "Top")
    assert game.draft_state.t1_picked == {top_hero: {"Top"}}
    assert game.draft_state.current_step == 1
    assert game.draft_recommendation is None

    game.apply_draft_action(enemy_hero)
    assert enemy_hero in game.draft_state.banned
    assert game.draft_state.current_step == 2
    assert game.draft_recommendation["hero"] == mid_hero
    assert game.draft_recommendation["position"] == "Mid"


def test_ending_a_draft_clears_temporary_enemy_data(game):
    top_hero = _hero_for_position(game, "Top")
    enemy_hero = _hero_for_position(game, "Jungler", excluded={top_hero})

    game.set_masteries("t1", "Top", {top_hero: 7})
    game.set_masteries("t2", "Jungler", {enemy_hero: 6})
    game.set_draft_order([("blue", "Pick")])
    game.start_draft("blue")

    game.end_draft()

    assert game.draft_state is None
    assert game.draft_recommendation is None
    assert game.t2_masteries[enemy_hero]["Jungler"] == 0


def test_invalid_draft_order_is_rejected(game):
    import pytest

    with pytest.raises(ValueError, match="blue/red"):
        game.set_draft_order([("green", "Pick")])
