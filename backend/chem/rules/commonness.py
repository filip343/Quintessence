"""Is this a species a school course actually uses?

Separate from correctness. Everything the engine can build is real chemistry;
this asks the narrower question of whether a student would recognise it, which
is what decides whether a route counts as findable rather than merely valid.

Composed the same way names are, and from the same joins:

- element   -- `COMMON_ELEMENTS`
- salt      -- both its ions common, so `NaHCO3` is and `Cu(HS)2` is not
- oxide     -- a common anhydride, or a metal oxide whose cation is common,
               which is what separates `CuO` from `Cu2O`
- acid, base, hydride -- their own `common` flag, already curated

The acid flag and the ion sets can disagree and that is correct rather than an
oversight: chromic acid is not a school reagent (`common=False`) while potassium
chromate is (`CrO4-2` is common). The flag describes the acid, the ion set
describes the salts.
"""

from __future__ import annotations

from chem.data.acids import ACIDS_BY_FORMULA
from chem.data.bases import BASES_BY_FORMULA
from chem.data.elements import COMMON_ELEMENTS, ELEMENT_OF_FORMULA
from chem.data.hydrides import HYDRIDES
from chem.data.ions import COMMON_ANIONS, COMMON_CATIONS
from chem.data.oxides import ANHYDRIDES, NEUTRAL_OXIDES, WATER
from chem.data.salts import OXIDE_IONS, SALT_IONS
from chem.formulas import ion_formula


def is_common(formula: str) -> bool:
    """True if a school course would put this species in front of a student."""
    if formula == WATER:
        return True

    element = ELEMENT_OF_FORMULA.get(formula)
    if element is not None:
        return element in COMMON_ELEMENTS

    ions = SALT_IONS.get(formula)
    if ions is not None:
        cation, anion = ions
        return cation in COMMON_CATIONS and anion in COMMON_ANIONS

    anhydride = ANHYDRIDES.get(formula)
    if anhydride is not None:
        return anhydride.common

    if formula in OXIDE_IONS:
        return _common_oxide(formula)

    for table in (ACIDS_BY_FORMULA, BASES_BY_FORMULA, HYDRIDES):
        record = table.get(formula)
        if record is not None:
            return record.common

    return False


def all_common(formulas: tuple[str, ...]) -> bool:
    return all(is_common(formula) for formula in formulas)


def _common_oxide(formula: str) -> bool:
    """A metal oxide is common when the cation it would give is.

    CuO and Cu2O are the case this exists for: both are real, one is school
    chemistry. Neutral oxides (CO, NO, N2O) are common in their own right --
    they are named in every course even though they make no cation.
    """
    if formula in NEUTRAL_OXIDES:
        return True
    element, state = OXIDE_IONS[formula]
    return ion_formula(element, state) in COMMON_CATIONS
