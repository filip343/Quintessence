"""Why a plausible-looking pair does nothing.

A dead end used to be silent. Mixing `K + NH4I` and mixing `KF + I2` produced
the same blank, so a player who had reasoned correctly and hit a curated gate
could not tell themselves apart from a player who had guessed. That is the
difference between a teaching game and a game of pixel-hunting, and it is worth
a table.

Only *curated* refusals get a note. "These two classes have no chemistry
together" is not interesting and gets silence; "the activity series says no", "it
would precipitate but only slightly", "the metal attacks the solvent first" are
each a fact a student should walk away with. So the presence of a note is itself
information -- it means you were on chemically sensible ground and one specific
table said no.

**Notes say why not, never what instead.** The brief keeps feedback about the
product rather than about whether a move lies on a path to the target, and a
note reading "try K + H2O" would quietly turn a dead end into a signpost. Saying
that potassium attacks water is a fact about potassium; the player is left to do
something with it.

`explain` refuses to speak about any pair that actually reacts, by asking
`combine` first rather than by trusting the mirrors below to stay in step with
the rules they paraphrase. Those mirrors will drift -- they are prose about a
gate, written next to but not inside the gate -- and this is the one failure mode
that would be a lie to the player rather than merely a silence.
"""

from __future__ import annotations

from chem.data.acids import (
    ACIDS,
    ACIDS_BY_FORMULA,
    ACID_FORMULAS,
    NON_HYDROGEN_ACIDS,
    PARENT_ANION,
)
from chem.data.activity import HALOGEN_RANK, NON_DISPLACING_HALOGENS
from chem.data.bases import BASE_FORMULAS, BASES_BY_FORMULA
from chem.data.elements import ELEMENTAL_FORMULA, ELEMENT_OF_FORMULA
from chem.data.hydrides import AMMONIUM
from chem.data.ions import CATION_CHARGES
from chem.data.salts import SALT_IONS
from chem.data.solubility import Solubility
from chem.data.strength import Strength
from chem.formulas import parse_charge, strip_charge
from chem.rules.acids import INSOLUBLE_ACIDS
from chem.rules.activity import (
    displaces_hydrogen_from_acid,
    is_more_active,
    reacts_with_cold_water,
)
from chem.rules.elements import is_metal
from chem.rules.reactions import combine
from chem.rules.salts import salt_formula
from chem.rules.solubility import certainly_precipitates, solubility
from chem.rules.species import SpeciesClass, classify

# Said of any product caught in the ambiguous middle band of the solubility
# table. The game has no amounts -- that is a core mechanic, not an oversight --
# so a step whose outcome depends on concentration cannot be scored either way.
_MARGINAL = (
    "only slightly soluble, so whether it drops out depends on how concentrated"
    " things are -- and this game has no amounts, so it is left out"
)


def explain(first: str, second: str) -> str | None:
    """Why this pair does nothing, or None if there is nothing worth saying.

    Asking `combine` first is what makes a note safe to show. The checks below
    paraphrase gates rather than sharing code with them, so they can fall out of
    step; this way the worst a stale mirror can do is stay quiet.
    """
    if combine(first, second):
        return None
    return _one_way(first, second) or _one_way(second, first)


def _one_way(left_formula: str, right_formula: str) -> str | None:
    left, right = classify(left_formula), classify(right_formula)
    element = ELEMENT_OF_FORMULA.get(left_formula)

    if left is SpeciesClass.ELEMENT and element is not None:
        if right is SpeciesClass.SALT:
            return _metal_with_salt(element, right_formula) or _halogen_with_salt(
                element, right_formula
            )
        if right is SpeciesClass.ACID:
            return _metal_with_acid(element, right_formula)
        return None

    if left is SpeciesClass.SALT:
        if right is SpeciesClass.SALT:
            return _double_displacement(left_formula, right_formula)
        if right is SpeciesClass.BASE:
            return _salt_with_base(left_formula, right_formula)
        if right is SpeciesClass.ACID:
            return _salt_with_acid(left_formula, right_formula)
    return None


# --------------------------------------------------------------------------
# The gates, paraphrased
# --------------------------------------------------------------------------


def _metal_with_salt(metal: str, salt: str) -> str | None:
    ions = SALT_IONS.get(salt)
    if ions is None or not _curated_metal(metal):
        return None
    cation, anion = ions
    if solubility(cation, anion) is not Solubility.SOLUBLE:
        return None  # a solid cannot swap ions; not a chemistry lesson

    # Ahead of the "is it even a metal" test, unlike the rule itself. Both are
    # true of K + NH4I, but only this one is also true of K + CuSO4, K + AgNO3
    # and every other salt -- so it is the fact worth carrying away.
    if _reacts_with_water(metal):
        return (
            f"{ELEMENTAL_FORMULA[metal]} attacks water on contact, so in solution"
            f" it never reaches the salt"
        )

    displaced = strip_charge(cation)
    if displaced not in CATION_CHARGES or not _is_metal(displaced):
        return f"{cation} is not a metal, so there is nothing here to displace"
    if not _more_active(metal, displaced):
        return (
            f"{ELEMENTAL_FORMULA[metal]} sits below {displaced} in the activity"
            f" series, so it cannot push it out"
        )
    return None


def _halogen_with_salt(halogen: str, salt: str) -> str | None:
    if halogen not in HALOGEN_RANK:
        return None
    ions = SALT_IONS.get(salt)
    if ions is None:
        return None
    cation, anion = ions
    displaced = strip_charge(anion)
    if displaced not in HALOGEN_RANK or parse_charge(anion) != -1:
        return None
    if solubility(cation, anion) is not Solubility.SOLUBLE:
        return None
    if halogen == displaced:
        return None  # a halogen cannot displace itself; nothing to explain
    if halogen in NON_DISPLACING_HALOGENS:
        return (
            f"{ELEMENTAL_FORMULA[halogen]} oxidises the water first, so it never"
            f" gets as far as the halide"
        )
    if HALOGEN_RANK[halogen] >= HALOGEN_RANK[displaced]:
        return (
            f"{ELEMENTAL_FORMULA[halogen]} is less reactive than"
            f" {ELEMENTAL_FORMULA[displaced]}, so it cannot push it out of a halide"
        )
    return None


def _metal_with_acid(metal: str, acid: str) -> str | None:
    if acid not in ACIDS_BY_FORMULA or not _curated_metal(metal):
        return None
    if acid in NON_HYDROGEN_ACIDS:
        return (
            f"{acid} oxidises the metal rather than handing over hydrogen, which"
            f" is outside what this game covers"
        )
    if not _above_hydrogen(metal):
        return (
            f"{ELEMENTAL_FORMULA[metal]} sits below hydrogen in the activity"
            f" series, so it cannot displace it from an acid"
        )
    return None


def _double_displacement(first: str, second: str) -> str | None:
    left, right = SALT_IONS.get(first), SALT_IONS.get(second)
    if left is None or right is None:
        return None
    (left_cation, left_anion), (right_cation, right_anion) = left, right
    if left_cation == right_cation or left_anion == right_anion:
        return None  # the swap is the same two salts back; nothing to say
    if not _in_solution(left_cation, left_anion) or not _in_solution(
        right_cation, right_anion
    ):
        return None

    marginal: list[str] = []
    for cation, anion in ((left_cation, right_anion), (right_cation, left_anion)):
        formula = salt_formula(cation, anion)
        if formula is None:
            return None
        if certainly_precipitates(cation, anion):
            return None  # this pair does react; `explain` should never get here
        if solubility(cation, anion) is Solubility.SLIGHTLY_SOLUBLE:
            marginal.append(formula)

    if marginal:
        return f"{' and '.join(marginal)} {'is' if len(marginal) == 1 else 'are'} {_MARGINAL}"
    return "both possible products stay in solution, so nothing drives the exchange"


def _salt_with_base(salt: str, base: str) -> str | None:
    ions = SALT_IONS.get(salt)
    base_record = BASES_BY_FORMULA.get(base)
    if ions is None or base_record is None:
        return None
    cation, anion = ions

    if cation == AMMONIUM:
        if base_record.cation == AMMONIUM:
            return None  # ammonia solution cannot drive off itself
        if base_record.strength is not Strength.STRONG:
            return f"{base} is too weak to drive the ammonia off -- that needs a strong alkali"
        return None

    if cation == base_record.cation:
        return None  # the swap hands back the same two species
    if not _in_solution(cation, anion):
        return None
    if solubility(base_record.cation, "OH-") is not Solubility.SOLUBLE:
        return None  # the attacking base is not itself in solution

    hydroxide = BASE_FORMULAS.get(cation)
    if hydroxide is None:
        return None
    character = solubility(cation, "OH-")
    if character is Solubility.SLIGHTLY_SOLUBLE:
        return f"{hydroxide} is {_MARGINAL}"
    if character is Solubility.SOLUBLE:
        return f"{hydroxide} is soluble, so it stays in solution and nothing drives the exchange"
    return None


def _salt_with_acid(salt: str, acid: str) -> str | None:
    ions = SALT_IONS.get(salt)
    attacking = ACIDS_BY_FORMULA.get(acid)
    if ions is None or attacking is None:
        return None
    _, salt_anion = ions
    # an acid salt behaves as a salt of its parent acid, exactly as it does in
    # `chem.rules.acids.displace_from_salt`
    freed_anion = PARENT_ANION.get(salt_anion, salt_anion)
    if attacking.anion == freed_anion:
        return None  # an acid cannot displace itself from its own salt
    freed_formula = ACID_FORMULAS.get(freed_anion)
    if freed_formula is None or freed_anion not in ACIDS:
        return None
    if freed_formula in INSOLUBLE_ACIDS:
        return None
    if attacking.strength.rank > ACIDS[freed_anion].strength.rank:
        return None
    return (
        f"{acid} is no stronger than {freed_formula}, so it cannot drive it out"
        f" of its own salt"
    )


# --------------------------------------------------------------------------
# Gate helpers, tolerant of species outside the curated tables
# --------------------------------------------------------------------------


def _curated_metal(metal: str) -> bool:
    return metal in CATION_CHARGES and metal in ELEMENTAL_FORMULA and _is_metal(metal)


def _is_metal(symbol: str) -> bool:
    try:
        return is_metal(symbol)
    except KeyError:
        return False


def _in_solution(cation: str, anion: str) -> bool:
    return solubility(cation, anion) is Solubility.SOLUBLE


def _above_hydrogen(metal: str) -> bool:
    try:
        return displaces_hydrogen_from_acid(metal)
    except KeyError:
        return False


def _more_active(metal: str, other: str) -> bool:
    try:
        return is_more_active(metal, other)
    except KeyError:
        return False


def _reacts_with_water(metal: str) -> bool:
    try:
        return reacts_with_cold_water(metal)
    except KeyError:
        return False
