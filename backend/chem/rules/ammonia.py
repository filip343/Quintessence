"""The ammonia branch: four templates around one species.

Ammonia earns a module because it is the only base in the game that is not a
hydroxide, and because it is the only way into the ammonium salts -- NH4+ is a
curated cation with a full row of salts in the index that nothing else can reach.

    synthesise()   H2 + N2 -> NH3                     the Haber process
    dissolve()     NH3 + H2O -> NH4OH                 ammonia solution
    with_acid()    NH3 + acid -> ammonium salt        the gas takes the proton
    liberate()     ammonium salt + strong base -> NH3 the test for NH4+

The last two are inverses, which is what makes this a branch rather than a
dead end: a puzzle can go into an ammonium salt and back out again.

`with_acid` is deliberately separate from `neutralise`. Ammonia is not NH4OH: it
takes a proton directly and gives no water, so the template that would otherwise
cover it produces the wrong equation.
"""

from __future__ import annotations

from chem.data.acids import ACIDS_BY_FORMULA
from chem.data.bases import BASE_FORMULAS, BASES_BY_FORMULA
from chem.data.elements import ELEMENTAL_FORMULA
from chem.data.hydrides import AMMONIA, AMMONIUM, HYDRIDE_OF_ELEMENT, HYDRIDES, Hydride
from chem.data.oxides import WATER
from chem.data.salts import SALT_IONS
from chem.data.strength import Strength
from chem.reaction import Reaction
from chem.rules.salts import salt_formula

SYNTHESIS = "hydrogen + nonmetal -> hydride"
DISSOLUTION = "hydride + water -> base"
HYDRIDE_WITH_ACID = "ammonia + acid -> ammonium salt"
LIBERATION = "ammonium salt + strong base -> ammonia + salt + water"

HYDROGEN: str = ELEMENTAL_FORMULA["H"]


# --------------------------------------------------------------------------
# Lookups
# --------------------------------------------------------------------------


def as_hydride(formula: str) -> Hydride | None:
    return HYDRIDES.get(formula)


def is_hydride(formula: str) -> bool:
    return formula in HYDRIDES


def hydride_of(symbol: str) -> str | None:
    """The molecular hydride of an element: "N" -> "NH3"."""
    return HYDRIDE_OF_ELEMENT.get(symbol)


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


def synthesise(symbol: str) -> Reaction | None:
    """`H2 + nonmetal -> hydride`. For nitrogen this is the Haber process.

    The mirror of `chem.rules.acids.hydrogenate`: same reactants, different
    table, because whether H2 + X gives an acid or a base is not something a
    formula-level rule can work out -- it is curated either way.
    """
    formula = HYDRIDE_OF_ELEMENT.get(symbol)
    elemental = ELEMENTAL_FORMULA.get(symbol)
    if formula is None or elemental is None:
        return None
    note = "needs pressure and a catalyst" if formula == AMMONIA else ""
    return Reaction(
        reactants=(HYDROGEN, elemental),
        products=(formula,),
        template=SYNTHESIS,
        note=note,
    )


def dissolve(hydride: str) -> Reaction | None:
    """`hydride + water -> base`, when the conjugate cation has a hydroxide."""
    record = HYDRIDES.get(hydride)
    if record is None:
        return None
    formula = BASE_FORMULAS.get(record.conjugate_cation)
    if formula is None:
        return None
    base = BASES_BY_FORMULA[formula]
    note = ""
    if base.decomposes_to:
        note = f"an equilibrium -- {formula} gives back {' + '.join(base.decomposes_to)}"
    return Reaction(
        reactants=(hydride, WATER),
        products=(formula,),
        template=DISSOLUTION,
        note=note,
    )


def with_acid(hydride: str, acid: str) -> Reaction | None:
    """`ammonia + acid -> ammonium salt`. No water: the gas takes the proton."""
    record = HYDRIDES.get(hydride)
    acid_record = ACIDS_BY_FORMULA.get(acid)
    if record is None or acid_record is None:
        return None
    salt = salt_formula(record.conjugate_cation, acid_record.anion)
    if salt is None:
        return None
    return Reaction(
        reactants=(hydride, acid),
        products=(salt,),
        template=HYDRIDE_WITH_ACID,
        note="no water -- the base is a gas, not a hydroxide",
    )


def liberate(salt: str, base: str) -> Reaction | None:
    """`ammonium salt + strong base -> NH3 + salt + water`.

    The standard lab test for an ammonium salt, and the only route that gets
    ammonia back out of one. Gated on a strong base: a weak one cannot drive off
    the gas.
    """
    ions = SALT_IONS.get(salt)
    base_record = BASES_BY_FORMULA.get(base)
    if ions is None or base_record is None:
        return None
    cation, anion = ions
    if cation != AMMONIUM:
        return None
    if base_record.strength is not Strength.STRONG:
        return None
    if base_record.cation == AMMONIUM:
        return None  # ammonia solution cannot drive off itself

    spectator = salt_formula(base_record.cation, anion)
    if spectator is None:
        return None
    return Reaction(
        reactants=(salt, base),
        products=(AMMONIA, spectator, WATER),
        template=LIBERATION,
        note="warm with alkali -- the test for an ammonium salt",
    )


def routes_to_ammonia() -> list[str]:
    """Human-readable ways to make ammonia, for the `routes` command."""
    return [
        f"{HYDROGEN} + {ELEMENTAL_FORMULA['N']}  ({SYNTHESIS})",
        f"an ammonium salt + a strong base  ({LIBERATION})",
    ]
