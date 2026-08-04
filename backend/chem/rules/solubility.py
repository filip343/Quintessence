"""Solubility lookup -- walks the anion-major rules in `chem.data.solubility`.

Resolution order:

1. `SOLUBILITY_OVERRIDES` -- specific pairs that no rule captures
2. the anion rule's per-cation exception
3. `ALWAYS_SOLUBLE_CATIONS` -- group 1 and ammonium salts dissolve
4. the anion rule's default
5. `UNKNOWN` if either ion is outside the curated set
"""

from __future__ import annotations

from chem.data.ions import CATION_FORMULAS
from chem.data.solubility import (
    ALWAYS_SOLUBLE_CATIONS,
    ANION_RULES,
    SOLUBILITY_OVERRIDES,
    Solubility,
)


def solubility(cation: str, anion: str) -> Solubility:
    """Look up a salt's solubility from its ion formulas, e.g. ("Ba+2", "SO4-2")."""
    override = SOLUBILITY_OVERRIDES.get((cation, anion))
    if override is not None:
        return override

    rule = ANION_RULES.get(anion)
    if rule is None:
        return Solubility.UNKNOWN

    exception = rule.exceptions.get(cation)
    if exception is not None:
        return exception

    if cation in ALWAYS_SOLUBLE_CATIONS:
        return Solubility.SOLUBLE

    if cation not in CATION_FORMULAS:
        return Solubility.UNKNOWN

    return rule.default


def precipitates(cation: str, anion: str) -> bool:
    """True if this salt comes out of solution (slightly-soluble included)."""
    return solubility(cation, anion).precipitates


def certainly_precipitates(cation: str, anion: str) -> bool:
    """True only for unambiguous precipitates -- safe for a par-path step."""
    return solubility(cation, anion).certainly_precipitates
