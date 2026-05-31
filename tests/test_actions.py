from pokemon_splendor.engine.actions import (
    TAKE_DIFF_COMBOS, TOTAL_ACTIONS, BOARD_SLOT_TIERS,
    TAKE_DIFF_START, TAKE_SAME_START, CATCH_BOARD_START,
    CATCH_RESERVED_START, RESERVE_MASTER_START, RESERVE_NO_MASTER_START,
    DISCARD_START, EVOLVE_START, EVOLVE_PASS,
)
from pokemon_splendor.models import PokeballType, Tier


def test_take_diff_combo_count():
    assert len(TAKE_DIFF_COMBOS) == 25


def test_take_diff_no_master():
    for combo in TAKE_DIFF_COMBOS:
        assert PokeballType.Master not in combo


def test_take_diff_all_unique_types_per_combo():
    for combo in TAKE_DIFF_COMBOS:
        assert len(set(combo)) == len(combo)


def test_board_slot_count():
    assert len(BOARD_SLOT_TIERS) == 14


def test_epic_legendary_slots():
    assert BOARD_SLOT_TIERS[12] == Tier.Epic
    assert BOARD_SLOT_TIERS[13] == Tier.Legendary


def test_total_actions():
    assert TOTAL_ACTIONS == 108


def test_action_ranges_non_overlapping():
    ranges = [
        range(TAKE_DIFF_START, TAKE_SAME_START),
        range(TAKE_SAME_START, CATCH_BOARD_START),
        range(CATCH_BOARD_START, CATCH_RESERVED_START),
        range(CATCH_RESERVED_START, RESERVE_MASTER_START),
        range(RESERVE_MASTER_START, RESERVE_NO_MASTER_START),
        range(RESERVE_NO_MASTER_START, DISCARD_START),
        range(DISCARD_START, EVOLVE_START),
        range(EVOLVE_START, EVOLVE_PASS),
    ]
    all_indices = [i for r in ranges for i in r] + [EVOLVE_PASS]
    assert len(all_indices) == len(set(all_indices)) == TOTAL_ACTIONS
