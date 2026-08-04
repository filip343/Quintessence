"""Reducing agents: what pulls the oxygen back out of a metal oxide.

The network could previously only go *up* the oxidation ladder. An element
burned to an oxide and that was the end of it -- the only way back to a free
metal was displacement by a more active metal, and carbon's entire chemistry was
"burns to CO2". This table is the way back down, and it is what makes an element
a plausible puzzle target.

Where a reducing agent stops working is the activity series again: a metal above
the threshold holds its oxygen too tightly and its oxide needs electrolysis
instead, which is not a formula-level reaction and stays out of scope. That is
why aluminium is extracted electrolytically and iron is not.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Reducer:
    formula: str  # the species that does the reducing
    oxidised_to: str  # what it becomes, e.g. C -> CO2
    below: str  # works on oxides of metals *below* this one in the series
    name: str


REDUCERS: dict[str, Reducer] = {
    # Carbon reduces everything below aluminium -- this is the blast furnace and
    # zinc smelting. It cannot touch Al2O3 or MgO.
    "C": Reducer("C", "CO2", "Al", "carbon"),
    # Carbon monoxide does the same job at the same reach; in a real furnace it
    # is the species doing most of the work.
    "CO": Reducer("CO", "CO2", "Al", "carbon monoxide"),
    # Hydrogen is the gentler one -- reliable from iron downwards, and the
    # standard classroom demonstration is CuO.
    "H2": Reducer("H2", "H2O", "Zn", "hydrogen"),
}

# Reducing agents deliberately absent, with the reason.
EXCLUDED_REDUCERS: dict[str, str] = {
    "Al": "the aluminothermic reaction is metal + oxide -- see rules.reduction",
    "CH4": "organic, and out of scope",
    "NH3": "reduces CuO, but the nitrogen chemistry that follows is not school-level",
}
