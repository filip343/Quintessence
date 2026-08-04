"""Ion lookups over `chem.data.ions`."""

from __future__ import annotations

from chem.data.ions import (
    ANION_CHARGES,
    ANION_FORMULAS,
    CATION_CHARGES,
    CATION_FORMULAS,
    POLYATOMIC_IONS,
)
from chem.formulas import parse_charge


def charge_of(formula: str) -> int:
    """Charge of any curated ion, monatomic or polyatomic."""
    ion = POLYATOMIC_IONS.get(formula)
    if ion is not None:
        return ion.charge
    charge = parse_charge(formula)
    if charge == 0:
        raise KeyError(f"{formula!r} is not a curated ion")
    return charge


def default_cation_charge(symbol: str) -> int:
    """The charge to assume for a metal when the puzzle does not say otherwise."""
    return CATION_CHARGES[symbol][0]


def default_anion_charge(symbol: str) -> int:
    return ANION_CHARGES[symbol][0]


def is_cation(formula: str) -> bool:
    return formula in CATION_FORMULAS


def is_anion(formula: str) -> bool:
    return formula in ANION_FORMULAS


def ion_name(formula: str) -> str | None:
    """Display name, for polyatomic ions only -- monatomic ones are named later."""
    ion = POLYATOMIC_IONS.get(formula)
    return None if ion is None else ion.name
