"""Curated chemistry tables. Data only -- no logic reads or interprets them here.

One module per table, matching the brief's curation list:

- `elements`  -- metal / nonmetal classification (+ metalloid, amphoteric tags)
- `ions`      -- ion charges, valences, polyatomic ions
- `activity`  -- activity series of metals, water reactivity, halogen order
- `solubility`-- solubility rules, anion-major with exceptions
- `oxides`    -- acid anhydrides, oxide-character exceptions
- `strength`  -- the strong/weak scale shared by acids and bases
- `acids` / `bases` / `hydrides` -- compound tables, keyed by the ion that
  defines them so no formula is written down twice
- `salts`     -- the formula -> ions index that replaces a formula parser
- `reduction` -- reducing agents and how far down the series each one reaches

The functions that walk these tables live in `chem.rules`; the cross-checks that
keep them honest live in `chem.validate`.
"""

from chem.data.acids import (
    ACID_FORMULA_OVERRIDES,
    ACID_FORMULAS,
    ACID_SALT_ANION_SET,
    ACID_SALT_ANIONS,
    ACIDS,
    ACIDS_BY_FORMULA,
    EXCLUDED_ACIDS,
    HYDRACID_ELEMENTS,
    NON_HYDROGEN_ACIDS,
    PARENT_ANION,
    PROTON_COUNT,
    Acid,
)
from chem.data.bases import (
    BASE_FORMULAS,
    BASES,
    BASES_BY_FORMULA,
    EXCLUDED_BASES,
    HYDRATABLE_OXIDE_CATIONS,
    Base,
)
from chem.data.activity import (
    ACTIVITY_RANK,
    ACTIVITY_SERIES,
    HALOGEN_ACTIVITY,
    HALOGEN_RANK,
    HYDROGEN_RANK,
    NON_DISPLACING_HALOGENS,
    WATER_REACTIVITY,
    WaterReactivity,
)
from chem.data.reduction import EXCLUDED_REDUCERS, REDUCERS, Reducer
from chem.data.elements import (
    ALKALI_METALS,
    ALKALINE_EARTH_METALS,
    AMPHOTERIC_OXIDE_ELEMENTS,
    COMMON_ELEMENTS,
    DIATOMIC_ELEMENTS,
    ELEMENT_NAMES,
    ELEMENT_OF_FORMULA,
    ELEMENTAL_FORMULA,
    HALOGENS,
    IS_METAL,
    METALLOIDS,
    NOBLE_GASES,
    NON_SOLID_ELEMENTS,
    OXIDISING_NONMETALS,
)
from chem.data.hydrides import (
    AMMONIA,
    AMMONIUM,
    EXCLUDED_HYDRIDES,
    HYDRIDE_ELEMENTS,
    HYDRIDE_OF_ELEMENT,
    HYDRIDES,
    Hydride,
)
from chem.data.salts import (
    OXIDE_IONS,
    SALT_FORMULAS,
    SALT_INDEX_COLLISIONS,
    SALT_IONS,
)
from chem.data.strength import Strength
from chem.data.ions import (
    ANION_CHARGES,
    ANION_FORMULAS,
    CATION_CHARGES,
    CATION_FORMULAS,
    CHEMPY_FORMULA_ALIASES,
    COMMON_ANIONS,
    COMMON_CATIONS,
    MONATOMIC_ANION_NAMES,
    POLYATOMIC_IONS,
    POSITIVE_OXIDATION_STATES,
    Ion,
)
from chem.data.oxides import (
    ACIDIC_METAL_STATE,
    ACIDIC_OXIDES,
    ANHYDRIDES,
    ANION_TO_ANHYDRIDE,
    EXCLUDED_OXIDES,
    NEUTRAL_OXIDE_NAMES,
    NEUTRAL_OXIDES,
    NON_SOLID_OXIDES,
    OXIDE_CHARACTER_OVERRIDES,
    WATER,
    Anhydride,
    OxideCharacter,
)
from chem.data.solubility import (
    ALWAYS_SOLUBLE_CATIONS,
    ANION_RULES,
    NON_AQUEOUS_ANIONS,
    SOLUBILITY_OVERRIDES,
    AnionRule,
    Solubility,
)

__all__ = [
    "AMMONIA",
    "AMMONIUM",
    "ACIDIC_METAL_STATE",
    "ACIDIC_OXIDES",
    "ACIDS",
    "ACIDS_BY_FORMULA",
    "ACID_FORMULAS",
    "ACID_FORMULA_OVERRIDES",
    "ACID_SALT_ANIONS",
    "ACID_SALT_ANION_SET",
    "ACTIVITY_RANK",
    "ACTIVITY_SERIES",
    "ALKALINE_EARTH_METALS",
    "ALKALI_METALS",
    "ALWAYS_SOLUBLE_CATIONS",
    "AMPHOTERIC_OXIDE_ELEMENTS",
    "ANHYDRIDES",
    "ANION_CHARGES",
    "ANION_FORMULAS",
    "ANION_RULES",
    "ANION_TO_ANHYDRIDE",
    "Acid",
    "Anhydride",
    "AnionRule",
    "BASES",
    "BASES_BY_FORMULA",
    "BASE_FORMULAS",
    "Base",
    "CATION_CHARGES",
    "CATION_FORMULAS",
    "CHEMPY_FORMULA_ALIASES",
    "COMMON_ANIONS",
    "COMMON_CATIONS",
    "COMMON_ELEMENTS",
    "DIATOMIC_ELEMENTS",
    "ELEMENTAL_FORMULA",
    "ELEMENT_NAMES",
    "ELEMENT_OF_FORMULA",
    "EXCLUDED_ACIDS",
    "EXCLUDED_BASES",
    "EXCLUDED_HYDRIDES",
    "EXCLUDED_OXIDES",
    "EXCLUDED_REDUCERS",
    "HALOGENS",
    "HALOGEN_ACTIVITY",
    "HALOGEN_RANK",
    "HYDRACID_ELEMENTS",
    "HYDRATABLE_OXIDE_CATIONS",
    "HYDRIDES",
    "HYDRIDE_ELEMENTS",
    "HYDRIDE_OF_ELEMENT",
    "HYDROGEN_RANK",
    "IS_METAL",
    "Hydride",
    "Ion",
    "METALLOIDS",
    "MONATOMIC_ANION_NAMES",
    "NEUTRAL_OXIDES",
    "NEUTRAL_OXIDE_NAMES",
    "NOBLE_GASES",
    "NON_AQUEOUS_ANIONS",
    "NON_DISPLACING_HALOGENS",
    "NON_HYDROGEN_ACIDS",
    "NON_SOLID_ELEMENTS",
    "NON_SOLID_OXIDES",
    "OXIDE_CHARACTER_OVERRIDES",
    "OXIDE_IONS",
    "OXIDISING_NONMETALS",
    "OxideCharacter",
    "PARENT_ANION",
    "POLYATOMIC_IONS",
    "POSITIVE_OXIDATION_STATES",
    "PROTON_COUNT",
    "REDUCERS",
    "Reducer",
    "SALT_FORMULAS",
    "SALT_INDEX_COLLISIONS",
    "SALT_IONS",
    "SOLUBILITY_OVERRIDES",
    "Solubility",
    "Strength",
    "WATER",
    "WATER_REACTIVITY",
    "WaterReactivity",
]
