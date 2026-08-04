"""Oxide tables: acid anhydrides, and the exceptions to the character rule.

An acid anhydride is stored as **oxide -> anion**, not oxide -> acid. The acid
formula is criss-cross of H+ with that anion (SO4-2 -> H2SO4), so no acid formula
is hardcoded anywhere and the acid table becomes a join rather than a second list
to keep in sync.

Each record carries the central element's oxidation state, which is what makes
the pairing checkable: the oxide formula must be the criss-cross of that state
with O(-2), and the anion's charge must equal `state - 2 * (oxygens in anion)`.
`chem.validate` asserts both for every row, so a typo cannot survive.

Basic oxides need no table -- any metal oxide is one, and its formula follows
from `CATION_CHARGES` by the same criss-cross. Only the acidic ones are
irregular enough to curate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OxideCharacter(Enum):
    BASIC = "basic"
    ACIDIC = "acidic"
    AMPHOTERIC = "amphoteric"  # out of scope for v1
    NEUTRAL = "neutral"  # reacts with neither water, acid nor base


@dataclass(frozen=True, slots=True)
class Anhydride:
    formula: str  # the oxide, e.g. "SO3"
    element: str  # central element, e.g. "S"
    state: int  # its oxidation state, e.g. 6
    anion: str  # anion of the acid it gives, e.g. "SO4-2"
    name: str
    hydrates: bool = True  # does oxide + water -> acid actually run?
    common: bool = True  # school-common; the generator should prefer these


# Curated acid anhydrides. An oxide is absent either because its acid's anion is
# not in `POLYATOMIC_IONS` yet, or because it is listed in `EXCLUDED_OXIDES`
# below with a reason.
ANHYDRIDES: dict[str, Anhydride] = {
    "CO2": Anhydride("CO2", "C", 4, "CO3-2", "carbon dioxide"),
    "SO2": Anhydride("SO2", "S", 4, "SO3-2", "sulfur dioxide"),
    "SO3": Anhydride("SO3", "S", 6, "SO4-2", "sulfur trioxide"),
    "N2O3": Anhydride("N2O3", "N", 3, "NO2-", "dinitrogen trioxide", common=False),
    "N2O5": Anhydride("N2O5", "N", 5, "NO3-", "dinitrogen pentoxide"),
    "P2O3": Anhydride("P2O3", "P", 3, "PO3-3", "diphosphorus trioxide", common=False),
    # P2O5 + cold water actually stops at HPO3; we model the hot-water product
    # H3PO4 and do not represent the difference.
    "P2O5": Anhydride("P2O5", "P", 5, "PO4-3", "diphosphorus pentoxide"),
    # The classic exception: SiO2 is insoluble and does not hydrate. H2SiO3 is
    # only reachable by acidifying a silicate.
    "SiO2": Anhydride("SiO2", "Si", 4, "SiO3-2", "silicon dioxide", hydrates=False),
    "B2O3": Anhydride("B2O3", "B", 3, "BO3-3", "diboron trioxide", common=False),
    "As2O5": Anhydride("As2O5", "As", 5, "AsO4-3", "diarsenic pentoxide", common=False),
    "As2O3": Anhydride("As2O3", "As", 3, "AsO3-3", "diarsenic trioxide", common=False),
    "SeO3": Anhydride("SeO3", "Se", 6, "SeO4-2", "selenium trioxide", common=False),
    "SeO2": Anhydride("SeO2", "Se", 4, "SeO3-2", "selenium dioxide", common=False),
    "Cl2O": Anhydride("Cl2O", "Cl", 1, "ClO-", "dichlorine monoxide", common=False),
    "Cl2O5": Anhydride("Cl2O5", "Cl", 5, "ClO3-", "dichlorine pentoxide", common=False),
    "Cl2O7": Anhydride("Cl2O7", "Cl", 7, "ClO4-", "dichlorine heptoxide", common=False),
    "I2O5": Anhydride("I2O5", "I", 5, "IO3-", "diiodine pentoxide", common=False),
    "CrO3": Anhydride("CrO3", "Cr", 6, "CrO4-2", "chromium(VI) oxide", common=False),
    "Mn2O7": Anhydride("Mn2O7", "Mn", 7, "MnO4-", "manganese(VII) oxide", common=False),
}

# Oxides that are anhydrides of nothing -- they react with neither water, acids
# nor bases. H2O is here because it is formally hydrogen's oxide: without this it
# would classify as acidic (H is a nonmetal) and hydrate into itself.
#
# Stored with names rather than as a bare set: these are the oxides whose name
# the roman-numeral rule would get wrong ("nitrogen(II) oxide" for NO), so the
# display layer needs them written out anyway.
NEUTRAL_OXIDE_NAMES: dict[str, str] = {
    "CO": "carbon monoxide",
    "NO": "nitrogen monoxide",
    "N2O": "dinitrogen monoxide",
    "H2O": "water",
}

NEUTRAL_OXIDES: frozenset[str] = frozenset(NEUTRAL_OXIDE_NAMES)

WATER: str = "H2O"

# State at room temperature for the oxides that are not solid. Everything absent
# is a solid, which is the right default once the gases are listed.
NON_SOLID_OXIDES: dict[str, str] = {
    "CO": "g",
    "CO2": "g",
    "NO": "g",
    "N2O": "g",
    "NO2": "g",
    "SO2": "g",
    "Cl2O": "g",
    "H2O": "l",
    "N2O3": "l",
    "SO3": "l",
    "Cl2O7": "l",
    "Mn2O7": "l",
}

# Deliberately kept out of `ANHYDRIDES`, with the reason. Worth having in the
# data so the exclusion is a decision on record rather than an omission.
EXCLUDED_OXIDES: dict[str, str] = {
    "NO2": "with water gives a mixture (HNO3 + NO), not one clean acid",
    "N2O4": "same as NO2, which it is in equilibrium with",
    "Cl2O3": "chlorous acid is real but this oxide effectively is not",
    "MnO2": "amphoteric and an oxidant; not a usable anhydride at school level",
}

# Oxides whose character the element-level rule gets wrong. Keyed by oxide
# formula, so one element can hold oxides of different character -- which is the
# whole point for Mn (MnO basic, MnO2 amphoteric, Mn2O7 acidic).
OXIDE_CHARACTER_OVERRIDES: dict[str, OxideCharacter] = {
    "MnO2": OxideCharacter.AMPHOTERIC,
}

# Metal oxides count as acidic from this oxidation state up (CrO3, Mn2O7).
ACIDIC_METAL_STATE: int = 6

ANION_TO_ANHYDRIDE: dict[str, str] = {a.anion: a.formula for a in ANHYDRIDES.values()}

ACIDIC_OXIDES: frozenset[str] = frozenset(ANHYDRIDES)
