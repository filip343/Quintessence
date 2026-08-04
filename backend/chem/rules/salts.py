"""Every route to a salt.

    neutralise()             acid + base -> salt + water
    acid_with_basic_oxide()  acid + basic oxide -> salt + water
    base_with_acidic_oxide() base + acidic oxide -> salt + water
    oxide_with_oxide()       basic oxide + acidic oxide -> salt
    metal_with_nonmetal()    metal + nonmetal -> binary salt
    metal_with_acid()        metal + acid -> salt + hydrogen
    double_displacement()    salt + salt -> salt + precipitate
    metal_with_salt()        metal + salt -> salt + metal
    halogen_with_salt()      halogen + halide -> halide + halogen
    decompose_carbonate()    carbonate --heat--> basic oxide + CO2

**Normal salts only.** H2SO4 + NaOH gives Na2SO4, never NaHSO4: acid salts would
double the product space for very little puzzle value.

Four gates carry the chemistry, and each is a judgement worth stating:

- *Which charge does a multi-valent metal take?* The partner decides.
  `OXIDISING_NONMETALS` (F, Cl, Br, O) drive it to its highest common state --
  Fe + Cl2 -> FeCl3 -- while sulfur, iodine and acids leave it at its usual one:
  Fe + S -> FeS, Fe + HCl -> FeCl2.
- *Does double displacement need a precipitate?* Yes. Without one nothing
  happens; mixing NaCl and KNO3 solutions gives a mixture, not a reaction. The
  gate is `certainly_precipitates`, so the ambiguous middle band (CaSO4, PbCl2)
  never carries a puzzle step.
- *Which acids give hydrogen with a metal?* Not nitric: it oxidises instead.
  `NON_HYDROGEN_ACIDS` keeps `metal + acid` honest.
- *Which halogen displaces which?* Group order, `HALOGEN_ACTIVITY` -- the
  nonmetal counterpart of the activity series. Fluorine ranks first but never
  attacks: it oxidises the water before it reaches the salt.
"""

from __future__ import annotations

from chem.data.acids import (
    ACID_SALT_ANIONS,
    ACIDS_BY_FORMULA,
    NON_HYDROGEN_ACIDS,
    PARENT_ANION,
)
from chem.data.bases import BASES_BY_FORMULA
from chem.data.elements import ELEMENTAL_FORMULA, OXIDISING_NONMETALS
from chem.data.ions import ANION_CHARGES, CATION_CHARGES
from chem.data.oxides import ANHYDRIDES, WATER, OxideCharacter
from chem.data.salts import OXIDE_IONS, SALT_IONS
from chem.data.solubility import Solubility
from chem.data.strength import Strength
from chem.formulas import criss_cross, ion_formula, parse_charge, strip_charge
from chem.reaction import Reaction
from chem.data.activity import HALOGEN_RANK, NON_DISPLACING_HALOGENS
from chem.rules.activity import displaces_hydrogen_from_acid, is_more_active, reacts_with_cold_water
from chem.rules.elements import is_metal
from chem.rules.ions import charge_of
from chem.rules.oxides import oxide_character
from chem.rules.solubility import certainly_precipitates, solubility

NEUTRALISATION = "acid + base -> salt + water"
ACID_WITH_OXIDE = "acid + basic oxide -> salt + water"
BASE_WITH_OXIDE = "base + acidic oxide -> salt + water"
OXIDE_WITH_OXIDE = "basic oxide + acidic oxide -> salt"
SYNTHESIS = "metal + nonmetal -> binary salt"
METAL_WITH_ACID = "metal + acid -> salt + hydrogen"
DOUBLE_DISPLACEMENT = "salt + salt -> salt + precipitate"
METAL_WITH_SALT = "metal + salt -> salt + metal"
HALOGEN_DISPLACEMENT = "halogen + halide -> halide + halogen"
ACID_SALT_NEUTRALISATION = "acid + base -> acid salt + water"
SALT_WITH_PARENT_ACID = "normal salt + its own acid -> acid salt"
ACID_SALT_WITH_BASE = "acid salt + base -> normal salt + water"
HYDROGENCARBONATE_DECOMPOSITION = "hydrogencarbonate --heat--> carbonate + CO2 + water"
CARBONATE_DECOMPOSITION = "carbonate --heat--> basic oxide + carbon dioxide"

HYDROGEN: str = ELEMENTAL_FORMULA["H"]
CARBONATE: str = "CO3-2"
HYDROGENCARBONATE: str = "HCO3-"
CARBON_DIOXIDE: str = "CO2"


# --------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------


def salt_formula(cation: str, anion: str) -> str | None:
    """Criss-cross two ion formulas into a salt: ("Ca+2", "PO4-3") -> "Ca3(PO4)2"."""
    try:
        cation_charge = charge_of(cation)
        anion_charge = charge_of(anion)
    except KeyError:
        return None
    if cation_charge <= 0 or anion_charge >= 0:
        return None
    return criss_cross(strip_charge(cation), cation_charge, strip_charge(anion), anion_charge)


def hydroxide_formula(cation: str) -> str | None:
    """The base of a cation: "Ca+2" -> "Ca(OH)2"."""
    return salt_formula(cation, "OH-")


def oxide_of_cation(cation: str) -> str | None:
    """The oxide of a cation: "Al+3" -> "Al2O3"."""
    charge = parse_charge(cation)
    if charge <= 0:
        return None
    return criss_cross(strip_charge(cation), charge, "O", -2)


def ions_of(salt: str) -> tuple[str, str] | None:
    """Take a salt formula apart: "Na2CO3" -> ("Na+", "CO3-2")."""
    return SALT_IONS.get(salt)


def is_salt(formula: str) -> bool:
    return formula in SALT_IONS


def cation_charge_for(metal: str, partner: str) -> int | None:
    """Which charge a metal takes, given what it is reacting with.

    An oxidising partner (F, Cl, Br, O) takes a multi-valent metal to its highest
    common state; anything else leaves it at its most common one.
    """
    charges = CATION_CHARGES.get(metal)
    if not charges:
        return None
    if len(charges) == 1:
        return charges[0]
    return max(charges) if partner in OXIDISING_NONMETALS else charges[0]


# --------------------------------------------------------------------------
# Routes that need no gate beyond the species being what they claim
# --------------------------------------------------------------------------


def neutralise(acid: str, base: str) -> Reaction | None:
    """`acid + base -> salt + water`. The one route with no driving-force gate."""
    acid_record = ACIDS_BY_FORMULA.get(acid)
    base_record = BASES_BY_FORMULA.get(base)
    if acid_record is None or base_record is None:
        return None
    salt = salt_formula(base_record.cation, acid_record.anion)
    if salt is None:
        return None
    return Reaction(
        reactants=(acid, base),
        products=(salt, WATER),
        template=NEUTRALISATION,
        note=_precipitate_note(base_record.cation, acid_record.anion),
    )


def acid_with_basic_oxide(acid: str, oxide: str) -> Reaction | None:
    """`acid + basic oxide -> salt + water`."""
    acid_record = ACIDS_BY_FORMULA.get(acid)
    cation = _basic_oxide_cation(oxide)
    if acid_record is None or cation is None:
        return None
    salt = salt_formula(cation, acid_record.anion)
    if salt is None:
        return None
    return Reaction(
        reactants=(acid, oxide),
        products=(salt, WATER),
        template=ACID_WITH_OXIDE,
        note=_precipitate_note(cation, acid_record.anion),
    )


def base_with_acidic_oxide(base: str, oxide: str) -> Reaction | None:
    """`base + acidic oxide -> salt + water`, for soluble strong bases only."""
    base_record = BASES_BY_FORMULA.get(base)
    anhydride = ANHYDRIDES.get(oxide)
    if base_record is None or anhydride is None:
        return None
    if base_record.strength is not Strength.STRONG:
        return None  # an insoluble hydroxide does not take up an acidic oxide
    salt = salt_formula(base_record.cation, anhydride.anion)
    if salt is None:
        return None
    return Reaction(
        reactants=(base, oxide),
        products=(salt, WATER),
        template=BASE_WITH_OXIDE,
        note=_precipitate_note(base_record.cation, anhydride.anion),
    )


def oxide_with_oxide(basic: str, acidic: str) -> Reaction | None:
    """`basic oxide + acidic oxide -> salt`. No water, so nothing else to balance."""
    cation = _basic_oxide_cation(basic)
    anhydride = ANHYDRIDES.get(acidic)
    if cation is None or anhydride is None:
        return None
    salt = salt_formula(cation, anhydride.anion)
    if salt is None:
        return None
    return Reaction(
        reactants=(basic, acidic),
        products=(salt,),
        template=OXIDE_WITH_OXIDE,
    )


def metal_with_nonmetal(metal: str, nonmetal: str) -> Reaction | None:
    """`metal + nonmetal -> binary salt`, with the charge set by the partner."""
    if not _is_curated_metal(metal) or nonmetal == "O":
        return None  # oxides are their own template
    anion_charges = ANION_CHARGES.get(nonmetal)
    if not anion_charges or is_metal(nonmetal):
        return None

    charge = cation_charge_for(metal, nonmetal)
    if charge is None:
        return None
    salt = salt_formula(ion_formula(metal, charge), ion_formula(nonmetal, anion_charges[0]))
    if salt is None:
        return None
    note = "" if len(CATION_CHARGES[metal]) == 1 else f"{metal} goes to +{charge} with {nonmetal}"
    return Reaction(
        reactants=(ELEMENTAL_FORMULA[metal], ELEMENTAL_FORMULA[nonmetal]),
        products=(salt,),
        template=SYNTHESIS,
        note=note,
    )


# --------------------------------------------------------------------------
# Routes with a driving-force gate
# --------------------------------------------------------------------------


def metal_with_acid(metal: str, acid: str) -> Reaction | None:
    """`metal + acid -> salt + H2`, for metals above hydrogen and non-oxidising acids."""
    acid_record = ACIDS_BY_FORMULA.get(acid)
    if acid_record is None or not _is_curated_metal(metal):
        return None
    if acid in NON_HYDROGEN_ACIDS:
        return None
    if not _above_hydrogen(metal):
        return None

    charge = cation_charge_for(metal, acid)
    if charge is None:
        return None
    salt = salt_formula(ion_formula(metal, charge), acid_record.anion)
    if salt is None:
        return None
    return Reaction(
        reactants=(ELEMENTAL_FORMULA[metal], acid),
        products=(salt, HYDROGEN),
        template=METAL_WITH_ACID,
        note=_precipitate_note(ion_formula(metal, charge), acid_record.anion),
    )


def double_displacement(first: str, second: str) -> Reaction | None:
    """`salt + salt -> salt + precipitate`. Needs a precipitate, or nothing happens."""
    left, right = SALT_IONS.get(first), SALT_IONS.get(second)
    if left is None or right is None:
        return None
    (left_cation, left_anion), (right_cation, right_anion) = left, right
    if left_cation == right_cation or left_anion == right_anion:
        return None
    if not _dissolves(left_cation, left_anion) or not _dissolves(right_cation, right_anion):
        return None  # a solid cannot swap ions with anything

    for cation, anion in ((left_cation, right_anion), (right_cation, left_anion)):
        if not certainly_precipitates(cation, anion):
            continue
        precipitate = salt_formula(cation, anion)
        spectator = salt_formula(
            right_cation if cation == left_cation else left_cation,
            left_anion if anion == right_anion else right_anion,
        )
        if precipitate is None or spectator is None:
            continue
        return Reaction(
            reactants=(first, second),
            products=(precipitate, spectator),
            template=DOUBLE_DISPLACEMENT,
            note=f"{precipitate} precipitates",
        )
    return None


def metal_with_salt(metal: str, salt: str) -> Reaction | None:
    """`metal + salt -> salt + metal`, if the free metal is the more active one."""
    ions = SALT_IONS.get(salt)
    if ions is None or not _is_curated_metal(metal):
        return None
    cation, anion = ions
    displaced = strip_charge(cation)
    if displaced not in CATION_CHARGES or not is_metal(displaced):
        return None
    if not _dissolves(cation, anion):
        return None  # nothing to displace out of a solid
    if _reacts_with_water(metal):
        return None  # Na would attack the water, not the salt
    if not _more_active(metal, displaced):
        return None

    charge = cation_charge_for(metal, anion)
    if charge is None:
        return None
    product = salt_formula(ion_formula(metal, charge), anion)
    if product is None:
        return None
    return Reaction(
        reactants=(ELEMENTAL_FORMULA[metal], salt),
        products=(product, ELEMENTAL_FORMULA[displaced]),
        template=METAL_WITH_SALT,
        note=f"{metal} is above {displaced} in the activity series",
    )


def halogen_with_salt(halogen: str, salt: str) -> Reaction | None:
    """`halogen + halide -> halide + halogen`, the more reactive one winning.

    The nonmetal mirror of `metal_with_salt`, and the reason bromine and iodine
    are reachable at all once their salts exist. Fluorine is excluded as an
    attacker: it oxidises the water first, so the displacement never happens.
    """
    if halogen not in HALOGEN_RANK or halogen in NON_DISPLACING_HALOGENS:
        return None
    ions = SALT_IONS.get(salt)
    if ions is None:
        return None
    cation, anion = ions

    displaced = strip_charge(anion)
    if displaced not in HALOGEN_RANK or parse_charge(anion) != -1:
        return None
    if HALOGEN_RANK[halogen] >= HALOGEN_RANK[displaced]:
        return None
    if not _dissolves(cation, anion):
        return None

    product = salt_formula(cation, ion_formula(halogen, -1))
    if product is None:
        return None
    return Reaction(
        reactants=(ELEMENTAL_FORMULA[halogen], salt),
        products=(product, ELEMENTAL_FORMULA[displaced]),
        template=HALOGEN_DISPLACEMENT,
        note=f"{halogen} is more reactive than {displaced}",
    )


# --------------------------------------------------------------------------
# Acid salts
# --------------------------------------------------------------------------
#
# The brief says normal salts only, and for a while that was right: acid salts
# double the product space for little puzzle value. What changed the answer is
# depth. Six anions -- HCO3-, HSO4-, HSO3-, H2PO4-, HPO4-2, HS- -- were curated
# in `POLYATOMIC_IONS` and reachable by nothing at all, and they are the only
# species in the game that naturally sit three or four moves from the elements.
#
# The reason to leave them out was that *how much* base you add decides which
# salt you get, and the engine has no amounts. That is handled the way burning
# an element is already handled: offer both products and let the player pick.
# `oxidations` has done exactly this since the first template was written.


def partial_neutralise(acid: str, base: str) -> list[Reaction]:
    """`acid + base -> acid salt + water`, for a polyprotic acid.

    Returns one reaction per acid salt the acid can give -- two for phosphoric
    acid, one for the rest, none for a monoprotic acid. The normal salt comes
    from `neutralise`; these are the same reaction with less base.
    """
    acid_record = ACIDS_BY_FORMULA.get(acid)
    base_record = BASES_BY_FORMULA.get(base)
    if acid_record is None or base_record is None:
        return []

    reactions: list[Reaction] = []
    for anion in ACID_SALT_ANIONS.get(acid_record.anion, ()):
        salt = salt_formula(base_record.cation, anion)
        if salt is None:
            continue
        reactions.append(
            Reaction(
                reactants=(acid, base),
                products=(salt, WATER),
                template=ACID_SALT_NEUTRALISATION,
                note="an acid salt -- less base than the normal salt needs",
            )
        )
    return reactions


def salt_with_parent_acid(salt: str, acid: str) -> list[Reaction]:
    """`normal salt + its own acid -> acid salt`. Na2SO4 + H2SO4 -> 2 NaHSO4.

    Only the salt's *own* acid does this; any other acid is displacement, which
    `chem.rules.acids` handles.
    """
    ions = SALT_IONS.get(salt)
    acid_record = ACIDS_BY_FORMULA.get(acid)
    if ions is None or acid_record is None:
        return []
    cation, anion = ions
    if acid_record.anion != anion:
        return []

    reactions: list[Reaction] = []
    for partial in ACID_SALT_ANIONS.get(anion, ()):
        product = salt_formula(cation, partial)
        if product is None:
            continue
        reactions.append(
            Reaction(
                reactants=(salt, acid),
                products=(product,),
                template=SALT_WITH_PARENT_ACID,
                note="the acid protonates its own salt",
            )
        )
    return reactions


def acid_salt_with_base(salt: str, base: str) -> list[Reaction]:
    """`acid salt + base -> normal salt + water`. NaHCO3 + NaOH -> Na2CO3 + H2O.

    Restricted to a base of the *same* cation. A different one would give a
    mixed salt (NaKCO3), which the criss-cross cannot write and which no school
    course asks for.
    """
    ions = SALT_IONS.get(salt)
    base_record = BASES_BY_FORMULA.get(base)
    if ions is None or base_record is None:
        return []
    cation, anion = ions
    parent = PARENT_ANION.get(anion)
    if parent is None or base_record.cation != cation:
        return []

    # every anion with fewer protons than this one, ending at the parent
    chain = ACID_SALT_ANIONS[parent]
    targets = list(chain[: chain.index(anion)]) + [parent]

    reactions: list[Reaction] = []
    for target in targets:
        product = salt_formula(cation, target)
        if product is None:
            continue
        reactions.append(
            Reaction(
                reactants=(salt, base),
                products=(product, WATER),
                template=ACID_SALT_WITH_BASE,
                note="more base takes off another proton",
            )
        )
    return reactions


def decompose_hydrogencarbonate(salt: str) -> Reaction | None:
    """`2 NaHCO3 --heat--> Na2CO3 + CO2 + H2O`.

    Unlike the carbonates, every hydrogencarbonate decomposes -- including the
    group 1 ones, which is what makes baking soda work.
    """
    ions = SALT_IONS.get(salt)
    if ions is None:
        return None
    cation, anion = ions
    if anion != HYDROGENCARBONATE:
        return None
    carbonate = salt_formula(cation, CARBONATE)
    if carbonate is None:
        return None
    return Reaction(
        reactants=(salt,),
        products=(carbonate, CARBON_DIOXIDE, WATER),
        template=HYDROGENCARBONATE_DECOMPOSITION,
        note="needs only gentle heating",
    )


def decompose_carbonate(salt: str) -> Reaction | None:
    """`carbonate --heat--> basic oxide + CO2`. Not for group 1: those survive."""
    ions = SALT_IONS.get(salt)
    if ions is None:
        return None
    cation, anion = ions
    if anion != CARBONATE:
        return None
    charge = parse_charge(cation)
    if charge == 1:
        return None  # Na2CO3 and K2CO3 do not decompose at school temperatures
    oxide = oxide_of_cation(cation)
    if oxide is None:
        return None
    return Reaction(
        reactants=(salt,),
        products=(oxide, CARBON_DIOXIDE),
        template=CARBONATE_DECOMPOSITION,
        note="needs heating",
    )


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _basic_oxide_cation(oxide: str) -> str | None:
    """The cation of a basic oxide, or None if it is not one."""
    resolved = OXIDE_IONS.get(oxide)
    if resolved is None:
        return None
    element, state = resolved
    if oxide_character(element, state) is not OxideCharacter.BASIC:
        return None
    cation = ion_formula(element, state)
    return cation if state in CATION_CHARGES.get(element, ()) else None


def _is_curated_metal(metal: str) -> bool:
    return metal in CATION_CHARGES and metal in ELEMENTAL_FORMULA and is_metal(metal)


def _dissolves(cation: str, anion: str) -> bool:
    """Strictly soluble -- a reactant that is not in solution cannot swap ions."""
    return solubility(cation, anion) is Solubility.SOLUBLE


def _precipitate_note(cation: str, anion: str) -> str:
    return f"{salt_formula(cation, anion)} is insoluble" if certainly_precipitates(cation, anion) else ""


def _above_hydrogen(metal: str) -> bool:
    try:
        return displaces_hydrogen_from_acid(metal)
    except KeyError:
        return False


def _more_active(metal: str, other: str) -> bool:
    try:
        return is_more_active(metal, other)
    except KeyError:
        return False


def _reacts_with_water(metal: str) -> bool:
    try:
        return reacts_with_cold_water(metal)
    except KeyError:
        return False
