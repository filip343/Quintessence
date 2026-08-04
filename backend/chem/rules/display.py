"""Species display records: name, class, state, constituent ions.

The brief's species record, assembled from the tables rather than curated. Only
three things here are written down by hand, and they live in `chem.data`:
element names, the monatomic anion names (the stems are irregular -- sulfur ->
sulfide), and which species are not solid. Everything else is composed:

    Na+ + SO4-2  ->  "sodium sulfate"
    Cu+2 + O-2   ->  "copper(II) oxide"
    Na+ + HCO3-  ->  "sodium hydrogencarbonate"

A roman numeral is added exactly when the element shows more than one positive
oxidation state, which is the usual convention and keeps `CuO` and `Cu2O`
distinguishable. Nonmetal oxides outside `ANHYDRIDES` come out as
"nitrogen(IV) oxide" rather than "nitrogen dioxide"; the common ones are named
in the anhydride table, so this only affects oxides the game treats as oddities.

State is room-temperature and, for anything ionic, the solubility table's
answer: soluble -> "aq", anything that comes out of solution -> "s". A salt is
of course a solid in the jar -- "aq" means "this is how the game meets it".
"""

from __future__ import annotations

from dataclasses import dataclass

from chem.data.acids import ACIDS_BY_FORMULA
from chem.data.bases import BASES_BY_FORMULA, HYDROXIDE
from chem.data.elements import ELEMENT_NAMES, ELEMENT_OF_FORMULA, NON_SOLID_ELEMENTS
from chem.data.hydrides import HYDRIDES
from chem.data.ions import (
    CATION_CHARGES,
    MONATOMIC_ANION_NAMES,
    POLYATOMIC_IONS,
    POSITIVE_OXIDATION_STATES,
)
from chem.data.oxides import (
    ANHYDRIDES,
    NEUTRAL_OXIDE_NAMES,
    NON_SOLID_OXIDES,
    OxideCharacter,
)
from chem.data.salts import OXIDE_IONS, SALT_IONS
from chem.formulas import ion_formula, parse_charge, strip_charge
from chem.rules.acids import INSOLUBLE_ACIDS
from chem.rules.oxides import oxide_character
from chem.rules.solubility import solubility
from chem.rules.species import SpeciesClass, classify

SOLID, LIQUID, GAS, AQUEOUS = "s", "l", "g", "aq"

# Amphoteric oxides classify as UNKNOWN -- v1 tags and excludes them (brief,
# "Scope") -- but they are still reachable by burning a metal, so a species
# record has to be able to say what they are.
AMPHOTERIC_OXIDE = "amphoteric oxide"

_ROMAN: dict[int, str] = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII"}


@dataclass(frozen=True, slots=True)
class Species:
    formula: str
    name: str
    species_class: str
    state: str
    # Constituent ions as {core formula: charge}, e.g. {"Na": 1, "OH": -1}.
    # Empty for anything not built from curated ions: elements, oxides, hydrides.
    ions: dict[str, int]


def species_record(formula: str) -> Species:
    return Species(
        formula=formula,
        name=display_name(formula),
        species_class=class_name(formula),
        state=state_of(formula),
        ions=constituent_ions(formula),
    )


# --------------------------------------------------------------------------
# Class
# --------------------------------------------------------------------------


def class_name(formula: str) -> str:
    """The species class as a string, naming the amphoteric oxides UNKNOWN hides."""
    species_class = classify(formula)
    if species_class is not SpeciesClass.UNKNOWN:
        return species_class.value
    entry = OXIDE_IONS.get(formula)
    if entry is not None and oxide_character(*entry) is OxideCharacter.AMPHOTERIC:
        return AMPHOTERIC_OXIDE
    return SpeciesClass.UNKNOWN.value


# --------------------------------------------------------------------------
# Name
# --------------------------------------------------------------------------


def display_name(formula: str) -> str:
    """Display name for any species the engine can make. Never raises."""
    # Water and the neutral oxides first: they are the names the roman-numeral
    # rule below would get wrong.
    neutral = NEUTRAL_OXIDE_NAMES.get(formula)
    if neutral is not None:
        return neutral

    element = ELEMENT_OF_FORMULA.get(formula)
    if element is not None:
        return ELEMENT_NAMES.get(element, formula)

    anhydride = ANHYDRIDES.get(formula)
    if anhydride is not None:
        return anhydride.name

    for table in (ACIDS_BY_FORMULA, BASES_BY_FORMULA, HYDRIDES):
        record = table.get(formula)
        if record is not None:
            return record.name

    ions = SALT_IONS.get(formula)
    if ions is not None:
        return f"{cation_name(ions[0])} {anion_name(ions[1])}"

    oxide = OXIDE_IONS.get(formula)
    if oxide is not None:
        return f"{_element_with_state(*oxide)} oxide"

    return formula


def cation_name(cation: str) -> str:
    """"Na+" -> "sodium", "Fe+3" -> "iron(III)", "NH4+" -> "ammonium"."""
    polyatomic = POLYATOMIC_IONS.get(cation)
    if polyatomic is not None:
        return polyatomic.name
    symbol, charge = strip_charge(cation), parse_charge(cation)
    return _element_with_state(symbol, charge)


def anion_name(anion: str) -> str:
    """"SO4-2" -> "sulfate", "Cl-" -> "chloride"."""
    polyatomic = POLYATOMIC_IONS.get(anion)
    if polyatomic is not None:
        return polyatomic.name
    return MONATOMIC_ANION_NAMES.get(anion, anion)


def _element_with_state(symbol: str, state: int) -> str:
    """Element name, with a roman numeral when the element is multivalent."""
    name = ELEMENT_NAMES.get(symbol, symbol)
    if not _multivalent(symbol):
        return name
    numeral = _ROMAN.get(state)
    return name if numeral is None else f"{name}({numeral})"


def _multivalent(symbol: str) -> bool:
    return (
        len(POSITIVE_OXIDATION_STATES.get(symbol, ())) > 1
        or len(CATION_CHARGES.get(symbol, ())) > 1
    )


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------


def state_of(formula: str) -> str:
    """Room-temperature state: one of "s", "l", "g", "aq"."""
    if formula in NON_SOLID_OXIDES:
        return NON_SOLID_OXIDES[formula]
    if formula in ELEMENT_OF_FORMULA:
        return NON_SOLID_ELEMENTS.get(formula, SOLID)
    if formula in HYDRIDES:
        return GAS
    if formula in ACIDS_BY_FORMULA:
        # Acids are met in solution; the exceptions are the ones that fall out
        # of it, which is exactly what drives `displace_from_salt` route 4.
        return SOLID if formula in INSOLUBLE_ACIDS else AQUEOUS
    base = BASES_BY_FORMULA.get(formula)
    if base is not None:
        return _ionic_state(base.cation, HYDROXIDE)
    ions = SALT_IONS.get(formula)
    if ions is not None:
        return _ionic_state(*ions)
    return SOLID


def _ionic_state(cation: str, anion: str) -> str:
    """Aqueous unless the solubility table says it comes out of solution."""
    return SOLID if solubility(cation, anion).precipitates else AQUEOUS


# --------------------------------------------------------------------------
# Ions
# --------------------------------------------------------------------------


def constituent_ions(formula: str) -> dict[str, int]:
    """{core formula: charge} for anything built from curated ions, else empty.

    Keyed by the ion without its charge suffix, since the charge is the value:
    NaOH -> {"Na": 1, "OH": -1}. Oxides are absent on purpose -- O-2 is kept out
    of the ion index precisely so oxides stay their own class.
    """
    ions = SALT_IONS.get(formula)
    if ions is not None:
        return _as_mapping(*ions)
    base = BASES_BY_FORMULA.get(formula)
    if base is not None:
        return _as_mapping(base.cation, HYDROXIDE)
    acid = ACIDS_BY_FORMULA.get(formula)
    if acid is not None:
        return _as_mapping(ion_formula("H", 1), acid.anion)
    return {}


def _as_mapping(cation: str, anion: str) -> dict[str, int]:
    return {
        strip_charge(cation): parse_charge(cation),
        strip_charge(anion): parse_charge(anion),
    }
