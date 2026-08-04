"""Molecular hydrides -- the compound class the brief calls "hydride".

Most hydrides are already owned by another table, and that is the point of this
one being short:

- HCl, HBr, HI, HF and H2S are hydrides, but in water they behave as acids, so
  `chem.data.acids` holds them and `H2 + nonmetal` builds them there.
- NaH and CaH2 are ionic. H- is a curated anion, so they fall out of the salt
  index for free.

What is left is ammonia: a base that is not a hydroxide, and the only species in
the game no other table can hold. It gets its own class rather than being forced
into one that does not fit.

`conjugate_cation` is the whole record, really -- ammonia's chemistry at formula
level is "take up a proton and become NH4+", which is what makes the ammonium
salts reachable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Hydride:
    formula: str
    element: str  # the nonmetal bonded to hydrogen
    name: str
    conjugate_cation: str  # what it becomes on taking up a proton, e.g. "NH4+"
    common: bool = True


HYDRIDES: dict[str, Hydride] = {
    "NH3": Hydride("NH3", "N", "ammonia", "NH4+"),
}

AMMONIA: str = "NH3"
AMMONIUM: str = "NH4+"

# Hydrides deliberately absent, with the reason.
EXCLUDED_HYDRIDES: dict[str, str] = {
    "CH4": "methane; organic, and it does nothing at formula level",
    "PH3": "phosphine gives no stable phosphonium salts at school level",
    "SiH4": "silane is not school chemistry",
    "HCl": "a hydride, but it acts as an acid -- see chem.data.acids",
    "H2S": "same as HCl",
    "NaH": "ionic; H- is a curated anion, so the salt index already has it",
}

# element -> its molecular hydride, for the `H2 + nonmetal` route.
HYDRIDE_OF_ELEMENT: dict[str, str] = {
    record.element: formula for formula, record in HYDRIDES.items()
}

HYDRIDE_ELEMENTS: frozenset[str] = frozenset(HYDRIDE_OF_ELEMENT)
