"""Every route to an acid, and the lookups the routes need.

Six routes exist at school level. Which are implemented here, and why:

1. `acidic oxide + water -> acid`      `hydrate()`        -- implemented
2. `H2 + nonmetal -> hydracid`         `hydrogenate()`    -- implemented
3. `salt + stronger acid -> acid + salt`  `displace_from_salt()`  -- implemented;
       the salt is taken apart through the index in `chem.data.salts`.
4. `salt + acid -> insoluble acid`     folded into `displace_from_salt()`, which
       accepts an insoluble product as its own driving force (silicate -> H2SiO3)
       even when the strength comparison alone would not allow it.
5. `salt + involatile acid, heated`    NOT implemented. NaCl + conc. H2SO4 -> HCl
       is real, but depends on concentration and heat, which the brief puts out
       of scope. It is the only route to HCl that does not start from Cl2.
6. `nonmetal + water -> two acids`     NOT implemented. Cl2 + H2O -> HCl + HClO is
       disproportionation: two products, no ion recombination, needs its own
       hardcoded template if it is ever wanted.

Products are unbalanced formulas -- see `chem.reaction`.
"""

from __future__ import annotations

from chem.data.acids import (
    ACID_FORMULAS,
    ACIDS,
    ACIDS_BY_FORMULA,
    HYDRACID_ELEMENTS,
    PARENT_ANION,
    PROTON_COUNT,
    Acid,
)
from chem.data.strength import Strength
from chem.data.elements import ELEMENTAL_FORMULA
from chem.data.oxides import ANHYDRIDES, ANION_TO_ANHYDRIDE, WATER
from chem.data.salts import SALT_IONS
from chem.formulas import ion_formula
from chem.reaction import Reaction
from chem.rules.ions import default_anion_charge
from chem.rules.salts import salt_formula

HYDRATION = "acidic oxide + water -> acid"
HYDROGENATION = "hydrogen + nonmetal -> hydracid"
DISPLACEMENT = "salt + stronger acid -> weaker acid + salt"


# --------------------------------------------------------------------------
# Lookups
# --------------------------------------------------------------------------


def acid_of(anion: str) -> Acid | None:
    """The acid whose conjugate base is `anion`."""
    return ACIDS.get(anion)


def acid_formula(anion: str) -> str | None:
    """Formula of that acid, criss-crossed from the anion at import time."""
    return ACID_FORMULAS.get(anion)


def as_acid(formula: str) -> Acid | None:
    """The acid record for a species formula, or None if it is not an acid."""
    return ACIDS_BY_FORMULA.get(formula)


def is_acid(formula: str) -> bool:
    return formula in ACIDS_BY_FORMULA


def strength_of(formula: str) -> Strength | None:
    acid = ACIDS_BY_FORMULA.get(formula)
    return None if acid is None else acid.strength


def is_stronger(formula: str, other: str) -> bool:
    """True if the first acid can drive the second out of its salt."""
    first, second = ACIDS_BY_FORMULA.get(formula), ACIDS_BY_FORMULA.get(other)
    if first is None or second is None:
        return False
    return first.strength.rank > second.strength.rank


def proton_count(anion: str) -> int | None:
    """Acidic hydrogens, i.e. the anion's charge magnitude."""
    return PROTON_COUNT.get(anion)


def decomposition_of(formula: str) -> tuple[str, ...]:
    """What this acid falls apart into. Empty if it is stable."""
    acid = ACIDS_BY_FORMULA.get(formula)
    return () if acid is None else acid.decomposes_to


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


def hydrate(oxide: str) -> Reaction | None:
    """Route 1 -- `acidic oxide + water -> acid`.

    Returns None for an oxide that is not an anhydride, and for SiO2, which is
    an anhydride that does not hydrate.
    """
    anhydride = ANHYDRIDES.get(oxide)
    if anhydride is None or not anhydride.hydrates:
        return None
    formula = ACID_FORMULAS.get(anhydride.anion)
    if formula is None:
        return None
    return Reaction(
        reactants=(oxide, WATER),
        products=(formula,),
        template=HYDRATION,
        note=_stability_note(formula),
    )


def hydrogenate(symbol: str) -> Reaction | None:
    """Route 2 -- `H2 + nonmetal -> hydracid`, for the halogens and sulfur."""
    if symbol not in HYDRACID_ELEMENTS:
        return None
    anion = ion_formula(symbol, default_anion_charge(symbol))
    formula = ACID_FORMULAS.get(anion)
    if formula is None:
        return None
    return Reaction(
        reactants=(ELEMENTAL_FORMULA["H"], ELEMENTAL_FORMULA[symbol]),
        products=(formula,),
        template=HYDROGENATION,
    )


def displace_from_salt(salt: str, acid: str) -> Reaction | None:
    """Routes 3 and 4 -- a stronger acid drives a weaker one out of its salt.

    Allowed when the freed acid is weaker than the attacking one (route 3), or
    when the freed acid is itself insoluble and simply drops out (route 4,
    silicate -> H2SiO3).
    """
    ions = SALT_IONS.get(salt)
    attacking = ACIDS_BY_FORMULA.get(acid)
    if ions is None or attacking is None:
        return None
    salt_cation, salt_anion = ions
    # an acid salt behaves as a salt of its parent acid: NaHCO3 + HCl frees the
    # same H2CO3 that Na2CO3 + HCl does
    freed_anion = PARENT_ANION.get(salt_anion, salt_anion)
    if attacking.anion == freed_anion:
        return None  # an acid cannot displace itself from its own salt

    freed_formula = ACID_FORMULAS.get(freed_anion)
    if freed_formula is None:
        return None

    freed = ACIDS[freed_anion]
    driven_by_strength = attacking.strength.rank > freed.strength.rank
    driven_by_precipitation = freed_formula in INSOLUBLE_ACIDS
    if not (driven_by_strength or driven_by_precipitation):
        return None

    new_salt = salt_formula(salt_cation, attacking.anion)
    if new_salt is None:
        return None

    note = _stability_note(freed_formula)
    if driven_by_precipitation and not driven_by_strength:
        note = "driven by the acid precipitating" if not note else note
    return Reaction(
        reactants=(salt, acid),
        products=(freed_formula, new_salt),
        template=DISPLACEMENT,
        note=note,
    )


def routes_to(formula: str) -> list[str]:
    """Human-readable ways to make this acid. Empty if it is not an acid."""
    acid = ACIDS_BY_FORMULA.get(formula)
    if acid is None:
        return []

    routes: list[str] = []
    anhydride = ANION_TO_ANHYDRIDE.get(acid.anion)
    if anhydride is not None:
        if ANHYDRIDES[anhydride].hydrates:
            routes.append(f"{anhydride} + {WATER}  ({HYDRATION})")
        else:
            routes.append(f"{anhydride} + {WATER} does NOT run -- {anhydride} will not hydrate")

    element = _hydracid_element(acid.anion)
    if element is not None:
        routes.append(
            f"{ELEMENTAL_FORMULA['H']} + {ELEMENTAL_FORMULA[element]}  ({HYDROGENATION})"
        )

    # displacement frees *this* acid, so the attacker must be stronger than it
    stronger = sorted(
        ACID_FORMULAS[other.anion]
        for other in ACIDS.values()
        if other.strength.rank > acid.strength.rank and other.common
    )
    if stronger:
        routes.append(
            f"a salt of {acid.anion} + a stronger acid"
            f" ({', '.join(stronger)})  ({DISPLACEMENT})"
        )
    elif formula not in INSOLUBLE_ACIDS:
        routes.append(f"no acid is stronger than {formula}, so displacement cannot free it")

    if formula in INSOLUBLE_ACIDS:
        routes.append(
            f"a salt of {acid.anion} + any acid  ({DISPLACEMENT},"
            f" driven by {formula} precipitating rather than by strength)"
        )
    return routes


# Acids that come out of solution rather than staying in it -- the driving force
# for route 4. The solubility table cannot supply this: it treats H+ as always
# soluble, which is right for every acid but these.
INSOLUBLE_ACIDS: frozenset[str] = frozenset({"H2SiO3"})


def _hydracid_element(anion: str) -> str | None:
    for symbol in HYDRACID_ELEMENTS:
        if ion_formula(symbol, default_anion_charge(symbol)) == anion:
            return symbol
    return None


def _stability_note(formula: str) -> str:
    products = decomposition_of(formula)
    return "" if not products else f"unstable -- decomposes to {' + '.join(products)}"
