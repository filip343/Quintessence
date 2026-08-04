"""Oxide classification and anhydride lookups over `chem.data.oxides`."""

from __future__ import annotations

from chem.data.elements import (
    AMPHOTERIC_OXIDE_ELEMENTS,
    ELEMENTAL_FORMULA,
    NOBLE_GASES,
)
from chem.data.ions import POSITIVE_OXIDATION_STATES
from chem.data.oxides import (
    ACIDIC_METAL_STATE,
    ANHYDRIDES,
    ANION_TO_ANHYDRIDE,
    EXCLUDED_OXIDES,
    NEUTRAL_OXIDES,
    OXIDE_CHARACTER_OVERRIDES,
    Anhydride,
    OxideCharacter,
)
from chem.formulas import oxide_formula
from chem.reaction import Reaction
from chem.rules.elements import is_metal

OXIDATION = "element + oxygen -> oxide"


def oxide_character(symbol: str, state: int) -> OxideCharacter:
    """Classify an oxide from its central element and oxidation state.

    Order matters: a high enough oxidation state makes a metal oxide acidic even
    when lower oxides of the same metal are amphoteric (Cr2O3 vs CrO3).
    """
    formula = oxide_formula(symbol, state)
    override = OXIDE_CHARACTER_OVERRIDES.get(formula)
    if override is not None:
        return override
    if formula in NEUTRAL_OXIDES:
        return OxideCharacter.NEUTRAL
    if is_metal(symbol) and state >= ACIDIC_METAL_STATE:
        return OxideCharacter.ACIDIC
    if symbol in AMPHOTERIC_OXIDE_ELEMENTS:
        return OxideCharacter.AMPHOTERIC
    if not is_metal(symbol):
        return OxideCharacter.ACIDIC
    return OxideCharacter.BASIC


def anhydride(formula: str) -> Anhydride | None:
    """The anhydride record for an oxide formula, if it is one."""
    return ANHYDRIDES.get(formula)


def anhydride_of(anion: str) -> str | None:
    """The oxide whose hydration gives the acid of `anion`, if there is one."""
    return ANION_TO_ANHYDRIDE.get(anion)


def is_acidic_oxide(formula: str) -> bool:
    return formula in ANHYDRIDES


def hydrates(formula: str) -> bool:
    """True if `oxide + water -> acid` runs for this anhydride (SiO2 does not)."""
    record = ANHYDRIDES.get(formula)
    return record is not None and record.hydrates


def oxidations(symbol: str) -> list[Reaction]:
    """`element + oxygen -> oxide`, one reaction per oxidation state it shows.

    Genuinely one-to-many: nitrogen burns to five different oxides. The caller
    decides which product a move produces -- this rule reports them all, in the
    element's own most-common-first order, and says what each one is.
    """
    if symbol == "O" or symbol in NOBLE_GASES:
        return []
    states = POSITIVE_OXIDATION_STATES.get(symbol)
    elemental = ELEMENTAL_FORMULA.get(symbol)
    if not states or elemental is None:
        return []

    reactions: list[Reaction] = []
    for state in states:
        formula = oxide_formula(symbol, state)
        excluded = EXCLUDED_OXIDES.get(formula)
        note = f"{oxide_character(symbol, state).value} oxide"
        if formula in ANHYDRIDES:
            note += f", anhydride of the acid of {ANHYDRIDES[formula].anion}"
        elif excluded is not None:
            note += f" -- excluded: {excluded}"
        reactions.append(
            Reaction(
                reactants=(elemental, ELEMENTAL_FORMULA["O"]),
                products=(formula,),
                template=OXIDATION,
                note=note,
            )
        )
    return reactions
