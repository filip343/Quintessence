"""Base table -- hydroxides, keyed by cation. The mirror of `chem.data.acids`.

Same trick as acids: no formula is written down. A base is a cation plus OH-, so
the formula is criss-cross of the two, computed at import into `BASE_FORMULAS`.

`strength` does two jobs. It gates displacement, and it decides which basic
oxides hydrate: only oxides of strong-base metals give a hydroxide with water
(Na2O and CaO do, CuO and Fe2O3 do not), which is otherwise an arbitrary-looking
exception list.
"""

from __future__ import annotations

from dataclasses import dataclass

from chem.data.strength import Strength
from chem.formulas import criss_cross, parse_charge, strip_charge


@dataclass(frozen=True, slots=True)
class Base:
    cation: str  # e.g. "Ca+2"
    name: str
    strength: Strength
    decomposes_to: tuple[str, ...] = ()
    common: bool = True

    @property
    def stable(self) -> bool:
        return not self.decomposes_to


_STRONG = Strength.STRONG
_WEAK = Strength.WEAK
_VERY_WEAK = Strength.VERY_WEAK

BASES: dict[str, Base] = {
    # --- alkali hydroxides: soluble and strong ---
    # LiOH is common because lithium's salts are: without it the neutralisation
    # and hydroxide-precipitation routes to every Li salt would not count.
    "Li+": Base("Li+", "lithium hydroxide", _STRONG),
    "Na+": Base("Na+", "sodium hydroxide", _STRONG),
    "K+": Base("K+", "potassium hydroxide", _STRONG),
    "Rb+": Base("Rb+", "rubidium hydroxide", _STRONG, common=False),
    "Cs+": Base("Cs+", "caesium hydroxide", _STRONG, common=False),
    # --- alkaline earth: strong, but Ca and Sr are only sparingly soluble ---
    "Ca+2": Base("Ca+2", "calcium hydroxide", _STRONG),
    "Sr+2": Base("Sr+2", "strontium hydroxide", _STRONG, common=False),
    "Ba+2": Base("Ba+2", "barium hydroxide", _STRONG),
    "Mg+2": Base("Mg+2", "magnesium hydroxide", _WEAK),
    "Be+2": Base("Be+2", "beryllium hydroxide", _WEAK, common=False),
    # --- ammonia solution: the one base that is not a metal hydroxide ---
    "NH4+": Base("NH4+", "ammonia solution", _WEAK, decomposes_to=("NH3", "H2O")),
    # --- insoluble weak bases: the precipitates of the double-displacement rule ---
    "Al+3": Base("Al+3", "aluminium hydroxide", _WEAK),
    "Ga+3": Base("Ga+3", "gallium hydroxide", _WEAK, common=False),
    "Zn+2": Base("Zn+2", "zinc hydroxide", _WEAK),
    "Cr+3": Base("Cr+3", "chromium(III) hydroxide", _WEAK, common=False),
    "Mn+2": Base("Mn+2", "manganese(II) hydroxide", _WEAK, common=False),
    "Fe+2": Base("Fe+2", "iron(II) hydroxide", _WEAK),
    "Fe+3": Base("Fe+3", "iron(III) hydroxide", _WEAK),
    "Co+2": Base("Co+2", "cobalt(II) hydroxide", _WEAK, common=False),
    "Ni+2": Base("Ni+2", "nickel(II) hydroxide", _WEAK, common=False),
    "Cu+2": Base("Cu+2", "copper(II) hydroxide", _WEAK),
    "Cd+2": Base("Cd+2", "cadmium hydroxide", _WEAK, common=False),
    "Sn+2": Base("Sn+2", "tin(II) hydroxide", _WEAK, common=False),
    "Pb+2": Base("Pb+2", "lead(II) hydroxide", _WEAK, common=False),
    "Bi+3": Base("Bi+3", "bismuth(III) hydroxide", _VERY_WEAK, common=False),
}

# Cations whose hydroxide deliberately has no record, with the reason. Each of
# these goes straight to the oxide instead, which is a fact worth keeping.
EXCLUDED_BASES: dict[str, str] = {
    "Ag+": "AgOH is not isolable -- silver gives Ag2O",
    "Hg+2": "Hg(OH)2 is not isolable -- mercury gives HgO",
    "Hg2+2": "same as mercury(II)",
    "Cu+": "CuOH disproportionates immediately",
    "H+": "water is hydrogen's hydroxide; handled as its own species",
    "H3O+": "same as H+",
    "Sn+4": "tin(IV) hydroxide is a hydrated oxide, not a usable base",
}

HYDROXIDE: str = "OH-"


def _formula_of(base: Base) -> str:
    return criss_cross(strip_charge(base.cation), parse_charge(base.cation), HYDROXIDE[:-1], -1)


BASE_FORMULAS: dict[str, str] = {cation: _formula_of(base) for cation, base in BASES.items()}

BASES_BY_FORMULA: dict[str, Base] = {
    formula: BASES[cation] for cation, formula in BASE_FORMULAS.items()
}

# Metals whose oxide hydrates to a hydroxide. Derived, not curated: it is exactly
# the strong bases. CuO + H2O does nothing because Cu(OH)2 is weak.
HYDRATABLE_OXIDE_CATIONS: frozenset[str] = frozenset(
    cation for cation, base in BASES.items() if base.strength is Strength.STRONG
)
