"""Dispatcher: given one or two species, which rule templates fire?

This is what the game's move calls. `combine` tries every template both ways
round and de-duplicates, so callers never worry about argument order.

Species are plain formula strings throughout. That works because no template
parses anything -- each recognises its inputs by table lookup, and salts are
taken apart through the precomputed index in `chem.data.salts`.
"""

from __future__ import annotations

from chem.data.acids import HYDRACID_ELEMENTS
from chem.data.elements import ELEMENTAL_FORMULA, ELEMENT_OF_FORMULA
from chem.data.hydrides import HYDRIDE_ELEMENTS
from chem.reaction import Reaction
from chem.rules.acids import displace_from_salt, hydrate, hydrogenate
from chem.rules.ammonia import dissolve, liberate, synthesise, with_acid
from chem.rules.bases import hydrate_oxide, metal_with_water
from chem.rules.disproportionation import disproportionate
from chem.data.salts import OXIDE_IONS
from chem.rules.oxides import oxidations
from chem.rules.reduction import metal_with_oxide, reduce_oxide
from chem.rules.unstable import decompose_unstable
from chem.rules.chromate import acidify, alkalise
from chem.rules.salts import (
    acid_salt_with_base,
    acid_with_basic_oxide,
    base_with_acidic_oxide,
    decompose_carbonate,
    decompose_hydrogencarbonate,
    double_displacement,
    halogen_with_salt,
    metal_with_acid,
    metal_with_nonmetal,
    metal_with_salt,
    neutralise,
    oxide_with_oxide,
    partial_neutralise,
    salt_with_parent_acid,
)
from chem.rules.species import SpeciesClass, classify

OXYGEN: str = ELEMENTAL_FORMULA["O"]
HYDROGEN: str = ELEMENTAL_FORMULA["H"]


def combine(first: str, second: str) -> list[Reaction]:
    """Every reaction the two species can undergo together, in any order."""
    found = _one_way(first, second) + _one_way(second, first)
    return _deduplicate(found)


def decompose(species: str) -> list[Reaction]:
    """Single-input reactions -- what this species does on its own, with heat."""
    return (
        _maybe(decompose_unstable(species))
        + _maybe(decompose_hydrogencarbonate(species))
        + _maybe(decompose_carbonate(species))
    )


def products_of(reactions: list[Reaction]) -> list[str]:
    """Flatten a reaction list to the species it can put in the inventory."""
    seen: dict[str, None] = {}
    for reaction in reactions:
        for product in reaction.products:
            seen.setdefault(product, None)
    return list(seen)


def _one_way(first: str, second: str) -> list[Reaction]:
    left, right = classify(first), classify(second)
    element, partner = ELEMENT_OF_FORMULA.get(first), ELEMENT_OF_FORMULA.get(second)

    # --- element + element -------------------------------------------------
    if left is SpeciesClass.ELEMENT and right is SpeciesClass.ELEMENT:
        assert element is not None and partner is not None
        if second == OXYGEN:
            return oxidations(element)
        if first == HYDROGEN and partner in HYDRACID_ELEMENTS:
            return _maybe(hydrogenate(partner))
        if first == HYDROGEN and partner in HYDRIDE_ELEMENTS:
            return _maybe(synthesise(partner))
        return _maybe(metal_with_nonmetal(element, partner))

    # --- anything + water --------------------------------------------------
    if right is SpeciesClass.WATER:
        if left is SpeciesClass.ACIDIC_OXIDE:
            return _maybe(hydrate(first))
        if left is SpeciesClass.BASIC_OXIDE:
            return _maybe(hydrate_oxide(first))
        if left is SpeciesClass.ELEMENT and element is not None:
            return _maybe(metal_with_water(element))
        if left is SpeciesClass.HYDRIDE:
            return _maybe(dissolve(first))
        return []

    # --- hydride + acid ----------------------------------------------------
    if left is SpeciesClass.HYDRIDE and right is SpeciesClass.ACID:
        return _maybe(with_acid(first, second))

    # --- reduction ---------------------------------------------------------
    # Keyed off the oxide index rather than the species class, deliberately: the
    # amphoteric oxides classify as UNKNOWN and would otherwise stay unreachable.
    if first in OXIDE_IONS:
        found = _maybe(reduce_oxide(first, second))
        if right is SpeciesClass.ELEMENT and partner is not None:
            found += _maybe(metal_with_oxide(partner, first))
        if found:
            return found

    # --- acid + partner ----------------------------------------------------
    if left is SpeciesClass.ACID:
        if right is SpeciesClass.BASE:
            return _maybe(neutralise(first, second)) + partial_neutralise(first, second)
        if right is SpeciesClass.BASIC_OXIDE:
            return _maybe(acid_with_basic_oxide(first, second))
        if right is SpeciesClass.ELEMENT and partner is not None:
            return _maybe(metal_with_acid(partner, first))
        return []

    # --- element + base ----------------------------------------------------
    # Only the halogens do anything with alkali, and what they do is
    # disproportionate rather than recombine ions.
    if left is SpeciesClass.ELEMENT and right is SpeciesClass.BASE and element is not None:
        return disproportionate(element, second)

    # --- base + acidic oxide -----------------------------------------------
    if left is SpeciesClass.BASE and right is SpeciesClass.ACIDIC_OXIDE:
        return _maybe(base_with_acidic_oxide(first, second))

    # --- oxide + oxide -----------------------------------------------------
    if left is SpeciesClass.BASIC_OXIDE and right is SpeciesClass.ACIDIC_OXIDE:
        return _maybe(oxide_with_oxide(first, second))

    # --- salt + partner ----------------------------------------------------
    if left is SpeciesClass.SALT:
        if right is SpeciesClass.SALT:
            return _maybe(double_displacement(first, second))
        if right is SpeciesClass.ELEMENT and partner is not None:
            return _maybe(metal_with_salt(partner, first)) + _maybe(
                halogen_with_salt(partner, first)
            )
        if right is SpeciesClass.BASE:
            return (
                _maybe(liberate(first, second))
                + _maybe(alkalise(first, second))
                + acid_salt_with_base(first, second)
                + _maybe(double_displacement_with_base(first, second))
            )
        if right is SpeciesClass.ACID:
            return (
                _maybe(displace_from_salt(first, second))
                + _maybe(acidify(first, second))
                + salt_with_parent_acid(first, second)
            )
        return []

    return []


def double_displacement_with_base(salt: str, base: str) -> Reaction | None:
    """`salt + base -> base + salt`, when the new hydroxide precipitates.

    The same exchange as `salt + salt`; it is here rather than in `salts` because
    the driving force is a hydroxide coming out of solution, which is how every
    insoluble base is actually made.
    """
    from chem.data.bases import BASE_FORMULAS, BASES_BY_FORMULA
    from chem.data.salts import SALT_IONS
    from chem.rules.salts import salt_formula
    from chem.rules.solubility import certainly_precipitates, solubility
    from chem.data.solubility import Solubility

    ions = SALT_IONS.get(salt)
    base_record = BASES_BY_FORMULA.get(base)
    if ions is None or base_record is None:
        return None
    cation, anion = ions
    if solubility(cation, anion) is not Solubility.SOLUBLE:
        return None
    if solubility(base_record.cation, "OH-") is not Solubility.SOLUBLE:
        return None  # the attacking base must itself be in solution
    if not certainly_precipitates(cation, "OH-"):
        return None

    precipitate = BASE_FORMULAS.get(cation)
    spectator = salt_formula(base_record.cation, anion)
    if precipitate is None or spectator is None:
        return None
    return Reaction(
        reactants=(salt, base),
        products=(precipitate, spectator),
        template="salt + base -> base + salt",
        note=f"{precipitate} precipitates",
    )


def _maybe(reaction: Reaction | None) -> list[Reaction]:
    return [] if reaction is None else [reaction]


def _deduplicate(reactions: list[Reaction]) -> list[Reaction]:
    seen: dict[tuple[tuple[str, ...], tuple[str, ...]], Reaction] = {}
    for reaction in reactions:
        key = (tuple(sorted(reaction.reactants)), reaction.products)
        seen.setdefault(key, reaction)
    return list(seen.values())
