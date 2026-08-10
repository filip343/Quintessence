"""Every reaction template, with a stable machine-readable id.

`Reaction.template` is prose -- "acid + base -> salt + water" -- which is right
for a tooltip and wrong for anything that has to persist. This module gives each
template a slug that an exported file, a save game or a puzzle definition can
key on, and that is free to stay fixed while the prose is reworded.

It is also the one place that lists the templates, so `chem.validate` can check
that every reaction the engine can emit came from a rule someone wrote down --
a template added without a slug shows up as a failed check rather than as an
unrecognised string in the export.

The map is not one-to-one, and the two places it is not are the point. A
template is an equation shape; a slug is a *kind of move*, and scoring counts
kinds. Ammonia writes two equations nothing else writes -- it takes a proton
without giving water, because it is not a hydroxide, and it leaves a salt as a
gas rather than as a precipitate -- but neither is a second thing to discover:

    NH3    + HNO3          -> NH4NO3                    neutralisation
    NH4OH  + HNO3          -> NH4NO3 + H2O              neutralisation

    NH4Cl  + NaOH          -> NaCl + NH3 + H2O          salt_with_base
    CuCl2  + 2 NaOH        -> 2 NaCl + Cu(OH)2          salt_with_base

Given its own slug, the first of each pair was a free way: NH4OH is ammonia
plus water, so a palette holding NH3 held both halves, and the two scored
separately. Ammonia is in most palettes because it is cheap to reach, so most
days were quietly worth one way less than they claimed -- and the way you were
missing was always the same one. Merged, the second of each pair reports the
kind as already found, which is the truth and is also the lesson: a gas leaving
and a precipitate dropping are one rule with two exits.

`hydroxide_precipitation` became `salt_with_base` in that merge, since half of
what it now covers drops nothing. Retired slugs are still named in the front
end's `RULE_NAMES`, because puzzles dealt before the merge are frozen and still
carry them.

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
SALT_WITH_BASE = "salt + base -> base + salt"

# Slugs that more than one template deliberately shares -- see the note above
# `RULE_SLUGS`. `chem.validate` flags every *other* collision, because an
# accidental one silently merges two rules in every file the engine writes.
MERGED_SLUGS: frozenset[str] = frozenset({"neutralisation", "salt_with_base"})

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
    # Ammonia writes a different equation and is not a different rule; the two
    # merges are the whole subject of the note above.
    HYDRIDE_WITH_ACID: "neutralisation",
    # --- salts ---
    DOUBLE_DISPLACEMENT: "double_displacement",
    SALT_WITH_BASE: "salt_with_base",
    LIBERATION: "salt_with_base",
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
