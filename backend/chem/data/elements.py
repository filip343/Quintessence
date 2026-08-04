"""Element classification table: metal / nonmetal, plus the tags it forces.

`IS_METAL` is table 4 of the brief: it decides whether an oxide is basic or
acidic, and whether `metal + nonmetal -> binary salt` applies.

`ELEMENT_NAMES` and `NON_SOLID_ELEMENTS` are display data rather than chemistry:
they exist so a species record can carry a name and a state without any other
table having to know how to spell things.

Two honest caveats are encoded as separate sets rather than fudged into the bool:

- **Metalloids** (B, Si, Ge, As, Sb, Te) are neither. `IS_METAL` assigns each the
  value matching how its oxide behaves in school chemistry (SiO2, B2O3, As2O3 ->
  acidic), so the bool stays usable, and `METALLOIDS` marks them for the
  generator to steer around.
- **Amphoteric-oxide elements** are out of scope for v1 per the brief. They are
  metals in `IS_METAL` (they are), but `AMPHOTERIC_OXIDE_ELEMENTS` tags them so
  oxide rules can skip them. Their *salts* are still fine.
"""

from __future__ import annotations

# Curated to school-relevant elements. Anything absent is deliberately out of
# scope -- `chem.rules.elements.is_metal` raises rather than guessing.
IS_METAL: dict[str, bool] = {
    # period 1
    "H": False,
    "He": False,
    # period 2
    "Li": True,
    "Be": True,
    "B": False,  # metalloid, acidic oxide
    "C": False,
    "N": False,
    "O": False,
    "F": False,
    "Ne": False,
    # period 3
    "Na": True,
    "Mg": True,
    "Al": True,
    "Si": False,  # metalloid, acidic oxide
    "P": False,
    "S": False,
    "Cl": False,
    "Ar": False,
    # period 4
    "K": True,
    "Ca": True,
    "Sc": True,
    "Ti": True,
    "V": True,
    "Cr": True,
    "Mn": True,
    "Fe": True,
    "Co": True,
    "Ni": True,
    "Cu": True,
    "Zn": True,
    "Ga": True,
    "Ge": False,  # metalloid
    "As": False,  # metalloid, acidic oxide
    "Se": False,
    "Br": False,
    "Kr": False,
    # period 5
    "Rb": True,
    "Sr": True,
    "Y": True,
    "Zr": True,
    "Nb": True,
    "Mo": True,
    "Ag": True,
    "Cd": True,
    "In": True,
    "Sn": True,
    "Sb": False,  # metalloid
    "Te": False,  # metalloid
    "I": False,
    "Xe": False,
    # period 6
    "Cs": True,
    "Ba": True,
    "La": True,
    "W": True,
    "Pt": True,
    "Au": True,
    "Hg": True,
    "Tl": True,
    "Pb": True,
    "Bi": True,
    "Rn": False,
    # period 7
    "Ra": True,
}

METALLOIDS: frozenset[str] = frozenset({"B", "Si", "Ge", "As", "Sb", "Te"})

# Elements a school course meets as the free element -- the ones that can be
# dealt in a starting palette without a student blinking. Mn and Sn are absent
# on purpose: their *compounds* are common (KMnO4, tin plating) while the bare
# element is not. See the note on commonness in `chem.data.ions`.
COMMON_ELEMENTS: frozenset[str] = frozenset(
    {
        "H", "C", "N", "O", "S", "P", "Si",
        # F is absent on purpose: fluorides are everyday, fluorine gas is not
        # something to hand a student, and the two are separate tables.
        "Cl", "Br", "I",
        "Li", "Na", "K", "Mg", "Ca", "Ba",
        "Al", "Zn", "Fe", "Cu", "Ag", "Pb", "Cr",
    }
)

NOBLE_GASES: frozenset[str] = frozenset({"He", "Ne", "Ar", "Kr", "Xe", "Rn"})

# Excluded from oxide-based reaction rules in v1 (brief, "Scope"). Cr is listed
# because Cr2O3 is amphoteric -- chromium(VI) chemistry (chromates) is unaffected,
# since `oxide_character` checks oxidation state before this set.
AMPHOTERIC_OXIDE_ELEMENTS: frozenset[str] = frozenset(
    {"Be", "Al", "Zn", "Ga", "Ge", "Sn", "Pb", "Sb", "Cr", "Ti", "In"}
)

HALOGENS: frozenset[str] = frozenset({"F", "Cl", "Br", "I"})

ALKALI_METALS: frozenset[str] = frozenset({"Li", "Na", "K", "Rb", "Cs"})
ALKALINE_EARTH_METALS: frozenset[str] = frozenset({"Be", "Mg", "Ca", "Sr", "Ba", "Ra"})

# How the free element is written as a species. Everything not listed is written
# as the bare symbol -- including S and P, which school chemistry writes as S and
# P rather than S8 and P4.
DIATOMIC_ELEMENTS: dict[str, str] = {
    "H": "H2",
    "N": "N2",
    "O": "O2",
    "F": "F2",
    "Cl": "Cl2",
    "Br": "Br2",
    "I": "I2",
}

ELEMENTAL_FORMULA: dict[str, str] = {
    symbol: DIATOMIC_ELEMENTS.get(symbol, symbol) for symbol in IS_METAL
}

ELEMENT_OF_FORMULA: dict[str, str] = {
    formula: symbol for symbol, formula in ELEMENTAL_FORMULA.items()
}

# --------------------------------------------------------------------------
# Display data
# --------------------------------------------------------------------------

# British spellings, to match the hand-written names in `chem.data.bases`
# ("aluminium hydroxide", "caesium hydroxide"). `chem.validate` asserts this
# table covers every element in `IS_METAL`, so a new element cannot arrive
# nameless.
ELEMENT_NAMES: dict[str, str] = {
    "H": "hydrogen",
    "He": "helium",
    "Li": "lithium",
    "Be": "beryllium",
    "B": "boron",
    "C": "carbon",
    "N": "nitrogen",
    "O": "oxygen",
    "F": "fluorine",
    "Ne": "neon",
    "Na": "sodium",
    "Mg": "magnesium",
    "Al": "aluminium",
    "Si": "silicon",
    "P": "phosphorus",
    "S": "sulfur",
    "Cl": "chlorine",
    "Ar": "argon",
    "K": "potassium",
    "Ca": "calcium",
    "Sc": "scandium",
    "Ti": "titanium",
    "V": "vanadium",
    "Cr": "chromium",
    "Mn": "manganese",
    "Fe": "iron",
    "Co": "cobalt",
    "Ni": "nickel",
    "Cu": "copper",
    "Zn": "zinc",
    "Ga": "gallium",
    "Ge": "germanium",
    "As": "arsenic",
    "Se": "selenium",
    "Br": "bromine",
    "Kr": "krypton",
    "Rb": "rubidium",
    "Sr": "strontium",
    "Y": "yttrium",
    "Zr": "zirconium",
    "Nb": "niobium",
    "Mo": "molybdenum",
    "Ag": "silver",
    "Cd": "cadmium",
    "In": "indium",
    "Sn": "tin",
    "Sb": "antimony",
    "Te": "tellurium",
    "I": "iodine",
    "Xe": "xenon",
    "Cs": "caesium",
    "Ba": "barium",
    "La": "lanthanum",
    "W": "tungsten",
    "Pt": "platinum",
    "Au": "gold",
    "Hg": "mercury",
    "Tl": "thallium",
    "Pb": "lead",
    "Bi": "bismuth",
    "Rn": "radon",
    "Ra": "radium",
}

# State of the free element at room temperature, for the ones that are not
# solid. Keyed by the *species* formula (Br2, not Br), since that is what a
# species record is keyed by. Everything absent is a solid.
NON_SOLID_ELEMENTS: dict[str, str] = {
    "H2": "g",
    "N2": "g",
    "O2": "g",
    "F2": "g",
    "Cl2": "g",
    "He": "g",
    "Ne": "g",
    "Ar": "g",
    "Kr": "g",
    "Xe": "g",
    "Rn": "g",
    "Br2": "l",
    "Hg": "l",
}

# Nonmetals oxidising enough to drive a multi-valent metal to its *highest*
# common state. This is the difference between Fe + Cl2 -> FeCl3 and
# Fe + S -> FeS, and it is a property of the partner, not of the metal.
# Iodine is deliberately absent: Fe + I2 gives FeI2, not FeI3.
OXIDISING_NONMETALS: frozenset[str] = frozenset({"F", "Cl", "Br", "O"})
