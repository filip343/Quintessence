"""Acid table (brief, table 6) -- keyed by anion, because the anion *is* the acid.

No acid formula is written down here. Each record names an anion, and the formula
is criss-cross of H+ with it (`SO4-2` -> `H2SO4`), computed at import into
`ACID_FORMULAS` / `ACIDS_BY_FORMULA`. That keeps this table a join over
`POLYATOMIC_IONS` and `ANHYDRIDES` rather than a third list to keep in sync: if an
anion is in `ANHYDRIDES`, its acid is reachable by hydration; if it is not, the
acid is a hydracid and comes from `H2 + nonmetal`.

`strength` gates displacement -- a stronger acid drives a weaker one out of its
salt. `decomposes_to` is the brief's unstable-products table for acids: H2CO3 and
H2SO3 are real products of a real reaction that simply do not survive.
"""

from __future__ import annotations

from dataclasses import dataclass

from chem.data.ions import POLYATOMIC_IONS
from chem.data.strength import Strength
from chem.formulas import criss_cross, ion_formula, parse_charge, strip_charge


@dataclass(frozen=True, slots=True)
class Acid:
    anion: str  # the acid's conjugate base, e.g. "SO4-2"
    name: str
    strength: Strength
    # Products it falls apart into, if it does not survive in solution. Empty
    # means stable.
    decomposes_to: tuple[str, ...] = ()
    common: bool = True

    @property
    def stable(self) -> bool:
        return not self.decomposes_to


_STRONG = Strength.STRONG
_MODERATE = Strength.MODERATE
_WEAK = Strength.WEAK
_VERY_WEAK = Strength.VERY_WEAK

ACIDS: dict[str, Acid] = {
    # --- hydracids: no anhydride, made from H2 + nonmetal ---
    "Cl-": Acid("Cl-", "hydrochloric acid", _STRONG),
    "Br-": Acid("Br-", "hydrobromic acid", _STRONG, common=False),
    "I-": Acid("I-", "hydroiodic acid", _STRONG, common=False),
    "F-": Acid("F-", "hydrofluoric acid", _WEAK, common=False),
    "S-2": Acid("S-2", "hydrosulfuric acid", _WEAK),
    "CN-": Acid("CN-", "hydrocyanic acid", _VERY_WEAK, common=False),
    # --- oxyacids of the common nonmetals ---
    "NO3-": Acid("NO3-", "nitric acid", _STRONG),
    "NO2-": Acid("NO2-", "nitrous acid", _WEAK, common=False),
    "SO4-2": Acid("SO4-2", "sulfuric acid", _STRONG),
    "SO3-2": Acid("SO3-2", "sulfurous acid", _WEAK, decomposes_to=("SO2", "H2O")),
    "CO3-2": Acid("CO3-2", "carbonic acid", _WEAK, decomposes_to=("CO2", "H2O")),
    "PO4-3": Acid("PO4-3", "phosphoric acid", _MODERATE),
    "PO3-3": Acid("PO3-3", "phosphorous acid", _MODERATE, common=False),
    "SiO3-2": Acid("SiO3-2", "silicic acid", _VERY_WEAK),
    # --- boron, arsenic, selenium: uncommon, but they give B/As/Se a chemistry ---
    "BO3-3": Acid("BO3-3", "boric acid", _VERY_WEAK, common=False),
    "AsO4-3": Acid("AsO4-3", "arsenic acid", _MODERATE, common=False),
    "AsO3-3": Acid("AsO3-3", "arsenous acid", _WEAK, common=False),
    "SeO4-2": Acid("SeO4-2", "selenic acid", _STRONG, common=False),
    "SeO3-2": Acid("SeO3-2", "selenous acid", _WEAK, common=False),
    "S2O3-2": Acid(
        "S2O3-2", "thiosulfuric acid", _WEAK, decomposes_to=("S", "SO2", "H2O"), common=False
    ),
    # --- halogen oxyacids ---
    "ClO-": Acid("ClO-", "hypochlorous acid", _WEAK, common=False),
    "ClO2-": Acid("ClO2-", "chlorous acid", _WEAK, common=False),
    "ClO3-": Acid("ClO3-", "chloric acid", _STRONG, common=False),
    "ClO4-": Acid("ClO4-", "perchloric acid", _STRONG, common=False),
    "BrO3-": Acid("BrO3-", "bromic acid", _STRONG, common=False),
    "IO3-": Acid("IO3-", "iodic acid", _STRONG, common=False),
    # --- oxyacids of high-valent metals ---
    "MnO4-": Acid("MnO4-", "permanganic acid", _STRONG, common=False),
    "CrO4-2": Acid("CrO4-2", "chromic acid", _MODERATE, common=False),
    "Cr2O7-2": Acid("Cr2O7-2", "dichromic acid", _STRONG, common=False),
    # --- carboxylic acids that school inorganic chemistry still uses ---
    "CH3COO-": Acid("CH3COO-", "acetic acid", _WEAK),
    "C2O4-2": Acid("C2O4-2", "oxalic acid", _MODERATE, common=False),
}

# Acids whose conventional formula is not the criss-cross. Only carboxylic acids
# need this -- the acidic hydrogen is written last.
ACID_FORMULA_OVERRIDES: dict[str, str] = {
    "CH3COO-": "CH3COOH",
}

# Anions whose acid deliberately has no record, with the reason.
EXCLUDED_ACIDS: dict[str, str] = {
    "HSO4-": "an acid salt anion, not an acid in its own right",
    "HSO3-": "an acid salt anion, not an acid in its own right",
    "HCO3-": "an acid salt anion, not an acid in its own right",
    "HS-": "an acid salt anion, not an acid in its own right",
    "H2PO4-": "an acid salt anion, not an acid in its own right",
    "HPO4-2": "an acid salt anion, not an acid in its own right",
    "SCN-": "thiocyanic acid is not school-level",
    "OH-": "water is the acid of hydroxide; handled as its own species",
}


def _formula_of(acid: Acid) -> str:
    override = ACID_FORMULA_OVERRIDES.get(acid.anion)
    if override is not None:
        return override
    return criss_cross("H", 1, strip_charge(acid.anion), parse_charge(acid.anion))


ACID_FORMULAS: dict[str, str] = {anion: _formula_of(acid) for anion, acid in ACIDS.items()}

ACIDS_BY_FORMULA: dict[str, Acid] = {
    formula: ACIDS[anion] for anion, formula in ACID_FORMULAS.items()
}

# Number of acidic hydrogens, straight off the anion's charge.
PROTON_COUNT: dict[str, int] = {anion: -parse_charge(anion) for anion in ACIDS}

# Nonmetals that combine with hydrogen to give an acid directly. N gives ammonia
# (a base) and C gives methane (neither), so the rule cannot be "any nonmetal".
HYDRACID_ELEMENTS: frozenset[str] = frozenset({"F", "Cl", "Br", "I", "S"})


# --------------------------------------------------------------------------
# Acid salts
# --------------------------------------------------------------------------


def _acid_salt_anions() -> dict[str, tuple[str, ...]]:
    """Parent anion -> its partially protonated forms, fewest protons first.

    Derived, not curated. For every acid with more than one proton, put the
    protons back on one at a time and keep whatever `POLYATOMIC_IONS` already
    has a record for. That makes the ion table the gate: HCO3- and HSO4- are
    curated so they appear, while HCrO4- and HSeO4- are not curated so they do
    not -- which is the right answer, since those are not salts a school course
    ever isolates.

    The charge falls out of the arithmetic: adding a proton to PO4-3 gives
    HPO4-2, adding another gives H2PO4-. `chem.validate` re-derives it.
    """
    table: dict[str, tuple[str, ...]] = {}
    for anion in ACIDS:
        charge = parse_charge(anion)
        protons = -charge
        if protons < 2:
            continue
        core = strip_charge(anion)
        found = [
            candidate
            for added in range(1, protons)
            if (
                candidate := ion_formula(
                    f"H{added if added > 1 else ''}{core}", charge + added
                )
            )
            in POLYATOMIC_IONS
        ]
        if found:
            table[anion] = tuple(found)
    return table


# CO3-2 -> (HCO3-,), PO4-3 -> (HPO4-2, H2PO4-), and so on.
ACID_SALT_ANIONS: dict[str, tuple[str, ...]] = _acid_salt_anions()

# The reverse: HCO3- -> CO3-2. This is what lets an acid salt behave like the
# salt of its parent acid without a second table of rules.
PARENT_ANION: dict[str, str] = {
    partial: parent for parent, group in ACID_SALT_ANIONS.items() for partial in group
}

ACID_SALT_ANION_SET: frozenset[str] = frozenset(PARENT_ANION)

# Acids that do NOT give hydrogen with a metal, however active the metal is.
# Nitric acid oxidises instead, giving NO or NO2 depending on concentration --
# outside the scope of a formula-level engine, so `metal + acid` skips them.
NON_HYDROGEN_ACIDS: frozenset[str] = frozenset({"HNO3", "HNO2"})
