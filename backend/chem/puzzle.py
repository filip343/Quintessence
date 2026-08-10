"""One dealt hand, as a self-contained JSON bundle for the front end.

    python -m chem.puzzle 2026-08-04            write that day's puzzle
    python -m chem.puzzle --days 30             a month of them
    python -m chem.puzzle CuSO4 --out .         one named target

A puzzle's whole closure is about 3 kB -- eighteen species and thirty-odd
reactions for a typical hand -- against 8.6 MB for the full reaction list. So
the front end never queries a backend: it loads one small file and plays.
Everything it needs is precomputed here, including the **balanced equations**,
because balancing is ChemPy and ChemPy is Python.

The bundle is closed under mixing. Every reaction between any two species the
player could ever hold is listed, so "what happens if I mix these" is a lookup
rather than a rule engine the browser would have to re-implement. That is the
whole reason the chemistry can stay in one language.

`answers` carries a worked reaction for every way, for the end-of-game screen.
It is deliberately in the same file the player already has: this is a teaching
game, and hiding the answer behind a request would mean the last screen fails
when the network does.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date as Date
from itertools import combinations
from datetime import timedelta
from pathlib import Path
from typing import Any

from chem import network
from chem.balance import balance
from chem.difficulty import PLAYABLE_RULES, Grade, assess_all
from chem.export import VERSION
from chem.network import cheapest_moves
from chem.generate import DEFAULT_CUT, MIN_WAYS, WANT_WAYS, Puzzle, generate
from chem.reaction import Reaction
from chem.rules.catalogue import rule_slug
from chem.rules.commonness import is_common
from chem.rules.misses import explain
from chem.rules.display import species_record

DEFAULT_OUTPUT = Path("../frontend/public/puzzles")

# How many targets a day may try before accepting a hand short of five ways.
_CANDIDATES = 40

# Rotates the difficulty over a week, the way a crossword does: gentle at the
# start, hardest midweek. Monday is index 0.
WEEK: tuple[Grade, ...] = (
    Grade.EASY,
    Grade.EASY,
    Grade.MEDIUM,
    Grade.MEDIUM,
    Grade.HARD,
    Grade.MEDIUM,
    Grade.EASY,
)


def bundle(puzzle: Puzzle) -> dict[str, Any]:
    """Everything the front end needs to run this hand offline."""
    net = network.build(puzzle.palette)
    reachable = sorted(net.species)
    examples = _ways(puzzle.target, net)

    return {
        "version": VERSION,
        "target": puzzle.target,
        "name": species_record(puzzle.target).name,
        "grade": puzzle.grade.value,
        "want": min(WANT_WAYS, len(examples)),  # ask for what exists
        "ways": len(examples),
        "cut": puzzle.cut,
        "palette": list(puzzle.palette),
        "species": {formula: _species(formula) for formula in reachable},
        "reactions": [_reaction(r) for r in net.reactions],
        "answers": {rule: _reaction(examples[rule]) for rule in examples},
        "misses": _misses(reachable, puzzle.target),
    }


def _misses(species: list[str], target: str) -> list[dict[str, Any]]:
    """Why the interesting dead ends are dead.

    Precomputed for the same reason the reactions are: the browser has no rule
    engine, and a note that had to be derived in the client would mean shipping
    the activity series and the solubility table to derive it from.

    Only pairs a curated gate refused get an entry, so this is a fraction of the
    dead ends rather than all of them -- on a typical hand, a quarter. Pairs
    containing the target are skipped because the board will not let anyone
    select it, so a note about one could never be read.
    """
    found: list[dict[str, Any]] = []
    for first, second in combinations([s for s in species if s != target], 2):
        note = explain(first, second)
        if note:
            found.append({"substrates": [first, second], "note": note})
    return found


def _ways(target: str, net: network.Network) -> dict[str, Reaction]:
    """One worked reaction per rule the dealt hand can actually reach.

    Counted from the closure the bundle ships rather than from the grading pass,
    because those two applied different filters and the difference was visible
    in play. `chem.difficulty` drops any rule whose substrates are not all
    `is_common` -- the right call when ranking 1183 targets, where it is what
    stops a route through MgCrO4 counting as a way. But the bundle ships the
    whole closure, and the board scores any reaction that makes the target. So
    a hand could offer eight ways, print five on the answer sheet, and give a
    player a sixth the end screen then failed to explain.

    The commonness gate has already done its work by this point: it chose the
    target and it chose the palette. Once a hand is dealt, anything the player
    can actually build out of it is a way, and the teaching screen owes them
    every one.

    Reactions consuming the target are excluded, the trophy rule again --
    `Na2SO4 + H2SO4 -> NaHSO4` then back again is two real reactions and a fake
    way. The shallowest reaction per rule wins, so the example shown is the one
    a player could most plausibly have found.
    """
    cost = cheapest_moves(net)
    by_rule: dict[str, list[Reaction]] = defaultdict(list)
    for reaction in net.reactions:
        if target in reaction.products and target not in reaction.reactants:
            slug = rule_slug(reaction.template) or reaction.template
            by_rule[slug].append(reaction)

    depth: dict[str, int] = {}
    best: dict[str, Reaction] = {}
    for rule, reactions in by_rule.items():
        usable = [r for r in reactions if all(x in cost for x in r.reactants)]
        if not usable:
            continue
        # `equation()` breaks ties, so the same hand always names the same
        # example -- a bundle that changed between two identical runs would
        # make a regenerated day a different puzzle for no reason.
        pick = min(usable, key=lambda r: (max(cost[x] for x in r.reactants), r.equation()))
        depth[rule] = max(cost[x] for x in pick.reactants)
        best[rule] = pick

    # Shallowest first: the end screen reads as a difficulty ramp.
    return {rule: best[rule] for rule in sorted(best, key=lambda r: (depth[r], r))}


def daily(day: Date, cut: int = DEFAULT_CUT) -> Puzzle | None:
    """The puzzle for a date. Same date, same hand, on every machine.

    Seeded off the ordinal rather than shuffled at random so a day can be
    regenerated after the fact -- to reproduce a bug report, or to rebuild a
    month of puzzles without changing yesterday's.
    """
    wanted = WEEK[day.weekday()]
    # The pool floor is a cheap pre-filter over the grading pass, which counts
    # ways across the whole network under the commonness gate. It is not the
    # number that ships -- `_ways` below recounts against the dealt closure,
    # which is usually larger -- so it is set as low as each grade can bear:
    #
    #   easy    68 targets, and every one of them offers five
    #   medium  100 at four ways, 32 at five -- the floor is the whole point
    #   hard    59 at three, and *none* at four, which is what hard means here
    #
    # Hard therefore has to admit three-way targets or Friday never generates;
    # its hands still have to earn four below, from the closure.
    floor = PLAYABLE_RULES if wanted is Grade.HARD else MIN_WAYS
    pool = sorted(
        target
        for target, found in _graded().items()
        if found.grade is wanted and found.ways >= floor
    )
    if not pool:
        return None

    seed = day.toordinal()
    fallback: Puzzle | None = None

    # Keep looking until a hand offers the full five, then settle; below that,
    # remember the first that clears the minimum and keep looking anyway. So a
    # day asks five wherever five exist and four where they do not, and never
    # deals a hand worth three -- the old fallback took the first playable
    # candidate at any depth, which is how a day could ship asking for three.
    #
    # Bounded rather than exhaustive, for the same reason `_cover` is greedy:
    # a generator that might scan a thousand targets on a bad day is one nobody
    # can predict the runtime of. Past the bound the remembered hand wins, and
    # if nothing ever cleared the minimum the day has no puzzle -- better a gap
    # the calendar can be asked about than a day that is not worth playing.
    for offset in range(min(len(pool), _CANDIDATES)):
        target = pool[(seed + offset * 7919) % len(pool)]  # a prime, to spread
        puzzle = generate(target, cut=cut, seed=seed)
        if puzzle is None:
            continue
        ways = len(_ways(target, network.build(puzzle.palette)))
        if ways >= WANT_WAYS:
            return puzzle
        if ways >= MIN_WAYS and fallback is None:
            fallback = puzzle
    return fallback


# --------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------


def _species(formula: str) -> dict[str, Any]:
    record = species_record(formula)
    entry: dict[str, Any] = {
        "name": record.name,
        "class": record.species_class,
        "state": record.state,
        "common": is_common(formula),
    }
    if record.ions:
        entry["ions"] = record.ions
    return entry


def _reaction(reaction: Reaction) -> dict[str, Any]:
    balanced = balance(reaction)
    entry: dict[str, Any] = {
        "substrates": list(reaction.reactants),
        "products": list(reaction.products),
        "rule": rule_slug(reaction.template) or reaction.template,
        # The balanced string, rendered here because the browser has no ChemPy.
        "equation": balanced.equation() if balanced else reaction.equation(),
    }
    if balanced is not None:
        entry["coefficients"] = {
            "substrates": [count for count, _ in balanced.reactants],
            "products": [count for count, _ in balanced.products],
        }
    if reaction.note:
        entry["note"] = reaction.note
    return entry


_GRADED: dict[str, Any] = {}


def _graded() -> dict[str, Any]:
    if not _GRADED:
        _GRADED.update(
            {t: a for t, a in assess_all().items() if a.grade is not Grade.UNSUITABLE}
        )
    return _GRADED


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    output = DEFAULT_OUTPUT
    if "--out" in argv:
        index = argv.index("--out")
        output = Path(argv[index + 1])
        argv = argv[:index] + argv[index + 2 :]

    days = 1
    if "--days" in argv:
        index = argv.index("--days")
        days = int(argv[index + 1])
        argv = argv[:index] + argv[index + 2 :]

    names = [a for a in argv if not a.startswith("--")]
    output.mkdir(parents=True, exist_ok=True)

    if names and not _is_date(names[0]):
        for target in names:
            puzzle = generate(target)
            if puzzle is None:
                print(f"{target}: cannot be dealt")
                continue
            _write(output / f"{target}.json", puzzle)
        return 0

    start = Date.fromisoformat(names[0]) if names else Date.today()
    written = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        puzzle = daily(day)
        if puzzle is None:
            print(f"{day}: no puzzle available")
            continue
        _write(output / f"{day.isoformat()}.json", puzzle)
        written.append(day.isoformat())

    if written:
        index = output / "index.json"
        index.write_text(
            json.dumps({"version": VERSION, "puzzles": written}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  wrote {index}  ({len(written)} puzzles)")
    return 0


def _write(path: Path, puzzle: Puzzle) -> None:
    document = bundle(puzzle)
    # Plain indented JSON: a bundle is a few kB, so the one-record-per-line
    # renderer the big exports need buys nothing here.
    rendered = json.dumps(document, indent=2, ensure_ascii=False)
    path.write_text(rendered + "\n", encoding="utf-8")
    print(
        f"  wrote {path}  ({path.stat().st_size / 1024:.0f} kB)"
        f"  {document['target']:<12} {document['grade']:<7}"
        f" {document['want']}/{document['ways']} ways,"
        f" {len(document['palette'])} species"
    )


def _is_date(text: str) -> bool:
    try:
        Date.fromisoformat(text)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
