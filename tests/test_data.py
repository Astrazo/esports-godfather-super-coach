"""Tests for the bundled reference data used by the draft workflow."""

from core.data import build_global_data


def test_core_data_loads_a_playable_hero_roster():
    data = build_global_data()

    assert len(data.hero_names) == 65
    assert data.hero_names == set(data.hero_tiers)
    assert all(
        1 <= tier <= 5
        for positions in data.hero_tiers.values()
        for tier in positions.values()
    )
