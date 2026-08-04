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
from datetime import date as Date
from datetime import timedelta
from pathlib import Path
from typing import Any

from chem import network
from chem.balance import balance
from chem.difficulty import PLAYABLE_RULES, Grade, assess_all
from chem.export import VERSION
from chem.generate import DEFAULT_CUT, WANT_WAYS, Puzzle, generate
from chem.reaction import Reaction
from chem.rules.catalogue import rule_slug
from chem.rules.commonness import is_common
from chem.rules.display import species_record

DEFAULT_OUTPUT = Path("../frontend/public/puzzles")

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

    return {
        "version": VERSION,
        "target": puzzle.target,
        "name": species_record(puzzle.target).name,
        "grade": puzzle.grade.value,
        "want": min(WANT_WAYS, puzzle.ways),  # ask for what exists
        "ways": puzzle.ways,
        "cut": puzzle.cut,
        "palette": list(puzzle.palette),
        "species": {formula: _species(formula) for formula in reachable},
        "reactions": [_reaction(r) for r in net.reactions],
        "answers": {
            rule: _reaction(puzzle.examples[rule])
            for rule in puzzle.rules
            if rule in puzzle.examples
        },
    }


def daily(day: Date, cut: int = DEFAULT_CUT) -> Puzzle | None:
    """The puzzle for a date. Same date, same hand, on every machine.

    Seeded off the ordinal rather than shuffled at random so a day can be
    regenerated after the fact -- to reproduce a bug report, or to rebuild a
    month of puzzles without changing yesterday's.
    """
    wanted = WEEK[day.weekday()]
    # A hard target has few ways -- that is what makes it hard -- so demanding
    # five of them excludes every hard compound and Friday never generates.
    # The ask scales instead: five where five exist, three on a tight day.
    floor = PLAYABLE_RULES if wanted is Grade.HARD else WANT_WAYS
    pool = sorted(
        target
        for target, found in _graded().items()
        if found.grade is wanted and found.ways >= floor
    )
    if not pool:
        return None

    seed = day.toordinal()
    for offset in range(len(pool)):
        target = pool[(seed + offset * 7919) % len(pool)]  # a prime, to spread
        puzzle = generate(target, cut=cut, seed=seed)
        if puzzle is not None and puzzle.ways >= floor:
            return puzzle
    return None


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
