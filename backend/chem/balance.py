"""Turn an unbalanced `Reaction` into coefficients, via ChemPy.

This is the one place ChemPy is used, and the one place it should be. The rule
templates decide *what* reacts; this decides *how much*, which is pure linear
algebra over the formulas and needs no chemistry knowledge at all.

Deliberately a separate pass rather than something the templates do:

- A template that produces the wrong species produces a wrong-but-balanceable
  equation just as happily. Balancing is not a correctness check on the
  chemistry, so it should not be able to masquerade as one.
- It costs a sympy solve per reaction. The game needs coefficients for display,
  not for search, so the hypergraph can run without ever calling this.

Per the brief, anything that is not a clean positive integer is **rejected**
rather than rounded or shown parametrically. Underdetermined systems are the
real reason: `balance_stoichiometry` will happily return a family of solutions
in terms of a free symbol, and an equation with an `x` in it is not something to
show a fifteen-year-old.

`Reaction.from_string` is never used -- it calls `eval`, and the brief forbids it
on anything that reaches user input.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from chempy import balance_stoichiometry

from chem.data.ions import CHEMPY_FORMULA_ALIASES
from chem.reaction import Reaction


@dataclass(frozen=True, slots=True)
class BalancedReaction:
    """A reaction plus integer coefficients, keyed by species formula."""

    reaction: Reaction
    reactants: tuple[tuple[int, str], ...]
    products: tuple[tuple[int, str], ...]

    def equation(self) -> str:
        return f"{_side(self.reactants)} -> {_side(self.products)}"

    def __str__(self) -> str:
        note = self.reaction.note
        return self.equation() if not note else f"{self.equation()}   ({note})"


@lru_cache(maxsize=4096)
def balance(reaction: Reaction) -> BalancedReaction | None:
    """Coefficients for a reaction, or None if it will not balance cleanly."""
    result, _ = _balance(reaction)
    return result


def balance_failure(reaction: Reaction) -> str:
    """Why a reaction does not balance. Empty string when it does."""
    _, reason = _balance(reaction)
    return reason


def unbalanceable(reactions: list[Reaction]) -> list[tuple[Reaction, str]]:
    """Every reaction in the list that will not balance, with the reason."""
    failures = []
    for reaction in reactions:
        result, reason = _balance(reaction)
        if result is None:
            failures.append((reaction, reason))
    return failures


# --------------------------------------------------------------------------
# Internals
# --------------------------------------------------------------------------


def _balance(reaction: Reaction) -> tuple[BalancedReaction | None, str]:
    reactants, products = reaction.reactants, reaction.products
    if len(set(reactants)) != len(reactants) or len(set(products)) != len(products):
        return None, "a species appears twice on the same side"
    overlap = set(reactants) & set(products)
    if overlap:
        return None, f"{sorted(overlap)} appears on both sides"

    left = {_chempy(f): f for f in reactants}
    right = {_chempy(f): f for f in products}

    try:
        # underdetermined=None makes ChemPy raise rather than hand back a
        # solution in terms of a free symbol
        solved_left, solved_right = balance_stoichiometry(
            set(left), set(right), underdetermined=None
        )
    except Exception as error:  # ChemPy raises several unrelated types
        return None, f"{type(error).__name__}: {error}"

    try:
        coefficients_left = _integers(solved_left, left)
        coefficients_right = _integers(solved_right, right)
    except ValueError as error:
        return None, str(error)

    return (
        BalancedReaction(
            reaction=reaction,
            reactants=tuple(coefficients_left[f] for f in reactants),
            products=tuple(coefficients_right[f] for f in products),
        ),
        "",
    )


def _integers(
    solved: dict[str, object], names: dict[str, str]
) -> dict[str, tuple[int, str]]:
    """Check every coefficient is a clean positive integer, and map back to ours."""
    out: dict[str, tuple[int, str]] = {}
    for chempy_formula, coefficient in solved.items():
        original = names[chempy_formula]
        try:
            value = int(coefficient)
        except (TypeError, ValueError):
            raise ValueError(
                f"{original}: coefficient {coefficient} is not an integer"
            ) from None
        if value != coefficient:
            raise ValueError(f"{original}: coefficient {coefficient} is not an integer")
        if value <= 0:
            raise ValueError(f"{original}: coefficient {value} is not positive")
        out[original] = (value, original)
    return out


def _chempy(formula: str) -> str:
    """Our display formula in the notation ChemPy parses, if they differ."""
    return CHEMPY_FORMULA_ALIASES.get(formula, formula)


def _side(terms: tuple[tuple[int, str], ...]) -> str:
    return " + ".join(formula if n == 1 else f"{n} {formula}" for n, formula in terms)
