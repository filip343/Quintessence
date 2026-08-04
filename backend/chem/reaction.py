"""The reaction record produced by every rule template.

Formula-level and **unbalanced**: reactants and products are species formulas,
with no coefficients. Balancing is a separate step -- ChemPy's
`balance_stoichiometry` over these formulas -- and a reaction whose coefficients
do not come out as clean positive integers is meant to be rejected there rather
than prevented here.

`template` names the rule that fired, so the UI can explain a move and the
generator can reason about which templates a puzzle exercises.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Reaction:
    reactants: tuple[str, ...]
    products: tuple[str, ...]
    template: str
    note: str = ""

    @property
    def product(self) -> str:
        """The single product a puzzle move adds to the inventory."""
        return self.products[0]

    def equation(self) -> str:
        return f"{' + '.join(self.reactants)} -> {' + '.join(self.products)}"

    def __str__(self) -> str:
        return self.equation() if not self.note else f"{self.equation()}   ({self.note})"
