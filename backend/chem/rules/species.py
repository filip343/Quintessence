"""What kind of thing is this formula?

The classes are disjoint by construction, so a formula never means two things at
once: `chem.data.salts` keeps O-2 and OH- out of the salt index precisely so
oxides and bases keep those to themselves. The order below is therefore a
formality rather than a tie-break, except for water, which is a neutral oxide but
deserves its own answer.

Nothing here parses. Every class is a dict lookup against a table or an index.
"""

from __future__ import annotations

from enum import Enum

from chem.data.acids import ACIDS_BY_FORMULA
from chem.data.bases import BASES_BY_FORMULA
from chem.data.elements import ELEMENT_OF_FORMULA
from chem.data.hydrides import HYDRIDES
from chem.data.oxides import ANHYDRIDES, NEUTRAL_OXIDES, WATER
from chem.data.salts import OXIDE_IONS, SALT_IONS


class SpeciesClass(Enum):
    ELEMENT = "element"
    WATER = "water"
    ACIDIC_OXIDE = "acidic oxide"
    BASIC_OXIDE = "basic oxide"
    NEUTRAL_OXIDE = "neutral oxide"
    ACID = "acid"
    BASE = "base"
    SALT = "salt"
    HYDRIDE = "hydride"
    UNKNOWN = "unknown"


def classify(formula: str) -> SpeciesClass:
    if formula == WATER:
        return SpeciesClass.WATER
    if formula in ELEMENT_OF_FORMULA:
        return SpeciesClass.ELEMENT
    if formula in ANHYDRIDES:
        return SpeciesClass.ACIDIC_OXIDE
    if formula in NEUTRAL_OXIDES:
        return SpeciesClass.NEUTRAL_OXIDE
    if formula in HYDRIDES:
        return SpeciesClass.HYDRIDE
    if formula in ACIDS_BY_FORMULA:
        return SpeciesClass.ACID
    if formula in BASES_BY_FORMULA:
        return SpeciesClass.BASE
    if formula in SALT_IONS:
        return SpeciesClass.SALT
    if formula in OXIDE_IONS:
        return _oxide_class(formula)
    return SpeciesClass.UNKNOWN


def is_known(formula: str) -> bool:
    return classify(formula) is not SpeciesClass.UNKNOWN


def _oxide_class(formula: str) -> SpeciesClass:
    from chem.data.oxides import OxideCharacter
    from chem.rules.oxides import oxide_character

    element, state = OXIDE_IONS[formula]
    character = oxide_character(element, state)
    if character is OxideCharacter.BASIC:
        return SpeciesClass.BASIC_OXIDE
    if character is OxideCharacter.ACIDIC:
        return SpeciesClass.ACIDIC_OXIDE
    if character is OxideCharacter.NEUTRAL:
        return SpeciesClass.NEUTRAL_OXIDE
    return SpeciesClass.UNKNOWN  # amphoteric -- out of scope for v1
