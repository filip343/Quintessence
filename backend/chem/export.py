"""Export the network as JSON: the species list, the reaction list, the routes.

    python -m chem.export [output directory] [--balance]     default: ./data

Separate files because they have different lifetimes and different readers:

- `species.json` -- what a species *is*. The UI needs this and nothing else to
  render an inventory.
- `reactions.json` -- the hypergraph's edge list, one row per reaction. This is
  the canonical form: a reaction with three products is one row, not three.
- `routes.json` -- the same reactions indexed by product, answering "how do I
  make X" directly. Derived, and regenerated with the other two.
- `targets.json` -- the playable subset, graded easy / medium / hard. What the
  daily is sampled from; see `chem.difficulty` for what the grades mean.

The two questions the game asks pull in opposite directions. The crafting loop
asks "the player selected A and B, what happens", which wants a substrate
index; the target-first generator asks "how do I make X", which wants a product
index. Neither file can be both, and inverting an index is a few lines at load
time, so the edge list stays canonical and `routes.json` is the inversion that
the generator would otherwise build on every run.

`routes.json` is exactly 2x the rows of `reactions.json` -- nearly every
reaction has two products, so nearly every reaction is filed under two keys.
That is the cost of the index, and it is why it is not the only form shipped.

All four carry the same `version`, so a mismatched set is detectable. Every
species named in `reactions.json` is present in `species.json` -- `check()`
asserts it before anything is written, so the set is never shipped
inconsistent.

Reactions are exported without coefficients, as `chem.reaction` defines them.
`--balance` runs the whole network through ChemPy first and drops anything whose
coefficients do not come out as clean positive integers; it is off by default
because it takes about twenty minutes over the full network, against three
seconds for everything else. Run it before shipping a data file, not while
iterating on one.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from chem import network
from chem.balance import balance
from chem.difficulty import Assessment, Grade, assess_all
from chem.network import Network
from chem.reaction import Reaction
from chem.rules.catalogue import rule_slug
from chem.rules.commonness import is_common
from chem.rules.display import species_record

VERSION = 3

SPECIES_FILE = "species.json"
REACTIONS_FILE = "reactions.json"
ROUTES_FILE = "routes.json"
TARGETS_FILE = "targets.json"

DEFAULT_OUTPUT = Path("data")


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------


def species_document(species: tuple[str, ...]) -> dict[str, Any]:
    return {
        "version": VERSION,
        "species": {formula: _species_entry(formula) for formula in sorted(species)},
    }


def reactions_document(reactions: tuple[Reaction, ...]) -> dict[str, Any]:
    entries = [_reaction_entry(reaction) for reaction in reactions]
    entries.sort(key=lambda entry: (entry["rule"], entry["substrates"], entry["products"]))
    return {"version": VERSION, "reactions": entries}


def routes_document(reactions: tuple[Reaction, ...]) -> dict[str, Any]:
    """`reactions.json` inverted: product -> every way to make it.

    Filed under *every* product, not just the first. Hydrogen comes out of
    `metal + acid` as the second product, and "how do I make hydrogen" is a fair
    question, so keying on `products[0]` alone would hide real routes.

    `sideproducts` is a list rather than a single value because 654 reactions
    have three products -- `NH4Cl + NaOH -> NH3 + NaCl + H2O` filed under NH3
    has two of them, and a singular field would silently drop one.
    """
    routes: dict[str, list[dict[str, Any]]] = {}
    for reaction in reactions:
        for product in reaction.products:
            routes.setdefault(product, []).append(_route_entry(reaction, product))

    for entries in routes.values():
        entries.sort(key=lambda entry: (entry["substrates"], entry["rule"]))
    return {"version": VERSION, "routes": {key: routes[key] for key in sorted(routes)}}


def targets_document(assessments: dict[str, Assessment]) -> dict[str, Any]:
    """The graded candidate targets -- what a daily is picked from.

    Only the playable ones. A species with two routes, or one no student would
    recognise, is not a bad target so much as not a target: the game asks for
    five ways and there is nothing to ask for. `chem.difficulty` explains the
    grades; this is that judgement, frozen for the generator to sample from.
    """
    entries = {
        target: {
            "grade": found.grade.value,
            "ways": found.ways,
            "depth": found.depth,
            "obscure": found.obscure,
            "rules": list(found.accessible),
            "setup": [found.setup[rule] for rule in found.accessible],
        }
        for target, found in sorted(assessments.items())
        if found.grade is not Grade.UNSUITABLE
    }
    return {"version": VERSION, "targets": entries}


def _route_entry(reaction: Reaction, product: str) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "substrates": list(reaction.reactants),
        "sideproducts": [other for other in reaction.products if other != product],
        "rule": rule_slug(reaction.template) or reaction.template,
    }
    if reaction.note:
        entry["note"] = reaction.note
    return entry


def _species_entry(formula: str) -> dict[str, Any]:
    record = species_record(formula)
    entry: dict[str, Any] = {
        "name": record.name,
        "class": record.species_class,
        "state": record.state,
        # Whether a school course would put this in front of a student. Not a
        # correctness claim -- everything here is real -- but the generator
        # needs it to keep Cu(HS)2 out of a starting palette.
        "common": is_common(formula),
    }
    if record.ions:
        entry["ions"] = record.ions
    return entry


def _reaction_entry(reaction: Reaction) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "substrates": list(reaction.reactants),
        "products": list(reaction.products),
        "rule": rule_slug(reaction.template) or reaction.template,
    }
    if reaction.note:
        entry["note"] = reaction.note
    return entry


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


def check(net: Network, species: tuple[str, ...]) -> list[str]:
    """Everything that would make the exported pair unusable. Empty is good."""
    problems: list[str] = []
    known = set(species)

    missing = sorted(
        {
            formula
            for reaction in net.reactions
            for formula in reaction.reactants + reaction.products
            if formula not in known
        }
    )
    problems += [f"{formula} appears in a reaction but not in the species list" for formula in missing]

    uncatalogued = sorted({r.template for r in net.reactions if rule_slug(r.template) is None})
    problems += [f"template {template!r} has no slug in the rule catalogue" for template in uncatalogued]

    unnamed = sorted(formula for formula in species if species_record(formula).name == formula)
    problems += [f"{formula} has no display name" for formula in unnamed]

    unclassed = sorted(formula for formula in species if species_record(formula).species_class == "unknown")
    problems += [f"{formula} classifies as unknown" for formula in unclassed]

    return problems


def check_routes(reactions: tuple[Reaction, ...], document: dict[str, Any]) -> list[str]:
    """The index must invert back to exactly the reactions it was built from.

    A derived file is only worth shipping if it is provably the same data. This
    reassembles each route into `{product} | {sideproducts}` and compares the
    multiset against the reactions' own product sets, which is the check that
    would have caught a singular `sideproduct` field dropping the third product
    of an ammonia liberation.
    """
    rebuilt: set[tuple[tuple[str, ...], frozenset[str]]] = set()
    for product, entries in document["routes"].items():
        for entry in entries:
            products = frozenset([product, *entry["sideproducts"]])
            rebuilt.add((tuple(entry["substrates"]), products))

    original = {
        (reaction.reactants, frozenset(reaction.products)) for reaction in reactions
    }
    problems = [
        f"routes lost {substrates} -> {sorted(products)}"
        for substrates, products in sorted(original - rebuilt)
    ]
    problems += [
        f"routes invented {substrates} -> {sorted(products)}"
        for substrates, products in sorted(rebuilt - original)
    ]
    return problems


def unbalanced(reactions: tuple[Reaction, ...]) -> list[Reaction]:
    return [reaction for reaction in reactions if balance(reaction) is None]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    verify = "--balance" in argv
    paths = [argument for argument in argv if not argument.startswith("--")]
    output = Path(paths[0]) if paths else DEFAULT_OUTPUT

    print("building the reaction network ...")
    net = network.build()
    species = net.reacting_species
    reacting = set(species)
    print(f"  {len(net.species)} species reachable, {len(species)} of them reacting")
    print(f"  {len(net.reactions)} reactions")

    dropped = sorted(formula for formula in net.species if formula not in reacting)
    if dropped:
        print(f"  {len(dropped)} inert species left out: {' '.join(dropped)}")

    reactions = net.reactions
    if verify:
        print(f"balancing {len(reactions)} reactions -- this takes a while ...")
        failures = set(unbalanced(reactions))
        if failures:
            print(f"  {len(failures)} do not balance and are not exported:")
            for reaction in sorted(failures, key=Reaction.equation)[:10]:
                print(f"    {reaction.equation()}   [{reaction.template}]")
        reactions = tuple(reaction for reaction in reactions if reaction not in failures)
        print(f"  {len(reactions)} balanced")
    else:
        print("balancing skipped -- rerun with --balance before shipping the files")

    routes = routes_document(reactions)
    rows = sum(len(entries) for entries in routes["routes"].values())
    print(f"indexed by product: {len(routes['routes'])} keys, {rows} routes")

    assessments = assess_all()
    targets = targets_document(assessments)
    playable = Counter(entry["grade"] for entry in targets["targets"].values())
    print(f"graded targets: {dict(playable)}")

    problems = check(net, species) + check_routes(reactions, routes)
    if problems:
        print(f"\n{len(problems)} problems -- nothing written:")
        for problem in problems[:20]:
            print(f"  {problem}")
        return 1

    output.mkdir(parents=True, exist_ok=True)
    _write(output / SPECIES_FILE, species_document(species))
    _write(output / REACTIONS_FILE, reactions_document(reactions))
    _write(output / ROUTES_FILE, routes)
    _write(output / TARGETS_FILE, targets)
    return 0


def _write(path: Path, document: dict[str, Any]) -> None:
    path.write_text(_render(document), encoding="utf-8")
    size = path.stat().st_size
    print(f"  wrote {path}  ({size / 1024:.0f} kB)")


COLLECTIONS = ("species", "reactions", "routes", "targets")


def _render(document: dict[str, Any]) -> str:
    """One record per line: plain JSON, but greppable and diffable.

    `json.dumps(indent=2)` breaks every formula in every list onto its own line,
    which triples the file and makes a reaction impossible to read at a glance.
    One record per line is the level a human wants, and it means
    `grep NaHCO3 reactions.json` answers a real question.

    A document is a header plus exactly one collection, in one of three shapes:
    a list of records, a mapping of key to record, or -- for the routes index --
    a mapping of key to a *list* of records, which gets a block of its own so
    that a species with 2241 routes does not become a 2241-record line.
    """
    body, *rest = [key for key in document if key in COLLECTIONS] or [None]
    if body is None or rest:
        raise ValueError(f"a document holds exactly one of {COLLECTIONS}")

    header = {key: value for key, value in document.items() if key != body}
    lines = [f"{json.dumps(key)}: {json.dumps(value)}," for key, value in header.items()]

    collection = document[body]
    if isinstance(collection, dict):
        blocks = [_entry(key, value) for key, value in collection.items()]
        braces = "{}"
    else:
        blocks = [[_compact(entry)] for entry in collection]
        braces = "[]"

    lines.append(f"{json.dumps(body)}: {braces[0]}")
    for index, block in enumerate(blocks):
        block[-1] += "," if index < len(blocks) - 1 else ""
        lines += [f"  {line}" for line in block]
    lines.append(braces[1])
    return "{\n" + "\n".join(f"  {line}" for line in lines) + "\n}\n"


def _entry(key: str, value: Any) -> list[str]:
    """One mapping entry: a single line, or a block if the value is a list."""
    if not isinstance(value, list):
        return [f"{json.dumps(key)}: {_compact(value)}"]
    if not value:
        return [f"{json.dumps(key)}: []"]
    records = [f"  {_compact(record)}," for record in value]
    records[-1] = records[-1][:-1]
    return [f"{json.dumps(key)}: ["] + records + ["]"]


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
