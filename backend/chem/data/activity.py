"""Activity series of metals (brief, table 3).

Gates three rule templates:

- `metal + acid -> salt + H2` -- only for metals above hydrogen.
- `metal + salt -> displacement` -- only if the free metal is above the salt's metal.
- `metal + water -> base + H2` -- needs `WATER_REACTIVITY`, not the series alone;
  the series puts Fe above H, but Fe gives no Fe(OH)2 in cold water.

Deliberately *not* electronegativity, which does not predict displacement.

Ordering follows the standard school series (most reactive first) rather than a
strict standard-potential sort; the two disagree only on pairs that are never
load-bearing in a puzzle (Ag/Hg, Co/Ni, Sn/Pb). Avoid adjacent-pair displacements
when generating puzzles for exactly that reason.
"""

from __future__ import annotations

from enum import Enum

# "H" is a marker, not a metal -- everything before it displaces hydrogen from acids.
ACTIVITY_SERIES: tuple[str, ...] = (
    "Li",
    "K",
    "Ba",
    "Sr",
    "Ca",
    "Na",
    "Mg",
    "Al",
    "Mn",
    "Zn",
    "Cr",
    "Fe",
    "Cd",
    "Co",
    "Ni",
    "Sn",
    "Pb",
    "H",
    "Cu",
    "Hg",
    "Ag",
    "Pt",
    "Au",
)

ACTIVITY_RANK: dict[str, int] = {symbol: i for i, symbol in enumerate(ACTIVITY_SERIES)}

HYDROGEN_RANK: int = ACTIVITY_RANK["H"]


# The nonmetal counterpart of the series: a halogen displaces any halogen below
# it from a halide salt. Most reactive first, which here is just the group order.
HALOGEN_ACTIVITY: tuple[str, ...] = ("F", "Cl", "Br", "I")

HALOGEN_RANK: dict[str, int] = {symbol: i for i, symbol in enumerate(HALOGEN_ACTIVITY)}

# Fluorine is in the order but never displaces anything in practice: it attacks
# the water before it reaches the salt. Kept in the ranking so Cl2 correctly
# fails to displace it, excluded as an attacker.
NON_DISPLACING_HALOGENS: frozenset[str] = frozenset({"F"})


class WaterReactivity(Enum):
    """How a metal behaves toward water."""

    COLD_WATER = "cold water"  # metal + H2O -> hydroxide + H2
    STEAM = "steam"  # metal + H2O -> oxide + H2, hot only
    NONE = "none"  # no reaction at school conditions


WATER_REACTIVITY: dict[str, WaterReactivity] = {
    "Li": WaterReactivity.COLD_WATER,
    "K": WaterReactivity.COLD_WATER,
    "Ba": WaterReactivity.COLD_WATER,
    "Sr": WaterReactivity.COLD_WATER,
    "Ca": WaterReactivity.COLD_WATER,
    "Na": WaterReactivity.COLD_WATER,
    # Mg reacts with cold water only very slowly; treated as a steam metal so
    # the generator never builds a puzzle step on the slow reaction.
    "Mg": WaterReactivity.STEAM,
    "Al": WaterReactivity.STEAM,  # oxide layer blocks it in practice
    "Mn": WaterReactivity.STEAM,
    "Zn": WaterReactivity.STEAM,
    "Cr": WaterReactivity.STEAM,
    "Fe": WaterReactivity.STEAM,
    "Cd": WaterReactivity.NONE,
    "Co": WaterReactivity.NONE,
    "Ni": WaterReactivity.NONE,
    "Sn": WaterReactivity.NONE,
    "Pb": WaterReactivity.NONE,
    "Cu": WaterReactivity.NONE,
    "Hg": WaterReactivity.NONE,
    "Ag": WaterReactivity.NONE,
    "Pt": WaterReactivity.NONE,
    "Au": WaterReactivity.NONE,
}
