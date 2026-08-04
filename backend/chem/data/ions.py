"""Ion charges and valences -- the backbone table (brief, table 1).

Three distinct things live here, because they answer three different questions:

- `CATION_CHARGES` / `ANION_CHARGES` -- what charge does a *monatomic ion* carry?
  Used for criss-cross salt building (Ca(+2) + PO4(-3) -> Ca3(PO4)2).
- `POLYATOMIC_IONS` -- the ~30 curated many-atom ions, with charge and name.
- `POSITIVE_OXIDATION_STATES` -- what positive oxidation states does an element
  show in *oxides and oxyacids*? Not the same table: Mn is only ever a 2+ cation
  in salts, but MnO2 and Mn2O7 need +4 and +7.

Formula notation is ChemPy's (see `chem.formulas`). Keys are meant to be handed
straight to `Substance.from_formula`.

Charge tuples are ordered **most common first**: the puzzle generator should
default to element 0 and treat later entries as deliberate variants.
"""

from __future__ import annotations

from dataclasses import dataclass

from chem.formulas import ion_formula


@dataclass(frozen=True, slots=True)
class Ion:
    formula: str  # ChemPy-parsable, e.g. "SO4-2"
    charge: int
    name: str


# --------------------------------------------------------------------------
# Monatomic ions
# --------------------------------------------------------------------------

# Curated to elements that form school-relevant salts. Metals in the activity
# series but with no everyday salt chemistry (Pt, Au, W, Mo) are deliberately
# absent so the generator cannot invent PtCl2 puzzles.
CATION_CHARGES: dict[str, tuple[int, ...]] = {
    "H": (1,),
    # group 1
    "Li": (1,),
    "Na": (1,),
    "K": (1,),
    "Rb": (1,),
    "Cs": (1,),
    # group 2
    "Be": (2,),
    "Mg": (2,),
    "Ca": (2,),
    "Sr": (2,),
    "Ba": (2,),
    # group 13 / post-transition
    "Al": (3,),
    "Ga": (3,),
    "Sn": (2, 4),
    # Pb(IV) is absent as a *cation*: PbCl4 decomposes and Pb(IV) salts are not
    # school chemistry. PbO2 still exists -- that lives in the oxidation states.
    "Pb": (2,),
    "Bi": (3,),
    # transition metals. Cr(II), Mn(III) and Co(III) are omitted: real, but not
    # stable enough in solution to build a school-level salt puzzle on.
    "Cr": (3,),
    "Mn": (2,),
    "Fe": (2, 3),
    "Co": (2,),
    "Ni": (2,),
    "Cu": (2, 1),
    "Zn": (2,),
    "Ag": (1,),
    "Cd": (2,),
    "Hg": (2,),  # mercury(I) is the diatomic Hg2+2 -- see POLYATOMIC_IONS
}

ANION_CHARGES: dict[str, tuple[int, ...]] = {
    "H": (-1,),  # hydrides: NaH, CaH2
    "F": (-1,),
    "Cl": (-1,),
    "Br": (-1,),
    "I": (-1,),
    "O": (-2,),
    "S": (-2,),
    "Se": (-2,),
    "N": (-3,),  # nitrides: Mg3N2
    "P": (-3,),  # phosphides: Ca3P2
    # Carbide is absent: the real product of metal + carbon is CaC2, whose anion
    # is C2-2, not C-4. Rather than model acetylides, we leave carbon out.
}

# Positive oxidation states as shown in oxides and oxyacids. For fixed-valence
# metals this repeats CATION_CHARGES on purpose -- one table to consult when
# building an oxide formula. `chem.validate` asserts the two agree.
POSITIVE_OXIDATION_STATES: dict[str, tuple[int, ...]] = {
    "H": (1,),
    # nonmetals and metalloids
    "B": (3,),
    "C": (4, 2),
    "N": (5, 4, 3, 2, 1),
    "Si": (4,),
    "P": (5, 3),
    "S": (6, 4),
    "Se": (6, 4),
    "As": (5, 3),
    "Cl": (7, 5, 3, 1),
    "Br": (7, 5, 1),
    "I": (7, 5, 1),
    # metals -- higher states here than in CATION_CHARGES where oxides need them
    "Li": (1,),
    "Na": (1,),
    "K": (1,),
    "Rb": (1,),
    "Cs": (1,),
    "Be": (2,),
    "Mg": (2,),
    "Ca": (2,),
    "Sr": (2,),
    "Ba": (2,),
    "Al": (3,),
    "Ga": (3,),
    "Sn": (4, 2),
    "Pb": (2, 4),
    "Bi": (3, 5),
    "Cr": (3, 6, 2),  # Cr2O3 amphoteric, CrO3 acidic
    "Mn": (4, 2, 3, 7, 6),  # MnO2, MnO, Mn2O3, Mn2O7
    "Fe": (3, 2),
    "Co": (2, 3),
    "Ni": (2,),
    "Cu": (2, 1),
    "Zn": (2,),
    "Ag": (1,),
    "Cd": (2,),
    "Hg": (2, 1),
}


# --------------------------------------------------------------------------
# Polyatomic ions
# --------------------------------------------------------------------------

POLYATOMIC_IONS: dict[str, Ion] = {
    # cations
    "NH4+": Ion("NH4+", 1, "ammonium"),
    "H3O+": Ion("H3O+", 1, "oxonium"),
    "Hg2+2": Ion("Hg2+2", 2, "mercury(I)"),
    # anions -- hydroxide and the oxyanions
    "OH-": Ion("OH-", -1, "hydroxide"),
    "NO3-": Ion("NO3-", -1, "nitrate"),
    "NO2-": Ion("NO2-", -1, "nitrite"),
    "CO3-2": Ion("CO3-2", -2, "carbonate"),
    "HCO3-": Ion("HCO3-", -1, "hydrogencarbonate"),
    "SO4-2": Ion("SO4-2", -2, "sulfate"),
    "HSO4-": Ion("HSO4-", -1, "hydrogensulfate"),
    "SO3-2": Ion("SO3-2", -2, "sulfite"),
    "HSO3-": Ion("HSO3-", -1, "hydrogensulfite"),
    "S2O3-2": Ion("S2O3-2", -2, "thiosulfate"),
    "HS-": Ion("HS-", -1, "hydrogensulfide"),
    "PO4-3": Ion("PO4-3", -3, "phosphate"),
    "HPO4-2": Ion("HPO4-2", -2, "hydrogenphosphate"),
    "H2PO4-": Ion("H2PO4-", -1, "dihydrogenphosphate"),
    "PO3-3": Ion("PO3-3", -3, "phosphite"),
    "SiO3-2": Ion("SiO3-2", -2, "silicate"),
    # Boron, arsenic and selenium had oxides but no anions, which left them with
    # nothing to do but burn. These are the ions `EXCLUDED_OXIDES` was waiting on.
    "BO3-3": Ion("BO3-3", -3, "borate"),
    "AsO4-3": Ion("AsO4-3", -3, "arsenate"),
    "AsO3-3": Ion("AsO3-3", -3, "arsenite"),
    "SeO4-2": Ion("SeO4-2", -2, "selenate"),
    "SeO3-2": Ion("SeO3-2", -2, "selenite"),
    "ClO-": Ion("ClO-", -1, "hypochlorite"),
    "ClO2-": Ion("ClO2-", -1, "chlorite"),
    "ClO3-": Ion("ClO3-", -1, "chlorate"),
    "ClO4-": Ion("ClO4-", -1, "perchlorate"),
    "BrO3-": Ion("BrO3-", -1, "bromate"),
    "IO3-": Ion("IO3-", -1, "iodate"),
    "MnO4-": Ion("MnO4-", -1, "permanganate"),
    # manganate MnO4-2 is deliberately absent: it is marginal chemistry, and it
    # is the only ion that makes salt formulas ambiguous (CuMnO4 would be both
    # Cu+2 + MnO4-2 and Cu+ + MnO4-, breaking the formula -> ions index).
    "CrO4-2": Ion("CrO4-2", -2, "chromate"),
    "Cr2O7-2": Ion("Cr2O7-2", -2, "dichromate"),
    "CN-": Ion("CN-", -1, "cyanide"),
    "SCN-": Ion("SCN-", -1, "thiocyanate"),
    "CH3COO-": Ion("CH3COO-", -1, "acetate"),
    "C2O4-2": Ion("C2O4-2", -2, "oxalate"),
}

# --------------------------------------------------------------------------
# Commonness
# --------------------------------------------------------------------------
#
# Which ions a school course actually uses. The other tables carry `common` on
# their records; ions could not, because they are plain dicts, and salts had no
# way to inherit it -- which is how `Cu(HS)2` and `Cu2SO4` ended up looking like
# legitimate answers alongside `CuO + H2SO4`.
#
# Positive lists rather than exclusions, because roughly half of each table is
# uncommon and a reader needs to see the short list, not reconstruct it. These
# are a judgement call about syllabus coverage, not about chemistry: everything
# absent is still real, still reachable, and still correct if a player finds it.
# `chem.difficulty` uses them to grade a target, so widening either set makes
# more compounds playable rather than making anything true or false.

COMMON_CATIONS: frozenset[str] = frozenset(
    {
        "H+",
        # group 1 and 2 that every course uses; Rb, Cs, Sr, Be are not
        "Li+",
        "Na+",
        "K+",
        "Mg+2",
        "Ca+2",
        "Ba+2",
        "NH4+",
        # the transition and post-transition metals with named salts
        "Al+3",
        "Zn+2",
        "Fe+2",
        "Fe+3",
        "Cu+2",  # copper(I) salts are not school chemistry
        "Cr+3",
        "Ag+",
        "Pb+2",
    }
)

COMMON_ANIONS: frozenset[str] = frozenset(
    {
        # halides and the other simple ones
        "F-",
        "Cl-",
        "Br-",
        "I-",
        "O-2",
        "S-2",
        "OH-",
        # the oxyanions a course names
        "NO3-",
        "SO4-2",
        "SO3-2",
        "CO3-2",
        "PO4-3",
        "SiO3-2",
        "CrO4-2",
        "Cr2O7-2",
        "MnO4-",
        "CH3COO-",
        # bleach and the classic school oxidant. Common only because
        # `chem.rules.disproportionation` gives them a route in from Cl2 + alkali
        # -- before that template existed the whole branch could only be entered
        # from inside itself, so marking them common would have meant nothing.
        "ClO-",
        "ClO3-",
        # acid-salt anions that are themselves household or syllabus items:
        # baking soda, sodium hydrogensulfate, the phosphate series
        "HCO3-",
        "HSO4-",
        "HPO4-2",
        "H2PO4-",
    }
)

# Names of the monatomic anions. Curated rather than stemmed, because the stems
# are irregular in exactly the cases that matter: sulfur -> sulfide, phosphorus
# -> phosphide, oxygen -> oxide. Cations need no such table -- a metal cation is
# named after its element, with a roman numeral when the element is multivalent.
MONATOMIC_ANION_NAMES: dict[str, str] = {
    "H-": "hydride",
    "F-": "fluoride",
    "Cl-": "chloride",
    "Br-": "bromide",
    "I-": "iodide",
    "O-2": "oxide",
    "S-2": "sulfide",
    "Se-2": "selenide",
    "N-3": "nitride",
    "P-3": "phosphide",
}

# Display-canonical formulas that ChemPy may not parse as written. Resolve
# through this before calling `Substance.from_formula`.
CHEMPY_FORMULA_ALIASES: dict[str, str] = {
    "CH3COO-": "C2H3O2-",
}


# --------------------------------------------------------------------------
# Derived sets
# --------------------------------------------------------------------------

CATION_FORMULAS: frozenset[str] = frozenset(
    [ion_formula(symbol, charge) for symbol, charges in CATION_CHARGES.items() for charge in charges]
    + [f for f, ion in POLYATOMIC_IONS.items() if ion.charge > 0]
)

ANION_FORMULAS: frozenset[str] = frozenset(
    [ion_formula(symbol, charge) for symbol, charges in ANION_CHARGES.items() for charge in charges]
    + [f for f, ion in POLYATOMIC_IONS.items() if ion.charge < 0]
)
