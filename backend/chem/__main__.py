"""`python -m chem` -- table summary, spot checks, and cross-validation."""

from __future__ import annotations

import sys

from chem.data import (
    ACIDS,
    ACTIVITY_SERIES,
    ANHYDRIDES,
    ANION_CHARGES,
    ANION_RULES,
    BASES,
    CATION_CHARGES,
    IS_METAL,
    POLYATOMIC_IONS,
    SALT_IONS,
)
from chem.balance import balance, unbalanceable
from chem.data.hydrides import HYDRIDES
from chem.data.reduction import REDUCERS
from chem.rules import combine, decompose, oxide_character, solubility
from chem.validate import check_tables

# Textbook facts to spot-check the solubility lookup against.
SOLUBILITY_CHECKS: tuple[tuple[str, str, str], ...] = (
    ("Ba+2", "SO4-2", "insoluble"),  # the barium test
    ("Ag+", "Cl-", "insoluble"),
    ("Na+", "CO3-2", "soluble"),
    ("Ca+2", "CO3-2", "insoluble"),
    ("Cu+2", "OH-", "insoluble"),
    ("K+", "NO3-", "soluble"),
    ("NH4+", "PO4-3", "soluble"),
    ("Pb+2", "I-", "insoluble"),
    ("Ba+2", "OH-", "soluble"),
    ("Hg+2", "Cl-", "soluble"),  # molecular, not ionic
)

# The character rule has to split one element's oxides by oxidation state.
OXIDE_CHECKS: tuple[tuple[str, int, str], ...] = (
    ("Ca", 2, "basic"),
    ("Na", 1, "basic"),
    ("Fe", 3, "basic"),
    ("S", 6, "acidic"),
    ("C", 4, "acidic"),
    ("Si", 4, "acidic"),
    ("Cr", 3, "amphoteric"),  # Cr2O3
    ("Cr", 6, "acidic"),  # CrO3 -- same element, different answer
    ("Mn", 2, "basic"),  # MnO
    ("Mn", 4, "amphoteric"),  # MnO2
    ("Mn", 7, "acidic"),  # Mn2O7
    ("Al", 3, "amphoteric"),  # out of scope for v1
    ("C", 2, "neutral"),  # CO
)

# The routes, end to end: what should two species produce?
REACTION_CHECKS: tuple[tuple[str, str, str], ...] = (
    # acids
    ("SO3", "H2O", "H2SO4"),
    ("CO2", "H2O", "H2CO3"),
    ("N2O5", "H2O", "HNO3"),
    ("P2O5", "H2O", "H3PO4"),
    ("H2", "Cl2", "HCl"),
    ("H2", "S", "H2S"),
    ("SiO2", "H2O", ""),  # the anhydride that will not hydrate
    ("CO", "H2O", ""),  # neutral oxide
    ("H2O", "H2O", ""),  # water is not its own anhydride
    # bases
    ("CaO", "H2O", "Ca(OH)2"),
    ("Na", "H2O", "NaOH"),
    ("CuO", "H2O", ""),  # only strong-base oxides hydrate
    ("Fe", "H2O", ""),  # above hydrogen, but not in cold water
    # salts
    ("HCl", "NaOH", "NaCl"),
    ("H2SO4", "Cu(OH)2", "CuSO4"),
    ("HCl", "CuO", "CuCl2"),
    ("NaOH", "CO2", "Na2CO3"),
    ("CaO", "CO2", "CaCO3"),
    ("Zn", "HCl", "ZnCl2"),
    ("Cu", "HCl", ""),  # below hydrogen
    ("Na", "HNO3", ""),  # nitric acid oxidises instead of giving H2
    ("BaCl2", "Na2SO4", "BaSO4"),
    ("NaCl", "KNO3", ""),  # no precipitate, no reaction
    ("CuSO4", "NaOH", "Cu(OH)2"),
    ("Fe", "CuSO4", "FeSO4"),
    ("Cu", "FeSO4", ""),  # wrong way round the activity series
    ("Na", "CuSO4", ""),  # sodium would attack the water instead
    # the oxidation-state policy: the partner decides
    ("Fe", "Cl2", "FeCl3"),
    ("Fe", "S", "FeS"),
    ("Fe", "HCl", "FeCl2"),
    ("Sn", "Cl2", "SnCl4"),
    # ammonia -- the one base that is not a hydroxide
    ("H2", "N2", "NH3"),
    ("NH3", "H2O", "NH4OH"),
    ("NH3", "HCl", "NH4Cl"),  # no water: the gas takes the proton directly
    ("NH3", "H2SO4", "(NH4)2SO4"),
    ("NH4Cl", "NaOH", "NH3"),  # the test for an ammonium salt
    ("NH4Cl", "Cu(OH)2", ""),  # a weak base cannot drive the gas off
    # halogen displacement: the nonmetal activity order
    ("Cl2", "NaBr", "NaCl"),
    ("Br2", "KI", "KBr"),
    ("Br2", "NaCl", ""),  # wrong way round
    ("F2", "NaCl", ""),  # fluorine attacks the water first
    # reduction: the way back down from an oxide
    ("CuO", "H2", "Cu"),
    ("CuO", "C", "Cu"),
    ("Fe2O3", "CO", "Fe"),  # the blast furnace
    ("ZnO", "C", "Zn"),  # an amphoteric oxide, still reducible
    ("ZnO", "H2", ""),  # hydrogen does not reach zinc
    ("Al2O3", "C", ""),  # too high in the series -- needs electrolysis
    ("MgO", "C", ""),
    ("Fe2O3", "Al", "Al2O3"),  # the aluminothermic reaction
    ("ZnO", "Cu", ""),  # wrong way round the activity series
    # boron, arsenic and selenium now have an acid to reach
    ("B2O3", "H2O", "H3BO3"),
    ("SeO3", "H2O", "H2SeO4"),
    ("As2O5", "H2O", "H3AsO4"),
    # chromate <-> dichromate: yellow to orange and back
    ("K2CrO4", "H2SO4", "H2CrO4"),
    ("K2Cr2O7", "KOH", "K2CrO4"),
    ("K2CrO4", "H2S", ""),  # too weak an acid to shift it
    ("K2Cr2O7", "NH4OH", ""),  # too weak a base
)

# Acid salts. `combine` returns the normal salt first and the acid salts after,
# so these check the *whole* list -- the point of the template is that a
# polyprotic acid offers a choice, and a check on products[0] would not see it.
ACID_SALT_CHECKS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("HCl", "NaOH", ("NaCl",)),  # monoprotic: no choice to offer
    ("H2SO4", "NaOH", ("Na2SO4", "NaHSO4")),
    ("H2CO3", "NaOH", ("Na2CO3", "NaHCO3")),
    ("H3PO4", "NaOH", ("Na3PO4", "Na2HPO4", "NaH2PO4")),
    ("Na2SO4", "H2SO4", ("NaHSO4",)),  # a salt protonated by its own acid
    ("Na3PO4", "H3PO4", ("Na2HPO4", "NaH2PO4")),
    ("NaHCO3", "NaOH", ("Na2CO3",)),  # and back down again
    ("NaH2PO4", "NaOH", ("Na2HPO4", "Na3PO4")),
    ("NaHCO3", "KOH", ()),  # a mixed salt we cannot write
    ("NaHCO3", "HCl", ("H2CO3",)),  # behaves as a salt of its parent acid
    ("NaHSO4", "HCl", ()),  # HCl is no stronger than H2SO4
)

# Single-input reactions.
DECOMPOSITION_CHECKS: tuple[tuple[str, str], ...] = (
    ("CaCO3", "CaO"),
    ("CuCO3", "CuO"),
    ("Na2CO3", ""),  # group 1 carbonates survive school-level heating
    ("H2CO3", "CO2"),  # the unstable-products table, finally applied
    ("H2SO3", "SO2"),
    ("NH4OH", "NH3"),
    ("NaHCO3", "Na2CO3"),  # unlike the carbonates, group 1 included
    ("Ca(HCO3)2", "CaCO3"),
    ("NaCl", ""),
)


def print_tables() -> None:
    metals = sum(1 for metal in IS_METAL.values() if metal)
    print("tables")
    print(f"  elements          {len(IS_METAL):>4}  ({metals} metals, {len(IS_METAL) - metals} not)")
    print(f"  cation elements   {len(CATION_CHARGES):>4}")
    print(f"  anion elements    {len(ANION_CHARGES):>4}")
    print(f"  polyatomic ions   {len(POLYATOMIC_IONS):>4}")
    print(f"  activity series   {len(ACTIVITY_SERIES):>4}  {' > '.join(ACTIVITY_SERIES)}")
    print(f"  solubility rules  {len(ANION_RULES):>4}")
    print(f"  acid anhydrides   {len(ANHYDRIDES):>4}")
    print(f"  acids             {len(ACIDS):>4}")
    print(f"  bases             {len(BASES):>4}")
    print(f"  hydrides          {len(HYDRIDES):>4}")
    print(f"  reducing agents   {len(REDUCERS):>4}")
    print(f"  salts indexed     {len(SALT_IONS):>4}  (formula -> ions, no parsing)")


def print_anhydrides() -> None:
    print("\nanhydrides")
    for record in ANHYDRIDES.values():
        note = "" if record.hydrates else "   (does not hydrate)"
        tier = " " if record.common else "."
        print(
            f" {tier} {record.formula:<6} +H2O -> acid of {record.anion:<7}"
            f" {record.element}(+{record.state}){note}"
        )


def run_spot_checks() -> int:
    print("\nspot checks")
    failures = 0
    for cation, anion, expected in SOLUBILITY_CHECKS:
        actual = solubility(cation, anion).value
        ok = actual == expected
        failures += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {cation:>6} + {anion:<8} {actual}")
    for element, state, expected in OXIDE_CHECKS:
        actual = oxide_character(element, state).value
        ok = actual == expected
        failures += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {element:>4}(+{state}) oxide  {actual}")

    for first, second, expected in REACTION_CHECKS:
        products = [reaction.product for reaction in combine(first, second)]
        actual = products[0] if products else ""
        ok = actual == expected
        failures += not ok
        print(
            f"  {'ok  ' if ok else 'FAIL'} {first:>6} + {second:<8} -> "
            f"{actual or 'no reaction'}"
        )

    for first, second, expected_all in ACID_SALT_CHECKS:
        actual = tuple(reaction.product for reaction in combine(first, second))
        ok = actual == expected_all
        failures += not ok
        print(
            f"  {'ok  ' if ok else 'FAIL'} {first:>8} + {second:<7} -> "
            f"{', '.join(actual) or 'no reaction'}"
            + ("" if ok else f"   expected {', '.join(expected_all) or 'no reaction'}")
        )

    for species, expected in DECOMPOSITION_CHECKS:
        products = [reaction.product for reaction in decompose(species)]
        actual = products[0] if products else ""
        ok = actual == expected
        failures += not ok
        print(
            f"  {'ok  ' if ok else 'FAIL'} heat {species:<11} -> "
            f"{actual or 'no reaction'}"
        )
    return failures


def run_balance_checks() -> int:
    """Every reaction the spot checks fire must balance in clean integers."""
    reactions = [
        reaction
        for first, second, _ in REACTION_CHECKS + ACID_SALT_CHECKS
        for reaction in combine(first, second)
    ] + [
        reaction for species, _ in DECOMPOSITION_CHECKS for reaction in decompose(species)
    ]

    failures = unbalanceable(reactions)
    print(f"\nbalancing ({len(reactions)} reactions)")
    for reaction, reason in failures:
        print(f"  FAIL {reaction.equation()}   {reason}")
    if not failures:
        for reaction in reactions[:8]:
            balanced = balance(reaction)
            if balanced is not None:
                print(f"  ok   {balanced.equation()}")
        print(f"  ... {len(reactions)} balanced, 0 rejected")
    return len(failures)


def main() -> int:
    print_tables()
    print_anhydrides()
    failures = run_spot_checks()
    failures += run_balance_checks()

    problems = check_tables()
    print(f"\nconsistency: {len(problems)} problem(s)")
    for problem in problems:
        print(f"  - {problem}")

    return 1 if problems or failures else 0


if __name__ == "__main__":
    sys.exit(main())
