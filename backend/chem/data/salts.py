"""Formula -> ions, by exhaustive index rather than by parsing.

Reading `Na2CO3` back into Na+ and CO3-2 looks like it needs a formula parser. It
does not: the space of salts we can build is finite and small. 32 cations by 39
anions is about 1200 formulas, all generated at import by the same criss-cross
that built them in the first place. Lookup is then a dict hit, and a formula the
index does not contain is by definition not a salt we can make.

This unblocks every template that takes a salt apart -- double displacement,
metal displacement, carbonate decomposition.

Two exclusions keep the species classes disjoint, so a formula never means two
things at once:

- O-2 is not indexed: metal oxides are their own class, in `OXIDE_IONS`.
- OH- is not indexed: hydroxides are bases, in `chem.data.bases`.
- H+ and H3O+ are not indexed as cations: those compounds are acids.

`chem.validate` asserts the index has no collisions. Manganate was dropped from
the ion table because it was the only thing that caused one.
"""

from __future__ import annotations

from collections import defaultdict

from chem.data.ions import (
    ANION_FORMULAS,
    CATION_FORMULAS,
    POSITIVE_OXIDATION_STATES,
)
from chem.formulas import criss_cross, oxide_formula, parse_charge, strip_charge

# Ions that belong to another species class, so salts never claim them.
_NON_SALT_ANIONS: frozenset[str] = frozenset({"O-2", "OH-"})
_NON_SALT_CATIONS: frozenset[str] = frozenset({"H+", "H3O+"})


def _build_salt_index() -> tuple[dict[str, tuple[str, str]], dict[str, list[tuple[str, str]]]]:
    index: dict[str, tuple[str, str]] = {}
    seen: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for cation in sorted(CATION_FORMULAS - _NON_SALT_CATIONS):
        for anion in sorted(ANION_FORMULAS - _NON_SALT_ANIONS):
            formula = criss_cross(
                strip_charge(cation), parse_charge(cation), strip_charge(anion), parse_charge(anion)
            )
            seen[formula].append((cation, anion))
            index.setdefault(formula, (cation, anion))

    collisions = {formula: pairs for formula, pairs in seen.items() if len(pairs) > 1}
    return index, collisions


SALT_IONS: dict[str, tuple[str, str]]
SALT_INDEX_COLLISIONS: dict[str, list[tuple[str, str]]]
SALT_IONS, SALT_INDEX_COLLISIONS = _build_salt_index()

SALT_FORMULAS: dict[tuple[str, str], str] = {ions: formula for formula, ions in SALT_IONS.items()}

# Oxide formula -> (element, oxidation state). Same idea, over every state each
# element shows, so `CuO` resolves to copper(+2) without parsing either.
OXIDE_IONS: dict[str, tuple[str, int]] = {
    oxide_formula(element, state): (element, state)
    for element, states in POSITIVE_OXIDATION_STATES.items()
    for state in states
}
