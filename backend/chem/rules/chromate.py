"""The chromate/dichromate equilibrium -- yellow one way, orange the other.

    acidify()  2 K2CrO4 + H2SO4 -> K2Cr2O7 + K2SO4 + H2O
    alkalise()   K2Cr2O7 + 2 KOH -> 2 K2CrO4 + H2O

This is a template unlike any other in the game. Every other rule recombines
whole ions; this one *changes the anion itself*, condensing two chromates into
one dichromate. Which is exactly why it earns a module rather than a branch in
`chem.rules.salts` -- the criss-cross machinery does not describe what is
happening here, it only writes down the result.

Worth having for two reasons beyond the colour change. Dichromate was one of the
stranded anions: curated in `POLYATOMIC_IONS`, indexed into every salt formula,
and reachable by nothing. And the route to it is genuinely long --
Cr -> CrO3 -> H2CrO4 -> K2CrO4 -> K2Cr2O7 is five moves, which is deeper than
anything else the network contains.

The pair is a true equilibrium, so both directions are offered; the engine has
no pH, and the reagent is what decides the direction.
"""

from __future__ import annotations

from chem.data.acids import ACIDS_BY_FORMULA
from chem.data.bases import BASES_BY_FORMULA
from chem.data.oxides import WATER
from chem.data.salts import SALT_IONS
from chem.data.strength import Strength
from chem.reaction import Reaction
from chem.rules.salts import salt_formula

CHROMATE: str = "CrO4-2"
DICHROMATE: str = "Cr2O7-2"

ACIDIFY = "chromate + acid -> dichromate + salt + water"
ALKALISE = "dichromate + base -> chromate + water"


def acidify(salt: str, acid: str) -> Reaction | None:
    """`chromate + acid -> dichromate + salt + water`. Yellow to orange."""
    ions = SALT_IONS.get(salt)
    acid_record = ACIDS_BY_FORMULA.get(acid)
    if ions is None or acid_record is None:
        return None
    cation, anion = ions
    if anion != CHROMATE:
        return None
    # chromic and dichromic acid are the same chromium chemistry -- letting them
    # attack would put a reactant on both sides of the equation
    if acid_record.anion in (CHROMATE, DICHROMATE):
        return None
    if acid_record.strength.rank < Strength.MODERATE.rank:
        return None  # a weak acid does not shift the equilibrium

    dichromate = salt_formula(cation, DICHROMATE)
    spectator = salt_formula(cation, acid_record.anion)
    if dichromate is None or spectator is None:
        return None
    return Reaction(
        reactants=(salt, acid),
        products=(dichromate, spectator, WATER),
        template=ACIDIFY,
        note="the yellow chromate turns orange",
    )


def alkalise(salt: str, base: str) -> Reaction | None:
    """`dichromate + base -> chromate + water`. Orange back to yellow.

    Restricted to a base of the same cation, for the same reason
    `acid_salt_with_base` is: anything else gives a mixed salt we cannot write.
    """
    ions = SALT_IONS.get(salt)
    base_record = BASES_BY_FORMULA.get(base)
    if ions is None or base_record is None:
        return None
    cation, anion = ions
    if anion != DICHROMATE or base_record.cation != cation:
        return None
    if base_record.strength is not Strength.STRONG:
        return None

    chromate = salt_formula(cation, CHROMATE)
    if chromate is None:
        return None
    return Reaction(
        reactants=(salt, base),
        products=(chromate, WATER),
        template=ALKALISE,
        note="the orange dichromate turns yellow again",
    )
