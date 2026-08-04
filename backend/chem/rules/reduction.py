"""Getting a metal back out of its oxide -- the routes that run downhill.

    reduce_oxide()      metal oxide + C / CO / H2 -> metal + CO2 / H2O
    metal_with_oxide()  metal oxide + more active metal -> oxide + metal

Two things this fixes beyond adding templates.

*Elements become reachable.* Every other route in the game produces a compound;
without reduction the only way back to a free metal is displacement out of a
*solution*, which needs the salt to exist first. A puzzle whose target is "make
copper" was not previously expressible.

*Amphoteric oxides stop being dead ends.* ZnO, SnO2 and friends are tagged out
of scope for v1, so no acid/base template touches them and `classify` returns
UNKNOWN. They were still producible by burning the metal, which left the player
holding a species with no moves. Reduction keys off the oxide index rather than
the species class, so `ZnO + C -> Zn + CO2` runs and the dead end closes.
"""

from __future__ import annotations

from chem.data.activity import ACTIVITY_RANK
from chem.data.elements import ELEMENTAL_FORMULA
from chem.data.reduction import REDUCERS, Reducer
from chem.data.salts import OXIDE_IONS
from chem.formulas import oxide_formula
from chem.reaction import Reaction
from chem.rules.elements import is_metal
from chem.rules.salts import cation_charge_for

REDUCTION = "metal oxide + reducing agent -> metal + oxide"
ALUMINOTHERMIC = "metal oxide + more active metal -> oxide + metal"

OXYGEN_PARTNER = "O"  # what `cation_charge_for` is told the metal is meeting


def as_reducer(formula: str) -> Reducer | None:
    return REDUCERS.get(formula)


def is_reducer(formula: str) -> bool:
    return formula in REDUCERS


def reduce_oxide(oxide: str, reducer: str) -> Reaction | None:
    """`metal oxide + C / CO / H2 -> metal + CO2 / H2O`.

    Gated on the activity series: a reducing agent only works below its own
    threshold. Above it the oxide needs electrolysis, which is out of scope.
    """
    record = REDUCERS.get(reducer)
    metal = _reducible_metal(oxide)
    if record is None or metal is None:
        return None
    if ACTIVITY_RANK[metal] <= ACTIVITY_RANK[record.below]:
        return None

    return Reaction(
        reactants=(oxide, reducer),
        products=(ELEMENTAL_FORMULA[metal], record.oxidised_to),
        template=REDUCTION,
        note=f"{record.name} reduces oxides below {record.below} in the activity series",
    )


def metal_with_oxide(metal: str, oxide: str) -> Reaction | None:
    """`metal oxide + more active metal -> oxide + metal`. Al + Fe2O3 is the classic."""
    displaced = _reducible_metal(oxide)
    if displaced is None or metal not in ACTIVITY_RANK or not is_metal(metal):
        return None
    if metal == displaced:
        return None
    if ACTIVITY_RANK[metal] >= ACTIVITY_RANK[displaced]:
        return None

    charge = cation_charge_for(metal, OXYGEN_PARTNER)
    if charge is None:
        return None
    return Reaction(
        reactants=(oxide, ELEMENTAL_FORMULA[metal]),
        products=(oxide_formula(metal, charge), ELEMENTAL_FORMULA[displaced]),
        template=ALUMINOTHERMIC,
        note=f"{metal} is above {displaced} in the activity series",
    )


def routes_to_element(symbol: str) -> list[str]:
    """Human-readable ways to make a free metal, for the `routes` command."""
    if symbol not in ACTIVITY_RANK or not is_metal(symbol):
        return []

    routes: list[str] = []
    oxide = _oxide_of(symbol)
    if oxide is not None:
        agents = sorted(
            record.formula
            for record in REDUCERS.values()
            if ACTIVITY_RANK[symbol] > ACTIVITY_RANK[record.below]
        )
        if agents:
            routes.append(f"{oxide} + {' or '.join(agents)}  ({REDUCTION})")
        else:
            routes.append(
                f"{oxide} cannot be reduced -- {symbol} is too high in the "
                f"activity series; its oxide needs electrolysis"
            )
        above = sorted(
            other
            for other in ACTIVITY_RANK
            if other != "H" and ACTIVITY_RANK[other] < ACTIVITY_RANK[symbol]
        )
        if above:
            routes.append(f"{oxide} + a more active metal  ({ALUMINOTHERMIC})")
    routes.append(f"a soluble salt of {symbol} + a more active metal  (metal + salt)")
    return routes


def _reducible_metal(oxide: str) -> str | None:
    """The metal of an oxide, if it is one whose reduction the series can judge."""
    resolved = OXIDE_IONS.get(oxide)
    if resolved is None:
        return None
    element, _ = resolved
    if not is_metal(element) or element not in ACTIVITY_RANK:
        return None
    return element


def _oxide_of(symbol: str) -> str | None:
    charge = cation_charge_for(symbol, OXYGEN_PARTNER)
    return None if charge is None else oxide_formula(symbol, charge)
