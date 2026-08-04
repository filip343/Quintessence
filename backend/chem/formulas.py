"""Formula-string manipulation. Pure syntax -- no chemistry data is imported here.

This is the bottom layer: `chem.data` may use it, `chem.rules` may use it, and it
depends on nothing. Notation is ChemPy's -- charge as a trailing sign with a
magnitude only when it exceeds one: `Na+`, `Cl-`, `Ca+2`, `SO4-2`.
"""

from __future__ import annotations

import re
from math import gcd

_CHARGE_RE = re.compile(r"^(?P<core>.+?)(?P<sign>[+-])(?P<magnitude>\d*)$")
_OXYGEN_COUNT_RE = re.compile(r"O(\d*)")


def ion_formula(symbol: str, charge: int) -> str:
    """Build an ion formula: ("Ca", 2) -> "Ca+2", ("Cl", -1) -> "Cl-"."""
    if charge == 0:
        raise ValueError("an ion cannot have charge 0")
    sign = "+" if charge > 0 else "-"
    magnitude = abs(charge)
    return f"{symbol}{sign}" if magnitude == 1 else f"{symbol}{sign}{magnitude}"


def parse_charge(formula: str) -> int:
    """Read the charge off an ion formula. Returns 0 for a neutral formula."""
    match = _CHARGE_RE.match(formula)
    if match is None:
        return 0
    magnitude = int(match["magnitude"]) if match["magnitude"] else 1
    return magnitude if match["sign"] == "+" else -magnitude


def strip_charge(formula: str) -> str:
    """Drop the charge suffix: "SO4-2" -> "SO4"."""
    match = _CHARGE_RE.match(formula)
    return formula if match is None else match["core"]


def oxygen_count(formula: str) -> int:
    """Count oxygens in a simple formula: "SO4-2" -> 4, "ClO-" -> 1."""
    match = _OXYGEN_COUNT_RE.search(formula)
    if match is None:
        return 0
    return int(match[1]) if match[1] else 1


def criss_cross(
    positive: str, positive_charge: int, negative: str, negative_charge: int
) -> str:
    """Combine two ions into a neutral formula by criss-crossing their charges.

    Group formulas of more than one atom get parenthesised when they repeat:
    ("Ca", 2, "OH", -1) -> "Ca(OH)2". Charges must be given unsigned-magnitude
    aware -- pass the real signed values.
    """
    if positive_charge <= 0 or negative_charge >= 0:
        raise ValueError("expected a positive and a negative charge")
    divisor = gcd(positive_charge, -negative_charge)
    positive_count = -negative_charge // divisor
    negative_count = positive_charge // divisor
    return _group(positive, positive_count) + _group(negative, negative_count)


def oxide_formula(symbol: str, state: int) -> str:
    """Criss-cross an element at `state` with O(-2): ("N", 5) -> "N2O5"."""
    if state <= 0:
        raise ValueError(f"an oxide needs a positive oxidation state, got {state}")
    return criss_cross(symbol, state, "O", -2)


def _group(formula: str, count: int) -> str:
    if count == 1:
        return formula
    needs_parens = len(re.findall(r"[A-Z]", formula)) > 1
    return f"({formula}){count}" if needs_parens else f"{formula}{count}"
