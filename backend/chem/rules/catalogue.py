"""Every reaction template, with a stable machine-readable id.

`Reaction.template` is prose -- "acid + base -> salt + water" -- which is right
for a tooltip and wrong for anything that has to persist. This module gives each
template a slug that an exported file, a save game or a puzzle definition can
key on, and that is free to stay fixed while the prose is reworded.

It is also the one place that lists the templates, so `chem.validate` can check
that every reaction the engine can emit came from a rule someone wrote down --
a template added without a slug shows up as a failed check rather than as an
unrecognised string in the export.

Note the two constants named SYNTHESIS: `chem.rules.ammonia` and
`chem.rules.salts` both use the name for different templates, and the package's
flat re-export keeps only the second. They are imported under distinct names
here so both survive.
"""

from __future__ import annotations

from chem.rules.acids import DISPLACEMENT, HYDRATION, HYDROGENATION
from chem.rules.ammonia import DISSOLUTION, HYDRIDE_WITH_ACID, LIBERATION
from chem.rules.ammonia import SYNTHESIS as HYDRIDE_SYNTHESIS
from chem.rules.bases import METAL_WITH_WATER, OXIDE_HYDRATION
from chem.rules.chromate import ACIDIFY, ALKALISE
from chem.rules.disproportionation import DISPROPORTIONATION
from chem.rules.oxides import OXIDATION
from chem.rules.reduction import ALUMINOTHERMIC, REDUCTION
from chem.rules.salts import (
    ACID_SALT_NEUTRALISATION,
    ACID_SALT_WITH_BASE,
    ACID_WITH_OXIDE,
    BASE_WITH_OXIDE,
    CARBONATE_DECOMPOSITION,
    DOUBLE_DISPLACEMENT,
    HALOGEN_DISPLACEMENT,
    HYDROGENCARBONATE_DECOMPOSITION,
    METAL_WITH_ACID,
    METAL_WITH_SALT,
    NEUTRALISATION,
    OXIDE_WITH_OXIDE,
    SALT_WITH_PARENT_ACID,
)
from chem.rules.salts import SYNTHESIS as BINARY_SALT_SYNTHESIS
from chem.rules.unstable import DECOMPOSITION

# `salt + base -> base + salt` is declared inline in `chem.rules.reactions`
# rather than as a constant; see the note on `double_displacement_with_base`.
HYDROXIDE_PRECIPITATION = "salt + base -> base + salt"

RULE_SLUGS: dict[str, str] = {
    # --- elements in ---
    OXIDATION: "oxidation",
    BINARY_SALT_SYNTHESIS: "binary_salt_synthesis",
    HYDROGENATION: "hydrogenation",
    HYDRIDE_SYNTHESIS: "hydride_synthesis",
    # --- water in ---
    HYDRATION: "anhydride_hydration",
    OXIDE_HYDRATION: "basic_oxide_hydration",
    METAL_WITH_WATER: "metal_with_water",
    DISSOLUTION: "hydride_dissolution",
    # --- acid/base ---
    NEUTRALISATION: "neutralisation",
    ACID_WITH_OXIDE: "acid_with_basic_oxide",
    BASE_WITH_OXIDE: "base_with_acidic_oxide",
    OXIDE_WITH_OXIDE: "oxide_with_oxide",
    METAL_WITH_ACID: "metal_with_acid",
    DISPLACEMENT: "acid_displacement",
    HYDRIDE_WITH_ACID: "ammonia_with_acid",
    LIBERATION: "ammonia_liberation",
    # --- salts ---
    DOUBLE_DISPLACEMENT: "double_displacement",
    HYDROXIDE_PRECIPITATION: "hydroxide_precipitation",
    METAL_WITH_SALT: "metal_displacement",
    HALOGEN_DISPLACEMENT: "halogen_displacement",
    REDUCTION: "oxide_reduction",
    ALUMINOTHERMIC: "aluminothermic_reduction",
    DISPROPORTIONATION: "halogen_disproportionation",
    # --- acid salts ---
    ACID_SALT_NEUTRALISATION: "partial_neutralisation",
    SALT_WITH_PARENT_ACID: "salt_with_parent_acid",
    ACID_SALT_WITH_BASE: "acid_salt_with_base",
    # --- chromate ---
    ACIDIFY: "chromate_acidification",
    ALKALISE: "dichromate_alkalisation",
    # --- decomposition ---
    DECOMPOSITION: "unstable_decomposition",
    HYDROGENCARBONATE_DECOMPOSITION: "hydrogencarbonate_decomposition",
    CARBONATE_DECOMPOSITION: "carbonate_decomposition",
}


def rule_slug(template: str) -> str | None:
    """The stable id for a template string, or None if it is not catalogued."""
    return RULE_SLUGS.get(template)
