"""Cross-checks that keep the curated tables honest.

These catch the mistakes hand-written tables actually make: an ion referenced by
the solubility rules that does not exist, an element in the activity series the
metal table calls a nonmetal, an oxide formula whose subscripts disagree with the
oxidation state next to it.

Each `check_*` returns a list of problem strings; empty means clean.
`check_tables()` runs them all, and `python -m chem` reports the result.
"""

from __future__ import annotations

from chem.data.acids import (
    ACID_FORMULAS,
    ACID_SALT_ANIONS,
    ACIDS,
    ACIDS_BY_FORMULA,
    EXCLUDED_ACIDS,
    HYDRACID_ELEMENTS,
    PARENT_ANION,
)
from chem.data.activity import (
    ACTIVITY_RANK,
    ACTIVITY_SERIES,
    HALOGEN_ACTIVITY,
    NON_DISPLACING_HALOGENS,
    WATER_REACTIVITY,
)
from chem.data.bases import (
    BASE_FORMULAS,
    BASES,
    BASES_BY_FORMULA,
    EXCLUDED_BASES,
    HYDRATABLE_OXIDE_CATIONS,
)
from chem.data.elements import (
    COMMON_ELEMENTS,
    ELEMENT_NAMES,
    ELEMENT_OF_FORMULA,
    ELEMENTAL_FORMULA,
    HALOGENS,
    IS_METAL,
    NON_SOLID_ELEMENTS,
    OXIDISING_NONMETALS,
)
from chem.data.hydrides import EXCLUDED_HYDRIDES, HYDRIDE_OF_ELEMENT, HYDRIDES
from chem.data.reduction import EXCLUDED_REDUCERS, REDUCERS
from chem.data.salts import OXIDE_IONS, SALT_INDEX_COLLISIONS, SALT_IONS
from chem.data.ions import (
    ANION_CHARGES,
    ANION_FORMULAS,
    CATION_CHARGES,
    CATION_FORMULAS,
    COMMON_ANIONS,
    COMMON_CATIONS,
    MONATOMIC_ANION_NAMES,
    POLYATOMIC_IONS,
    POSITIVE_OXIDATION_STATES,
)
from chem.data.oxides import (
    ACIDIC_OXIDES,
    ANHYDRIDES,
    ANION_TO_ANHYDRIDE,
    EXCLUDED_OXIDES,
    NEUTRAL_OXIDE_NAMES,
    NEUTRAL_OXIDES,
    NON_SOLID_OXIDES,
    OxideCharacter,
)
from chem.data.solubility import (
    ALWAYS_SOLUBLE_CATIONS,
    ANION_RULES,
    NON_AQUEOUS_ANIONS,
    SOLUBILITY_OVERRIDES,
)
from chem.formulas import oxide_formula, oxygen_count, parse_charge, strip_charge
from chem.reaction import Reaction
from chem.rules.catalogue import RULE_SLUGS
from chem.rules.chromate import CHROMATE, DICHROMATE
from chem.rules.display import GAS, LIQUID
from chem.rules.oxides import oxide_character


def check_ions() -> list[str]:
    """Charge signs, formula suffixes, and coverage by the element table."""
    problems: list[str] = []

    for table_name, symbols in (
        ("CATION_CHARGES", CATION_CHARGES),
        ("ANION_CHARGES", ANION_CHARGES),
        ("POSITIVE_OXIDATION_STATES", POSITIVE_OXIDATION_STATES),
    ):
        for symbol in symbols:
            if symbol not in IS_METAL:
                problems.append(f"{table_name}: {symbol!r} missing from IS_METAL")

    for symbol, charges in CATION_CHARGES.items():
        if any(charge <= 0 for charge in charges):
            problems.append(f"CATION_CHARGES: {symbol!r} has a non-positive charge")
    for symbol, charges in ANION_CHARGES.items():
        if any(charge >= 0 for charge in charges):
            problems.append(f"ANION_CHARGES: {symbol!r} has a non-negative charge")

    # a metal's ionic charges must be available as oxidation states too, or an
    # oxide of that ion cannot be built
    for symbol, charges in CATION_CHARGES.items():
        states = POSITIVE_OXIDATION_STATES.get(symbol)
        if states is None:
            problems.append(f"POSITIVE_OXIDATION_STATES: missing {symbol!r}")
            continue
        for charge in charges:
            if charge not in states:
                problems.append(
                    f"POSITIVE_OXIDATION_STATES: {symbol!r} lacks state +{charge} "
                    f"present in CATION_CHARGES"
                )

    for formula, ion in POLYATOMIC_IONS.items():
        if formula != ion.formula:
            problems.append(f"POLYATOMIC_IONS: key {formula!r} != Ion.formula {ion.formula!r}")
        if parse_charge(formula) != ion.charge:
            problems.append(
                f"POLYATOMIC_IONS: {formula!r} suffix implies "
                f"{parse_charge(formula)}, recorded {ion.charge}"
            )

    return problems


def check_activity() -> list[str]:
    """The series holds metals only, and every metal in it has a water verdict."""
    problems: list[str] = []

    for symbol in ACTIVITY_SERIES:
        if symbol == "H":
            continue
        if symbol not in IS_METAL:
            problems.append(f"ACTIVITY_SERIES: {symbol!r} missing from IS_METAL")
        elif not IS_METAL[symbol]:
            problems.append(f"ACTIVITY_SERIES: {symbol!r} is classified as a nonmetal")

    missing = set(ACTIVITY_SERIES) - {"H"} - set(WATER_REACTIVITY)
    if missing:
        problems.append(f"WATER_REACTIVITY: missing {sorted(missing)}")
    extra = set(WATER_REACTIVITY) - set(ACTIVITY_SERIES)
    if extra:
        problems.append(f"WATER_REACTIVITY: {sorted(extra)} not in ACTIVITY_SERIES")

    # the halogen order must cover exactly the halogens, and they must be able
    # to form the -1 anion the displacement rule builds its product from
    if set(HALOGEN_ACTIVITY) != HALOGENS:
        problems.append(
            f"HALOGEN_ACTIVITY: {sorted(set(HALOGEN_ACTIVITY) ^ HALOGENS)} "
            f"disagrees with HALOGENS"
        )
    for symbol in HALOGEN_ACTIVITY:
        if -1 not in ANION_CHARGES.get(symbol, ()):
            problems.append(f"HALOGEN_ACTIVITY: {symbol!r} has no -1 charge in ANION_CHARGES")
        if symbol not in ELEMENTAL_FORMULA:
            problems.append(f"HALOGEN_ACTIVITY: {symbol!r} has no elemental formula")
    for symbol in NON_DISPLACING_HALOGENS:
        if symbol not in HALOGEN_ACTIVITY:
            problems.append(f"NON_DISPLACING_HALOGENS: {symbol!r} is not a halogen")

    return problems


def check_reduction() -> list[str]:
    """Reducing agents: real species, real thresholds, real products."""
    problems: list[str] = []

    known = set(ANHYDRIDES) | set(NEUTRAL_OXIDES) | set(ELEMENT_OF_FORMULA) | set(OXIDE_IONS)
    for formula, record in REDUCERS.items():
        if formula != record.formula:
            problems.append(f"REDUCERS: key {formula!r} != record {record.formula!r}")
        if formula not in known:
            problems.append(f"REDUCERS[{formula!r}]: not a species anything else can make")
        if record.oxidised_to not in known:
            problems.append(
                f"REDUCERS[{formula!r}]: product {record.oxidised_to!r} is not a known species"
            )
        if record.below not in ACTIVITY_RANK:
            problems.append(
                f"REDUCERS[{formula!r}]: threshold {record.below!r} is not in the activity series"
            )
        elif record.below == "H":
            problems.append(
                f"REDUCERS[{formula!r}]: threshold {record.below!r} is the hydrogen marker, "
                f"not a metal"
            )
        if formula in EXCLUDED_REDUCERS:
            problems.append(f"REDUCERS[{formula!r}]: also listed in EXCLUDED_REDUCERS")

        # a reducer that is itself a reducible metal oxide would reduce itself
        resolved = OXIDE_IONS.get(formula)
        if resolved is not None and IS_METAL.get(resolved[0]):
            problems.append(f"REDUCERS[{formula!r}]: is itself a metal oxide")

    return problems


def check_solubility() -> list[str]:
    """Rules may only reference curated ions, and must cover every aqueous anion."""
    problems: list[str] = []

    for anion, rule in ANION_RULES.items():
        if anion not in ANION_FORMULAS:
            problems.append(f"ANION_RULES: {anion!r} is not a curated anion")
        for cation in rule.exceptions:
            if cation not in CATION_FORMULAS:
                problems.append(f"ANION_RULES[{anion!r}]: {cation!r} is not a curated cation")

    for cation, anion in SOLUBILITY_OVERRIDES:
        if cation not in CATION_FORMULAS:
            problems.append(f"SOLUBILITY_OVERRIDES: {cation!r} is not a curated cation")
        if anion not in ANION_FORMULAS:
            problems.append(f"SOLUBILITY_OVERRIDES: {anion!r} is not a curated anion")

    for cation in ALWAYS_SOLUBLE_CATIONS:
        if cation not in CATION_FORMULAS:
            problems.append(f"ALWAYS_SOLUBLE_CATIONS: {cation!r} is not a curated cation")

    for anion in sorted(ANION_FORMULAS - NON_AQUEOUS_ANIONS):
        if anion not in ANION_RULES:
            problems.append(f"ANION_RULES: no rule for curated anion {anion!r}")

    return problems


def check_oxides() -> list[str]:
    """Every anhydride row, against the ion and oxidation-state tables."""
    problems: list[str] = []

    for formula, record in ANHYDRIDES.items():
        if formula != record.formula:
            problems.append(f"ANHYDRIDES: key {formula!r} != record {record.formula!r}")

        # the oxide formula must be the criss-cross of its own stated valence
        expected = oxide_formula(record.element, record.state)
        if expected != record.formula:
            problems.append(
                f"ANHYDRIDES[{formula!r}]: {record.element} at +{record.state} "
                f"criss-crosses to {expected!r}"
            )

        # that valence must be one the element is recorded as showing
        states = POSITIVE_OXIDATION_STATES.get(record.element)
        if states is None:
            problems.append(f"ANHYDRIDES[{formula!r}]: {record.element!r} has no oxidation states")
        elif record.state not in states:
            problems.append(
                f"ANHYDRIDES[{formula!r}]: +{record.state} not in "
                f"POSITIVE_OXIDATION_STATES[{record.element!r}]"
            )

        # the anion must exist, and its charge must balance the same valence
        ion = POLYATOMIC_IONS.get(record.anion)
        if ion is None:
            problems.append(f"ANHYDRIDES[{formula!r}]: {record.anion!r} is not a curated ion")
            continue
        implied = record.state - 2 * oxygen_count(record.anion)
        if implied != ion.charge:
            problems.append(
                f"ANHYDRIDES[{formula!r}]: {record.anion} implies charge {implied} "
                f"at +{record.state}, recorded {ion.charge}"
            )

        character = oxide_character(record.element, record.state)
        if character is not OxideCharacter.ACIDIC:
            problems.append(f"ANHYDRIDES[{formula!r}]: classifies as {character.value}, not acidic")

    # one anhydride per anion, or `anhydride_of` silently drops rows
    if len(ANION_TO_ANHYDRIDE) != len(ANHYDRIDES):
        problems.append("ANHYDRIDES: two oxides claim the same anion")

    overlap = ACIDIC_OXIDES & (NEUTRAL_OXIDES | EXCLUDED_OXIDES.keys())
    if overlap:
        problems.append(f"ANHYDRIDES: {sorted(overlap)} also listed as neutral/excluded")

    return problems


def check_acids() -> list[str]:
    """Acid records, their derived formulas, and their reachability."""
    problems: list[str] = []

    for anion, acid in ACIDS.items():
        if anion != acid.anion:
            problems.append(f"ACIDS: key {anion!r} != record {acid.anion!r}")
        if anion not in ANION_FORMULAS:
            problems.append(f"ACIDS[{anion!r}]: not a curated anion")
        if parse_charge(anion) >= 0:
            problems.append(f"ACIDS[{anion!r}]: an acid's anion must be negative")
        if anion in EXCLUDED_ACIDS:
            problems.append(f"ACIDS[{anion!r}]: also listed in EXCLUDED_ACIDS")

        formula = ACID_FORMULAS[anion]
        if not formula.startswith("H") and not formula.endswith("H"):
            problems.append(f"ACID_FORMULAS[{anion!r}]: {formula!r} has no acidic hydrogen")

    # a derivation collision would silently hide an acid from formula lookups
    if len(ACIDS_BY_FORMULA) != len(ACIDS):
        problems.append("ACID_FORMULAS: two acids derive the same formula")

    # every anhydride must lead somewhere -- otherwise hydration produces nothing
    for oxide, record in ANHYDRIDES.items():
        if record.anion not in ACIDS:
            problems.append(f"ANHYDRIDES[{oxide!r}]: no acid recorded for {record.anion!r}")

    # every hydracid element must have both a free-element formula and an acid
    for symbol in HYDRACID_ELEMENTS:
        if symbol not in IS_METAL:
            problems.append(f"HYDRACID_ELEMENTS: {symbol!r} missing from IS_METAL")
        elif IS_METAL[symbol]:
            problems.append(f"HYDRACID_ELEMENTS: {symbol!r} is a metal")

    # decomposition products must be species something else can recognise
    known = set(ANHYDRIDES) | set(NEUTRAL_OXIDES) | set(ELEMENT_OF_FORMULA)
    for anion, acid in ACIDS.items():
        for product in acid.decomposes_to:
            if product not in known:
                problems.append(
                    f"ACIDS[{anion!r}]: decomposition product {product!r} is not a known species"
                )

    return problems


def check_acid_salts() -> list[str]:
    """Re-derive every acid-salt anion from its parent's charge arithmetic.

    `ACID_SALT_ANIONS` is generated, so the risk is not a typo -- it is the
    generator quietly producing a formula that happens to collide with a
    curated ion meaning something else. Checking the charge and the atom count
    independently catches that.
    """
    problems: list[str] = []

    for parent, group in ACID_SALT_ANIONS.items():
        if parent not in ACIDS:
            problems.append(f"ACID_SALT_ANIONS: {parent!r} is not an acid's anion")
            continue
        parent_charge = parse_charge(parent)
        core = strip_charge(parent)

        for index, partial in enumerate(group, start=1):
            ion = POLYATOMIC_IONS.get(partial)
            if ion is None:
                problems.append(f"ACID_SALT_ANIONS[{parent!r}]: {partial!r} is not a curated ion")
                continue
            # one proton per step: charge rises by exactly the step number
            if ion.charge != parent_charge + index:
                problems.append(
                    f"ACID_SALT_ANIONS[{parent!r}]: {partial!r} has charge {ion.charge}, "
                    f"expected {parent_charge + index} after {index} proton(s)"
                )
            expected = f"H{index if index > 1 else ''}{core}"
            if strip_charge(partial) != expected:
                problems.append(
                    f"ACID_SALT_ANIONS[{parent!r}]: {partial!r} is not {expected!r}"
                )
            if partial not in EXCLUDED_ACIDS:
                problems.append(
                    f"EXCLUDED_ACIDS: {partial!r} is an acid salt anion and should be "
                    f"listed there with a reason"
                )

        # a full set is one anion per removable proton, less the parent itself
        if len(group) != -parent_charge - 1:
            problems.append(
                f"ACID_SALT_ANIONS[{parent!r}]: {len(group)} acid salt anion(s) for "
                f"{-parent_charge} protons -- the ion table is missing one"
            )

    # the reverse map must be a clean inverse, or an acid salt resolves to the
    # wrong parent acid in `displace_from_salt`
    if len(PARENT_ANION) != sum(len(group) for group in ACID_SALT_ANIONS.values()):
        problems.append("PARENT_ANION: two parents claim the same acid salt anion")
    for partial, parent in PARENT_ANION.items():
        if partial not in ACID_SALT_ANIONS.get(parent, ()):
            problems.append(f"PARENT_ANION: {partial!r} -> {parent!r} is not in ACID_SALT_ANIONS")
        if partial in ACIDS:
            problems.append(f"PARENT_ANION: {partial!r} is also a full acid's anion")

    return problems


def check_chromate() -> list[str]:
    """The chromate pair must be curated ions with a salt each."""
    problems: list[str] = []

    for formula in (CHROMATE, DICHROMATE):
        if formula not in POLYATOMIC_IONS:
            problems.append(f"chromate rules: {formula!r} is not a curated ion")
        if formula not in ANION_RULES:
            problems.append(f"chromate rules: {formula!r} has no solubility rule")
    if CHROMATE not in ACIDS:
        problems.append(f"chromate rules: no acid recorded for {CHROMATE!r}")

    # the condensation halves the chromium count per formula unit; if the two
    # ions ever disagreed on that, the equation would balance but mean nothing
    if oxygen_count(DICHROMATE) != 2 * oxygen_count(CHROMATE) - 1:
        problems.append(
            f"chromate rules: {DICHROMATE!r} should have one oxygen fewer than two "
            f"{CHROMATE!r}"
        )

    return problems


def check_bases() -> list[str]:
    """Base records, their cations, and the oxide-hydration derivation."""
    problems: list[str] = []

    for cation, base in BASES.items():
        if cation != base.cation:
            problems.append(f"BASES: key {cation!r} != record {base.cation!r}")
        if cation not in CATION_FORMULAS:
            problems.append(f"BASES[{cation!r}]: not a curated cation")
        if parse_charge(cation) <= 0:
            problems.append(f"BASES[{cation!r}]: a base's cation must be positive")
        if cation in EXCLUDED_BASES:
            problems.append(f"BASES[{cation!r}]: also listed in EXCLUDED_BASES")
        if "OH" not in BASE_FORMULAS[cation]:
            problems.append(f"BASE_FORMULAS[{cation!r}]: {BASE_FORMULAS[cation]!r} has no hydroxide")

    if len(BASES_BY_FORMULA) != len(BASES):
        problems.append("BASE_FORMULAS: two bases derive the same formula")

    # a hydratable oxide needs a cation that actually forms that oxide
    for cation in HYDRATABLE_OXIDE_CATIONS:
        element, charge = strip_charge(cation), parse_charge(cation)
        if charge not in POSITIVE_OXIDATION_STATES.get(element, ()):
            problems.append(
                f"HYDRATABLE_OXIDE_CATIONS: {cation!r} has no oxide "
                f"-- +{charge} is not an oxidation state of {element}"
            )

    known = set(ANHYDRIDES) | set(NEUTRAL_OXIDES) | set(HYDRIDES) | set(ELEMENT_OF_FORMULA)
    for cation, base in BASES.items():
        for product in base.decomposes_to:
            if product not in known:
                problems.append(
                    f"BASES[{cation!r}]: decomposition product {product!r} is not a known species"
                )

    return problems


def check_hydrides() -> list[str]:
    """Hydride records, and the class boundary against acids and salts."""
    problems: list[str] = []

    for formula, record in HYDRIDES.items():
        if formula != record.formula:
            problems.append(f"HYDRIDES: key {formula!r} != record {record.formula!r}")
        if record.element not in IS_METAL:
            problems.append(f"HYDRIDES[{formula!r}]: {record.element!r} missing from IS_METAL")
        elif IS_METAL[record.element]:
            problems.append(
                f"HYDRIDES[{formula!r}]: {record.element!r} is a metal -- "
                f"its hydride is ionic and belongs in the salt index"
            )
        if formula in EXCLUDED_HYDRIDES:
            problems.append(f"HYDRIDES[{formula!r}]: also listed in EXCLUDED_HYDRIDES")

        # the conjugate cation is the whole point of the record: without a base
        # for it, `dissolve` produces nothing and the branch is a dead end
        if record.conjugate_cation not in CATION_FORMULAS:
            problems.append(
                f"HYDRIDES[{formula!r}]: {record.conjugate_cation!r} is not a curated cation"
            )
        elif record.conjugate_cation not in BASES:
            problems.append(
                f"HYDRIDES[{formula!r}]: no base recorded for {record.conjugate_cation!r}"
            )

        # classes must stay disjoint, or `classify` answers by table order
        if formula in ACIDS_BY_FORMULA:
            problems.append(f"HYDRIDES: {formula!r} is also an acid")
        if formula in BASES_BY_FORMULA:
            problems.append(f"HYDRIDES: {formula!r} is also a base")
        if formula in SALT_IONS:
            problems.append(f"HYDRIDES: {formula!r} is also in the salt index")
        if formula in OXIDE_IONS:
            problems.append(f"HYDRIDES: {formula!r} is also an oxide")

    # one hydride per element, or `synthesise` silently drops rows
    if len(HYDRIDE_OF_ELEMENT) != len(HYDRIDES):
        problems.append("HYDRIDES: two hydrides claim the same element")

    # H2 + X must give either an acid or a hydride, never both
    overlap = {HYDRIDES[f].element for f in HYDRIDES} & HYDRACID_ELEMENTS
    if overlap:
        problems.append(f"HYDRIDES: {sorted(overlap)} also in HYDRACID_ELEMENTS")

    return problems


def check_salt_index() -> list[str]:
    """The formula -> ions index must be unambiguous, or lookups lie."""
    problems: list[str] = []

    for formula, pairs in SALT_INDEX_COLLISIONS.items():
        problems.append(f"SALT_IONS: {formula!r} is ambiguous -- {pairs}")

    # species classes must stay disjoint, or `classify` picks by accident
    for formula in SALT_IONS:
        if formula in OXIDE_IONS:
            problems.append(f"SALT_IONS: {formula!r} is also an oxide")
        if formula in ACIDS_BY_FORMULA:
            problems.append(f"SALT_IONS: {formula!r} is also an acid")
        if formula in BASES_BY_FORMULA:
            problems.append(f"SALT_IONS: {formula!r} is also a base")

    for symbol in OXIDISING_NONMETALS:
        if symbol not in IS_METAL:
            problems.append(f"OXIDISING_NONMETALS: {symbol!r} missing from IS_METAL")
        elif IS_METAL[symbol]:
            problems.append(f"OXIDISING_NONMETALS: {symbol!r} is a metal")

    return problems


def check_display() -> list[str]:
    """Display data must cover the tables it decorates.

    Names are the one kind of data nothing else depends on, which is exactly why
    they rot: a new element or ion works perfectly and simply has no name until
    something renders it. These checks make that a failure at import time rather
    than a bare formula in the exported species list.
    """
    problems: list[str] = []

    for symbol in IS_METAL:
        if symbol not in ELEMENT_NAMES:
            problems.append(f"ELEMENT_NAMES: no name for element {symbol!r}")
    for symbol in ELEMENT_NAMES:
        if symbol not in IS_METAL:
            problems.append(f"ELEMENT_NAMES: {symbol!r} is not in IS_METAL")

    for formula in NON_SOLID_ELEMENTS:
        if formula not in ELEMENT_OF_FORMULA:
            problems.append(f"NON_SOLID_ELEMENTS: {formula!r} is not an element species")
    for formula in NON_SOLID_OXIDES:
        if formula not in OXIDE_IONS:
            problems.append(f"NON_SOLID_OXIDES: {formula!r} is not an oxide")

    for state in list(NON_SOLID_ELEMENTS.values()) + list(NON_SOLID_OXIDES.values()):
        if state not in (LIQUID, GAS):
            problems.append(f"a non-solid table lists state {state!r}")

    # every monatomic anion the salt index can produce needs a name
    for anion in ANION_FORMULAS:
        if anion in POLYATOMIC_IONS or anion in MONATOMIC_ANION_NAMES:
            continue
        problems.append(f"MONATOMIC_ANION_NAMES: no name for {anion!r}")
    for anion in MONATOMIC_ANION_NAMES:
        if anion not in ANION_FORMULAS:
            problems.append(f"MONATOMIC_ANION_NAMES: {anion!r} is not a curated anion")

    for formula in NEUTRAL_OXIDE_NAMES:
        if formula not in OXIDE_IONS:
            problems.append(f"NEUTRAL_OXIDE_NAMES: {formula!r} is not an oxide")

    # commonness is a judgement about syllabus coverage, but it still has to
    # name ions and elements that exist -- a typo here silently makes a species
    # uncommon, which quietly drops it out of every difficulty grade
    for cation in COMMON_CATIONS:
        if cation not in CATION_FORMULAS:
            problems.append(f"COMMON_CATIONS: {cation!r} is not a curated cation")
    for anion in COMMON_ANIONS:
        if anion not in ANION_FORMULAS:
            problems.append(f"COMMON_ANIONS: {anion!r} is not a curated anion")
    for symbol in COMMON_ELEMENTS:
        if symbol not in IS_METAL:
            problems.append(f"COMMON_ELEMENTS: {symbol!r} is not a curated element")

    # the slug is what persists, so two templates sharing one would silently
    # merge two rules in every exported file
    slugs: dict[str, str] = {}
    for template, slug in RULE_SLUGS.items():
        if slug in slugs:
            problems.append(f"RULE_SLUGS: {slug!r} is used by {slugs[slug]!r} and {template!r}")
        slugs[slug] = template

    return problems


def check_symmetry() -> list[str]:
    """Mixing is unordered: `a + b` must be the same reaction as `b + a`.

    The player picks two bottles, not a first and a second, so a template that
    reads its arguments positionally is a bug — and it surfaces in the ugliest
    possible way, as the game asking which of two identical reactions you meant.
    `double_displacement` did exactly that: it returned on the first ion pairing
    that precipitated, so where *both* new salts are insoluble (AgF + CaBr2
    gives AgBr and CaF2) the two orders named different precipitates.

    Swept in two passes, because one pass cannot be both cheap and sensitive:

    - every pair of common species through `combine`, which covers all thirty-one
      templates but only at the scale a player meets;
    - every pair of the 1260 indexed salts through `double_displacement` alone.
      That is where the combinatorics are, and the bug above appears on none of
      the common pairs — a sample would have called it clean.
    """
    from chem.rules.commonness import is_common
    from chem.rules.reactions import combine
    from chem.rules.salts import double_displacement

    def signature(reactions: list[Reaction]) -> set[tuple[object, ...]]:
        return {(tuple(sorted(r.reactants)), r.products, r.template, r.note) for r in reactions}

    problems: list[str] = []

    common = sorted(
        {formula for formula in SALT_IONS if is_common(formula)}
        | {formula for formula in ACID_FORMULAS.values() if is_common(formula)}
        | {formula for formula in BASE_FORMULAS.values() if is_common(formula)}
        | {formula for formula in OXIDE_IONS if is_common(formula)}
    )
    for index, first in enumerate(common):
        for second in common[index + 1 :]:
            forward, backward = combine(first, second), combine(second, first)
            if signature(forward) != signature(backward):
                problems.append(
                    f"{first} + {second} differs from {second} + {first}: "
                    f"{[str(r) for r in forward]} vs {[str(r) for r in backward]}"
                )

    salts = sorted(SALT_IONS)
    for index, first in enumerate(salts):
        for second in salts[index + 1 :]:
            forward, backward = (
                double_displacement(first, second),
                double_displacement(second, first),
            )
            if (forward is None) != (backward is None):
                problems.append(f"{first} + {second} reacts one way round only")
            elif forward is not None and backward is not None:
                if (forward.products, forward.note) != (backward.products, backward.note):
                    problems.append(
                        f"{first} + {second} swaps its products when written the "
                        f"other way: {forward} vs {backward}"
                    )
    return problems


def check_tables() -> list[str]:
    """Run every check. Empty result means the tables agree with each other."""
    return (
        check_ions()
        + check_symmetry()
        + check_display()
        + check_activity()
        + check_solubility()
        + check_oxides()
        + check_acids()
        + check_acid_salts()
        + check_bases()
        + check_chromate()
        + check_hydrides()
        + check_reduction()
        + check_salt_index()
    )
