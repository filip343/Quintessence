"""Halogen in alkali -- the one reaction where a species oxidises and reduces itself.

    Cl2 + 2 NaOH   -> NaClO  + NaCl + H2O      cold, dilute   (bleach)
    3 Cl2 + 6 KOH  -> KClO3 + 5 KCl + 3 H2O    hot, concentrated

Chlorine goes to -1 and to +1 (or +5) in the same equation. No other template
does this: everything else in `chem.rules.salts` recombines ions that arrive
already at their final oxidation state, and `chem.rules.chromate` -- the other
module that earns its own file -- changes an anion without changing any element's
oxidation state at all.

This is the route the hypochlorites and halates were waiting on. They were
curated in `POLYATOMIC_IONS` and indexed into every salt formula, but the only
way into the branch was from a species already inside it: every route to KClO3
needed HClO3, Cl2O5, or another chlorate. Ten templates reached it and none of
them could be entered. `Cl2 + KOH` enters it from two reagents that are in
every palette.

**Conditions.** Hot alkali gives the halate, cold gives the hypohalite, and the
brief puts reaction conditions out of scope for v1. Handled the way
`oxides.oxidations` handles a metal with several oxidation states and
`salts.partial_neutralise` handles a polyprotic acid: offer every product the
tables support, say which is which in the note, and let the player choose. No
condition is modelled -- the choice carries the information instead.

Fluorine is excluded. F2 with alkali gives OF2, not a fluorate: fluorine's only
positive oxidation state does not exist, so the disproportionation cannot run.
Bromine and iodine have no curated hypohalite, which matches the chemistry --
BrO- and IO- disproportionate onward too fast to isolate, so those two give
only the halate.
"""

from __future__ import annotations

from chem.data.activity import NON_DISPLACING_HALOGENS
from chem.data.bases import BASES_BY_FORMULA
from chem.data.elements import ELEMENTAL_FORMULA, HALOGENS
from chem.data.ions import POLYATOMIC_IONS
from chem.data.oxides import WATER
from chem.data.strength import Strength
from chem.formulas import ion_formula
from chem.reaction import Reaction
from chem.rules.salts import salt_formula

DISPROPORTIONATION = "halogen + strong base -> halide + oxyhalide + water"

# Oxyanion suffix -> what to call the condition that gives it. Derived against
# `POLYATOMIC_IONS` rather than curated per halogen: chlorine has both a
# hypochlorite and a chlorate in the table so it offers two products, bromine
# and iodine have only the halate so they offer one.
OXYANION_CONDITIONS: dict[str, str] = {
    "O-": "cold dilute alkali",
    "O3-": "hot concentrated alkali",
}


def disproportionate(halogen: str, base: str) -> list[Reaction]:
    """`halogen + strong base -> halide + oxyhalide + water`, one per product.

    Genuinely one-to-many, and the two answers are different chemistry rather
    than different spectator ions, so both are offered.
    """
    if halogen not in HALOGENS or halogen in NON_DISPLACING_HALOGENS:
        return []
    base_record = BASES_BY_FORMULA.get(base)
    if base_record is None or base_record.strength is not Strength.STRONG:
        return []

    cation = base_record.cation
    halide = salt_formula(cation, ion_formula(halogen, -1))
    if halide is None:
        return []

    reactions: list[Reaction] = []
    for suffix, condition in OXYANION_CONDITIONS.items():
        oxyanion = f"{halogen}{suffix}"
        if oxyanion not in POLYATOMIC_IONS:
            continue
        salt = salt_formula(cation, oxyanion)
        if salt is None or salt == halide:
            continue
        reactions.append(
            Reaction(
                reactants=(ELEMENTAL_FORMULA[halogen], base),
                products=(salt, halide, WATER),
                template=DISPROPORTIONATION,
                note=f"{condition} -- {halogen} is oxidised and reduced at once",
            )
        )
    return reactions


def routes_into_oxyhalides() -> list[str]:
    """Which halogens can enter the oxyhalide branch, and with what product."""
    routes: list[str] = []
    for halogen in sorted(HALOGENS - NON_DISPLACING_HALOGENS):
        products = [
            POLYATOMIC_IONS[f"{halogen}{suffix}"].name
            for suffix in OXYANION_CONDITIONS
            if f"{halogen}{suffix}" in POLYATOMIC_IONS
        ]
        if products:
            routes.append(
                f"{ELEMENTAL_FORMULA[halogen]} + a strong base"
                f"  ({DISPROPORTIONATION}) -> {', '.join(products)}"
            )
    return routes
