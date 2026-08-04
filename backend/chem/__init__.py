"""Chemistry knowledge for the daily synthesis puzzle.

Three layers, each depending only on the ones below it:

    chem.formulas   formula-string syntax; no chemistry, no dependencies
    chem.reaction   the Reaction record every rule template returns
    chem.data       curated tables; data only, one module per table
    chem.rules      decisions and reaction templates built from those tables
    chem.validate   cross-checks that keep the tables agreeing

Two passes sit on top of those layers rather than inside them, because both are
about finished reactions rather than about deciding them:

    chem.balance    ChemPy coefficients; the only place ChemPy is used
    chem.network    the whole hypergraph, and the minimum-moves relaxation
    chem.export     that network as species.json + reactions.json

`chem.rules.combine(a, b)` is the entry point for "the player mixed these two".

Both `chem.data` and `chem.rules` are re-exported flat for convenience, so
`from chem import IS_METAL, solubility` works. Import the subpackage directly
(`from chem.data import IS_METAL`) when the layer matters to the reader.

Run `python -m chem` to sanity-check the tables against each other.
"""

from chem import data, formulas, rules, validate
from chem.data import *  # noqa: F403
from chem.rules import *  # noqa: F403
from chem.formulas import (
    criss_cross,
    ion_formula,
    oxide_formula,
    oxygen_count,
    parse_charge,
    strip_charge,
)
from chem.reaction import Reaction
from chem.validate import check_tables

__all__ = [
    "Reaction",
    "check_tables",
    "criss_cross",
    "data",
    "formulas",
    "ion_formula",
    "oxide_formula",
    "oxygen_count",
    "parse_charge",
    "rules",
    "strip_charge",
    "validate",
    *data.__all__,
    *rules.__all__,
]
