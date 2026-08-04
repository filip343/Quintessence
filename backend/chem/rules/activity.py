"""Displacement gates read off the activity series."""

from __future__ import annotations

from chem.data.activity import ACTIVITY_RANK, HYDROGEN_RANK, WATER_REACTIVITY, WaterReactivity


def is_more_active(metal: str, other: str) -> bool:
    """True if `metal` sits above `other` in the series, so it displaces it."""
    return ACTIVITY_RANK[metal] < ACTIVITY_RANK[other]


def displaces_hydrogen_from_acid(metal: str) -> bool:
    """True if `metal + acid -> salt + H2` is allowed."""
    return ACTIVITY_RANK[metal] < HYDROGEN_RANK


def water_reactivity(metal: str) -> WaterReactivity:
    return WATER_REACTIVITY[metal]


def reacts_with_cold_water(metal: str) -> bool:
    """True if `metal + H2O -> base + H2` is allowed as written."""
    return WATER_REACTIVITY[metal] is WaterReactivity.COLD_WATER


def in_series(symbol: str) -> bool:
    return symbol in ACTIVITY_RANK
