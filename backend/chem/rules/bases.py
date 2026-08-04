"""Routes to a base, and the lookups they need.

Two routes exist at formula level:

1. `basic oxide + water -> base`   `hydrate_oxide()`
       Only for oxides of strong-base metals. Na2O and CaO slake; CuO and Fe2O3
       sit there. `HYDRATABLE_OXIDE_CATIONS` derives that from base strength
       rather than listing exceptions.
2. `metal + water -> base + H2`    `metal_with_water()`
       Gated on `WATER_REACTIVITY`, not on the activity series: iron is above
       hydrogen but gives no Fe(OH)2 in cold water.

The third way a base appears -- precipitating out of `salt + base` -- is a salt
template, and lives in `chem.rules.salts`.
"""

from __future__ import annotations

from chem.data.bases import (
    BASE_FORMULAS,
    BASES,
    BASES_BY_FORMULA,
    HYDRATABLE_OXIDE_CATIONS,
    Base,
)
from chem.data.elements import ELEMENTAL_FORMULA
from chem.data.oxides import WATER
from chem.data.salts import OXIDE_IONS
from chem.data.strength import Strength
from chem.formulas import ion_formula
from chem.reaction import Reaction
from chem.rules.activity import reacts_with_cold_water
from chem.rules.oxides import oxide_character
from chem.data.oxides import OxideCharacter

OXIDE_HYDRATION = "basic oxide + water -> base"
METAL_WITH_WATER = "metal + water -> base + hydrogen"

HYDROGEN: str = ELEMENTAL_FORMULA["H"]


# --------------------------------------------------------------------------
# Lookups
# --------------------------------------------------------------------------


def base_of(cation: str) -> Base | None:
    return BASES.get(cation)


def base_formula(cation: str) -> str | None:
    return BASE_FORMULAS.get(cation)


def as_base(formula: str) -> Base | None:
    return BASES_BY_FORMULA.get(formula)


def is_base(formula: str) -> bool:
    return formula in BASES_BY_FORMULA


def base_strength(formula: str) -> Strength | None:
    base = BASES_BY_FORMULA.get(formula)
    return None if base is None else base.strength


def is_stronger_base(formula: str, other: str) -> bool:
    first, second = BASES_BY_FORMULA.get(formula), BASES_BY_FORMULA.get(other)
    if first is None or second is None:
        return False
    return first.strength.rank > second.strength.rank


def base_decomposition(formula: str) -> tuple[str, ...]:
    base = BASES_BY_FORMULA.get(formula)
    return () if base is None else base.decomposes_to


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


def hydrate_oxide(oxide: str) -> Reaction | None:
    """Route 1 -- `basic oxide + water -> base`, for strong-base metals only."""
    resolved = OXIDE_IONS.get(oxide)
    if resolved is None:
        return None
    element, state = resolved
    if oxide_character(element, state) is not OxideCharacter.BASIC:
        return None

    cation = ion_formula(element, state)
    if cation not in HYDRATABLE_OXIDE_CATIONS:
        return None
    formula = BASE_FORMULAS.get(cation)
    if formula is None:
        return None
    return Reaction(
        reactants=(oxide, WATER),
        products=(formula,),
        template=OXIDE_HYDRATION,
        note=_stability_note(formula),
    )


def metal_with_water(metal: str) -> Reaction | None:
    """Route 2 -- `metal + water -> base + H2`, cold-water metals only."""
    if metal not in ELEMENTAL_FORMULA or not _reacts_with_water(metal):
        return None
    cation = ion_formula(metal, _base_charge(metal))
    formula = BASE_FORMULAS.get(cation)
    if formula is None:
        return None
    return Reaction(
        reactants=(ELEMENTAL_FORMULA[metal], WATER),
        products=(formula, HYDROGEN),
        template=METAL_WITH_WATER,
    )


def routes_to_base(formula: str) -> list[str]:
    """Human-readable ways to make this base."""
    base = BASES_BY_FORMULA.get(formula)
    if base is None:
        return []

    routes: list[str] = []
    if base.cation in HYDRATABLE_OXIDE_CATIONS:
        from chem.rules.salts import oxide_of_cation

        oxide = oxide_of_cation(base.cation)
        if oxide is not None:
            routes.append(f"{oxide} + {WATER}  ({OXIDE_HYDRATION})")

    element = _element_of_cation(base.cation)
    if element is not None and _reacts_with_water(element):
        routes.append(f"{ELEMENTAL_FORMULA[element]} + {WATER}  ({METAL_WITH_WATER})")

    if base.strength is not Strength.STRONG:
        routes.append(
            f"a soluble salt of {base.cation} + a strong base"
            "  (double displacement -- this hydroxide precipitates)"
        )
    return routes


def _reacts_with_water(element: str) -> bool:
    try:
        return reacts_with_cold_water(element)
    except KeyError:
        return False


def _base_charge(metal: str) -> int:
    from chem.rules.ions import default_cation_charge

    return default_cation_charge(metal)


def _element_of_cation(cation: str) -> str | None:
    from chem.formulas import strip_charge

    element = strip_charge(cation)
    return element if element in ELEMENTAL_FORMULA else None


def _stability_note(formula: str) -> str:
    products = base_decomposition(formula)
    return "" if not products else f"unstable -- decomposes to {' + '.join(products)}"
