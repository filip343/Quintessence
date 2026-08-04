"""Species that fall apart on their own (brief, table 5).

The data has been in `Acid.decomposes_to` and `Base.decomposes_to` since those
tables were written; this is the rule that finally applies it. H2CO3 -> CO2 +
H2O, H2SO3 -> SO2 + H2O, NH4OH -> NH3 + H2O.

Deliberately *not* automatic. A template that produces H2CO3 still produces
H2CO3, and the player has to take the extra step to break it up. Auto-splitting
would silently rewrite the product of a move the player just made, and the move
budget is the whole scoring mechanic -- a step the engine takes for free is a
step the par calculation has to know about. Keeping it an explicit move keeps
the hypergraph honest.
"""

from __future__ import annotations

from chem.data.acids import ACIDS_BY_FORMULA
from chem.data.bases import BASES_BY_FORMULA
from chem.reaction import Reaction

DECOMPOSITION = "unstable species --> its decomposition products"


def decomposition_products(species: str) -> tuple[str, ...]:
    """What this species falls apart into. Empty if it is stable."""
    acid = ACIDS_BY_FORMULA.get(species)
    if acid is not None:
        return acid.decomposes_to
    base = BASES_BY_FORMULA.get(species)
    if base is not None:
        return base.decomposes_to
    return ()


def is_unstable(species: str) -> bool:
    return bool(decomposition_products(species))


def decompose_unstable(species: str) -> Reaction | None:
    """`unstable species -> products`, for the acids and bases that do not survive."""
    products = decomposition_products(species)
    if not products:
        return None
    return Reaction(
        reactants=(species,),
        products=products,
        template=DECOMPOSITION,
        note="does not survive in solution",
    )
