"""One dealt hand, as a self-contained JSON bundle for the front end.

    python -m chem.puzzle 2026-08-04            write that day's puzzle
    python -m chem.puzzle --days 30             a month of them
    python -m chem.puzzle --days 0 --prune      drop what has fallen out of range
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

# Two months, and it is two numbers wearing one name. A day will not deal a
# target any day inside the window behind it dealt, and `prune` deletes what
# falls out of the window behind today. They have to be the same number: a day
# can only avoid what it can still read, so anything deleted is a repeat waiting
# to happen, and anything kept past the window is being kept for nothing.
#
# Counted in days rather than calendar months so the window is one length all
# year -- a February that means something different from a March is the sort of
# detail that surfaces as an unreproducible day.
RECENT_DAYS = 62

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
    way. Excluding them is not enough on its own, though: the same rule has to
    reach one step further back, into what the *substrates* are made of. A rule
    whose substrate is itself only reachable through the target is circular at
    one remove, and it looked like a way here until a CO2 day shipped asking for
    five and offering two. `without=target` is what makes the count the closure
    the player actually meets rather than the one on paper.

    The shallowest reaction per rule wins, so the example shown is the one a
    player could most plausibly have found.
    """
    cost = cheapest_moves(net, without=target)
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


def daily(
    day: Date, cut: int = DEFAULT_CUT, avoid: frozenset[str] = frozenset()
) -> Puzzle | None:
    """The puzzle for a date. Same date, same hand, on every machine.

    Seeded off the ordinal rather than shuffled at random so a day can be
    regenerated after the fact -- to reproduce a bug report, or to rebuild a
    month of puzzles without changing yesterday's.

    `avoid` is what the last two months already used; see `recent`. The draw
    needs it because it has no other memory: a date ordinal and a prime stride
    spread the *choices* evenly but know nothing of what was chosen before, so
    the same compound could come up twice in a week and did. Filtering the pool
    beforehand rather than rejecting a repeat afterwards keeps the scan below
    doing one job, which is finding a hand worth five ways.
    """
    wanted = WEEK[day.weekday()]
    # The pool floor is a cheap pre-filter over the grading pass, which counts
    # ways across the whole network under the commonness gate. It is not the
    # number that ships -- `_ways` below recounts against the dealt closure,
    # which is usually larger -- so it is set as low as each grade can bear:
    #
    #   easy    68 targets, and every one of them offers five
    #   medium  99 at four ways, 31 at five -- the floor is the whole point
    #   hard    58 at three, and *none* at four, which is what hard means here
    #
    # Hard therefore has to admit three-way targets or Friday never generates;
    # its hands still have to earn four below, from the closure.
    floor = PLAYABLE_RULES if wanted is Grade.HARD else MIN_WAYS
    eligible = sorted(
        target
        for target, found in _graded().items()
        if found.grade is wanted and found.ways >= floor
    )
    if not eligible:
        return None

    # Two months takes roughly 27 days off easy and medium and 9 off hard, out
    # of 68, 99 and 58, which looks comfortable and is only true of easy and
    # medium. A target in the pool is not a target that deals: of the 58 hard
    # ones, **7** produce a hand worth four ways or better, the rest failing
    # `generate` or coming back with three. Friday wants one of those 7 and the
    # window holds about 9 Fridays, so on hard the rule is not tight, it is
    # unsatisfiable -- roughly one Friday in three has to repeat.
    #
    # Which is why the window yields and the day does not. A missing day is not
    # a smaller version of a repeated target, it is a worse one: the site serves
    # the most recent day it has, so a gap repeats yesterday's whole hand,
    # answers and all. Try the targets the window has not used; if none of them
    # deals, try the rest and take the repeat, saying so.
    fresh = [target for target in eligible if target not in avoid]
    for pool in (fresh, eligible):
        if not pool:
            continue
        puzzle = _draw(pool, day, cut)
        if puzzle is not None:
            if pool is eligible and fresh:
                print(f"  {day}: nothing outside the window dealt; repeating a target")
            return puzzle
    return None


def _draw(pool: list[str], day: Date, cut: int) -> Puzzle | None:
    """Scan a pool for the best hand this day can be given.

    Keep looking until a hand offers the full five, then settle; below that,
    remember the first that clears the minimum and keep looking anyway. So a day
    asks five wherever five exist and four where they do not, and never deals a
    hand worth three -- the old fallback took the first playable candidate at
    any depth, which is how a day could ship asking for three.

    Bounded rather than exhaustive, for the same reason `_cover` is greedy: a
    generator that might scan a thousand targets on a bad day is one nobody can
    predict the runtime of. Past the bound the remembered hand wins, and if
    nothing ever cleared the minimum this pool has no hand to offer.
    """
    seed = day.toordinal()
    fallback: Puzzle | None = None

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
# The calendar already on disk
# --------------------------------------------------------------------------


def dealt(directory: Path) -> dict[str, str]:
    """Every day already written, and the target it was dealt.

    `index.json` names the calendar and is read first, because it is the file
    that says what this deployment serves. It is not trusted on its own: a day
    it lists but does not have is skipped, and every dated bundle in the
    directory is read whether the index mentions it or not. The index has a
    history of being written short -- it used to hold only the days of the run
    that wrote it -- and the failure that would cause here is silent, a day
    repeating because the walk could not see the day it was repeating.

    Bundles are parsed rather than pattern-matched for their target. A hand is
    a couple of hundred kB at worst and there are only two months of them, so
    the whole read is a fraction of a second against a minute of grading.
    """
    days: set[str] = set()

    try:
        listed = json.loads((directory / "index.json").read_text(encoding="utf-8"))
        days.update(day for day in listed.get("puzzles", []) if _is_date(str(day)))
    except (OSError, json.JSONDecodeError, AttributeError):
        pass  # no index yet, or an unreadable one; the directory still knows

    days.update(p.stem for p in directory.glob("*.json") if _is_date(p.stem))

    found: dict[str, str] = {}
    for day in sorted(days):
        try:
            document = json.loads(
                (directory / f"{day}.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            continue  # listed but missing, or half-written; it deals no target
        target = document.get("target")
        if isinstance(target, str):
            found[day] = target
    return found


def recent(
    known: dict[str, str], day: Date, window: int = RECENT_DAYS
) -> frozenset[str]:
    """What the `window` days *before* `day` were dealt.

    Behind only, deliberately. A symmetric window would read the days after the
    one being dealt too, which sounds strictly better and quietly costs the
    property that makes this calendar debuggable: regenerate a day and you get
    the same puzzle, because the same seed met the same inputs. Days after it
    are inputs that did not exist when it was first dealt. Looking only
    backwards means a day depends on its own past and nothing else, so it can
    still be rebuilt from a date -- as long as the two months behind it are
    still on disk, which is exactly what `prune` keeps.
    """
    first = day - timedelta(days=window)
    return frozenset(
        target
        for other, target in known.items()
        if first <= Date.fromisoformat(other) < day
    )


def prune(directory: Path, today: Date, window: int = RECENT_DAYS) -> list[str]:
    """Delete bundles older than the window. Returns the days removed.

    Safe to delete because nothing reads them. The front end serves exactly one
    day -- the most recent that is not in the future -- and has no archive, so a
    bundle two months past is bytes in a deployment and a diff nobody reads.
    Every one of them is still in git history if a day ever has to be inspected.

    Two rails. Future days are never touched however far ahead they run, and the
    day the site is currently serving is never touched even if it is older than
    the window, which it would be only if the calendar had already run dry. That
    second one is the difference between a stale puzzle and a 404.
    """
    keep_from = today - timedelta(days=window)
    days = sorted(p.stem for p in directory.glob("*.json") if _is_date(p.stem))
    serving = _serving(days, today)

    removed: list[str] = []
    for day in days:
        if Date.fromisoformat(day) >= keep_from or day == serving:
            continue
        (directory / f"{day}.json").unlink()
        removed.append(day)
    return removed


def _serving(days: list[str], today: Date) -> str | None:
    """The day the site would hand a player right now.

    Mirrors `lib/day.pick` in the front end, down to the fallback: with nothing
    but future days it serves the earliest rather than nothing. Duplicated in
    two languages because it has to be, and kept to four lines so the two can be
    read against each other.
    """
    now = today.isoformat()
    past = [day for day in sorted(days) if day <= now]
    return past[-1] if past else (sorted(days)[0] if days else None)


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

    # The calendar so far, kept in hand and added to as the run deals. Reading
    # it once and updating it is not only cheaper than re-reading the directory
    # each day -- it is the only version that is right, because the days this
    # run is writing have to count against each other too. A week dealt in one
    # go used to be the easiest place to draw the same target twice.
    known = dealt(output)

    written = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        puzzle = daily(day, avoid=recent(known, day))
        if puzzle is None:
            print(f"{day}: no puzzle available")
            continue
        _write(output / f"{day.isoformat()}.json", puzzle)
        known[day.isoformat()] = puzzle.target
        written.append(day.isoformat())

    if "--prune" in argv:
        # Against today, not against the days just dealt. The window is what a
        # *player* has been shown, and dealing a month ahead must not drag the
        # cutoff a month forward with it and delete two months of still-current
        # calendar. `daily` reads the same window, so what goes is what nothing
        # will ask for again.
        removed = prune(output, Date.today())
        for day in removed:
            print(f"  pruned {day}  (older than {RECENT_DAYS} days)")
        print(f"  pruned {len(removed)} bundle{'' if len(removed) == 1 else 's'}")

    # Written from the directory rather than from `written`, always. The index
    # used to list only the days of the run that produced it, so dealing one day
    # truncated the calendar to that day and orphaned every other bundle --
    # `verify_bundles.py --reindex` exists to repair exactly that. Now that a
    # run can delete files as well as add them the index has to be rebuilt here
    # anyway, and rebuilding it from what is on disk is the version that cannot
    # be wrong. The repair stays, as the independent check it always was.
    listing = sorted(p.stem for p in output.glob("*.json") if _is_date(p.stem))
    index = output / "index.json"
    index.write_text(
        json.dumps({"version": VERSION, "puzzles": listing}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  wrote {index}  ({len(listing)} puzzles, {len(written)} new)")
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
