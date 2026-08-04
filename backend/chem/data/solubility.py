"""Solubility table (brief, table 2) -- gates double displacement.

Stored anion-major with per-cation exceptions, which is how the chemistry
actually factors: the anion sets the default and a short list of cations breaks
it. A flat (cation, anion) grid would be ~500 cells, most of them repeats. The
lookup that walks these rules lives in `chem.rules.solubility`.

`SLIGHTLY_SOLUBLE` is a distinct value rather than being folded into one side.
It exists so the generator can *avoid* the judgement calls (CaSO4, PbCl2,
Ca(OH)2) instead of committing a puzzle to one reading of them. Only
`INSOLUBLE` is a guaranteed precipitate for a par-path step.

Oxides are absent on purpose: O-2 has no solubility, it reacts with water. That
is the `basic oxide + water -> base` template, not this table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class Solubility(Enum):
    SOLUBLE = "soluble"
    SLIGHTLY_SOLUBLE = "slightly soluble"
    INSOLUBLE = "insoluble"
    UNKNOWN = "unknown"

    @property
    def precipitates(self) -> bool:
        """Forms a visible precipitate. Includes the slightly-soluble middle."""
        return self in (Solubility.INSOLUBLE, Solubility.SLIGHTLY_SOLUBLE)

    @property
    def certainly_precipitates(self) -> bool:
        """Safe to build a puzzle step on -- no textbook disagrees."""
        return self is Solubility.INSOLUBLE


_S = Solubility.SOLUBLE
_SS = Solubility.SLIGHTLY_SOLUBLE
_I = Solubility.INSOLUBLE


@dataclass(frozen=True, slots=True)
class AnionRule:
    default: Solubility
    exceptions: Mapping[str, Solubility] = field(default_factory=dict)


# Salts of these cations dissolve regardless of anion (Li is the usual offender
# and is handled by per-anion exceptions below).
ALWAYS_SOLUBLE_CATIONS: frozenset[str] = frozenset(
    {"Li+", "Na+", "K+", "Rb+", "Cs+", "NH4+", "H+", "H3O+"}
)

ANION_RULES: dict[str, AnionRule] = {
    # --- anions whose salts are essentially all soluble ---
    "NO3-": AnionRule(_S),
    "NO2-": AnionRule(_S, {"Ag+": _SS}),
    "ClO3-": AnionRule(_S),
    "ClO4-": AnionRule(_S, {"K+": _SS, "Rb+": _SS, "Cs+": _SS}),
    "ClO-": AnionRule(_S),
    "ClO2-": AnionRule(_S, {"Ag+": _SS}),
    "HSO3-": AnionRule(_S),
    "MnO4-": AnionRule(_S),
    "HCO3-": AnionRule(_S),
    "HSO4-": AnionRule(_S),
    "H2PO4-": AnionRule(_S),
    "HS-": AnionRule(_S),
    "CH3COO-": AnionRule(_S, {"Ag+": _SS, "Hg2+2": _SS}),
    "SCN-": AnionRule(_S, {"Ag+": _I, "Cu+": _I, "Hg+2": _I, "Pb+2": _SS}),
    "Cr2O7-2": AnionRule(_S, {"Ag+": _I, "Pb+2": _I, "Ba+2": _SS}),
    # --- halides: soluble but for the classic silver/lead/mercury(I) trio ---
    "F-": AnionRule(
        _S,
        {
            "Li+": _SS,
            "Mg+2": _I,
            "Ca+2": _I,
            "Sr+2": _I,
            "Ba+2": _SS,
            "Pb+2": _SS,
        },
    ),
    "Cl-": AnionRule(_S, {"Ag+": _I, "Cu+": _I, "Hg2+2": _I, "Pb+2": _SS}),
    "Br-": AnionRule(_S, {"Ag+": _I, "Cu+": _I, "Hg2+2": _I, "Pb+2": _SS}),
    "I-": AnionRule(_S, {"Ag+": _I, "Cu+": _I, "Hg2+2": _I, "Hg+2": _I, "Pb+2": _I}),
    # --- sulfate: the barium test ---
    "SO4-2": AnionRule(
        _S,
        {
            "Ba+2": _I,
            "Sr+2": _I,
            "Pb+2": _I,
            "Ca+2": _SS,
            "Ag+": _SS,
            "Hg2+2": _SS,
        },
    ),
    # --- anions whose salts are mostly insoluble ---
    "OH-": AnionRule(_I, {"Ba+2": _S, "Sr+2": _SS, "Ca+2": _SS}),
    "CO3-2": AnionRule(_I, {"Li+": _SS}),
    "SO3-2": AnionRule(_I),
    "S-2": AnionRule(_I, {"Mg+2": _S, "Ca+2": _SS, "Sr+2": _SS, "Ba+2": _S}),
    "PO4-3": AnionRule(_I),
    "HPO4-2": AnionRule(_I),
    "PO3-3": AnionRule(_I),
    "SiO3-2": AnionRule(_I),
    # borate, arsenate and arsenite follow phosphate; selenate follows sulfate
    # (including the barium test) and selenite follows sulfite
    "BO3-3": AnionRule(_I),
    "AsO4-3": AnionRule(_I),
    "AsO3-3": AnionRule(_I),
    "SeO3-2": AnionRule(_I),
    "SeO4-2": AnionRule(
        _S,
        {
            "Ba+2": _I,
            "Sr+2": _I,
            "Pb+2": _I,
            "Ca+2": _SS,
            "Ag+": _SS,
        },
    ),
    "CrO4-2": AnionRule(_I, {"Mg+2": _S, "Ca+2": _SS}),
    "C2O4-2": AnionRule(_I, {"Mg+2": _SS}),
    "CN-": AnionRule(_I),
    "S2O3-2": AnionRule(_I, {"Mg+2": _S, "Ca+2": _S, "Sr+2": _SS, "Ba+2": _SS}),
    "IO3-": AnionRule(_SS, {"Ag+": _I, "Ba+2": _SS, "Pb+2": _I}),
    "BrO3-": AnionRule(_S, {"Ag+": _I, "Ba+2": _SS, "Pb+2": _SS}),
}

# Pairs the anion rules get wrong. Mercury(II) halides are molecular rather than
# ionic, so the halide rule does not describe them.
SOLUBILITY_OVERRIDES: dict[tuple[str, str], Solubility] = {
    ("Hg+2", "Cl-"): _S,  # HgCl2 is molecular and dissolves
    ("Hg+2", "Br-"): _SS,
    ("Ca+2", "OH-"): _SS,  # limewater -- sparingly soluble, not a precipitate
}

# Anions that never appear in aqueous solution, so the table owes them no rule:
# oxides, hydrides, nitrides, phosphides, carbides, selenides.
NON_AQUEOUS_ANIONS: frozenset[str] = frozenset({"O-2", "H-", "N-3", "P-3", "Se-2"})
