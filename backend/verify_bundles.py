"""Check the puzzle bundles the browser will actually be served.

Deliberately standing outside `chem`: it imports nothing from the generator and
needs no dependencies, so it re-derives winnability from the shipped JSON rather
than asking the code that produced it whether it did a good job. A generator bug
that miscounts `ways` is invisible to a check that trusts `ways`.

The reachability walk here is the game's rules, not the network's:

  - you start with the palette and nothing else;
  - a reaction fires only when every substrate is already in hand;
  - the target may never be a substrate, because consuming the target to make
    the target is not a way to make it, and the board refuses to select it;
  - products are added and never consumed.

Run with --reindex to rebuild index.json from the directory first. The generator
writes an index containing only the days of that one run, so generating a single
day rewrites the index down to that day and silently orphans every other bundle
on disk. Rebuilding from the directory is the fix that cannot get this wrong.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

# Below this many days of remaining calendar, say so. The generator tops up
# weekly to a month ahead, so anything under a week means roughly three runs
# have not happened and the schedule needs looking at.
RUNWAY_WARNING = 7

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "frontend/public/puzzles"


def reachable_rules(bundle: dict) -> set[str]:
    """Every rule making the target that the palette can actually get to."""
    target = bundle["target"]
    inventory = set(bundle["palette"])
    usable = [r for r in bundle["reactions"] if target not in r["substrates"]]

    # Fixpoint: a reaction can unlock the substrate another one was waiting on.
    grew = True
    while grew:
        grew = False
        for reaction in usable:
            if not set(reaction["substrates"]) <= inventory:
                continue
            products = set(reaction["products"])
            if not products <= inventory:
                inventory |= products
                grew = True

    return {
        reaction["rule"]
        for reaction in usable
        if target in reaction["products"] and set(reaction["substrates"]) <= inventory
    }


def check(day: str, bundle: dict) -> tuple[list[str], list[str]]:
    """Returns (problems, notes). Problems fail the run; notes only report.

    The split is about what a player would experience. A day that cannot be
    finished, or an answer sheet citing a route the palette never permitted,
    is broken and must not ship. A day that is merely *richer* than it claims
    still plays correctly — you can win it, and every scored way is real — so
    it is reported rather than blocking a calendar that is otherwise fine.
    """
    problems, notes = [], []
    target = bundle["target"]
    reached = reachable_rules(bundle)
    want, ways = bundle["want"], bundle["ways"]

    # The one that makes a day unplayable rather than merely odd.
    if len(reached) < want:
        problems.append(
            f"{day}: asks for {want} ways but only {len(reached)} are reachable "
            f"from the palette ({', '.join(sorted(reached)) or 'none'})"
        )
    if want > ways:
        problems.append(f"{day}: want {want} exceeds ways {ways}")

    answers = set(bundle["answers"])
    if len(answers) != ways:
        problems.append(f"{day}: {len(answers)} answers for {ways} ways")
    # The end screen teaches from `answers`, so an answer nobody could have
    # found is a lesson about a route the puzzle never contained.
    if answers - reached:
        problems.append(
            f"{day}: answers unreachable from the palette: "
            f"{', '.join(sorted(answers - reached))}"
        )

    # A dead-end note on a pair that actually reacts is the one kind of feedback
    # that is worse than silence: the player is told, in the game's own voice,
    # that chemistry they could have run does not happen. `explain` guards
    # against it on the way in by asking `combine` first; this checks the
    # shipped file, which is the only artefact a player ever sees.
    pairs = {tuple(sorted(r["substrates"])) for r in bundle["reactions"]}
    lying = [
        " + ".join(sorted(m["substrates"]))
        for m in bundle.get("misses", [])
        if tuple(sorted(m["substrates"])) in pairs
    ]
    if lying:
        problems.append(
            f"{day}: dead-end notes on pairs that do react: {', '.join(sorted(lying))}"
        )

    # Playable, but the end screen promises *every* way and would omit these.
    if reached - answers:
        notes.append(
            f"{day}: {len(reached)} ways reachable, {ways} on the answer sheet, "
            f"missing {', '.join(sorted(reached - answers))}"
        )
    # Sidesteps the trophy rule: the board refuses to select the target, so a
    # target dealt at the start is a bottle nobody can ever pick up.
    if target in bundle["palette"]:
        notes.append(f"{day}: the target {target} is dealt in the palette")

    return problems, notes


def days_on_disk(directory: Path) -> list[str]:
    return sorted(p.stem for p in directory.glob("*.json") if p.stem != "index")


def main(argv: list[str]) -> int:
    paths = [a for a in argv if not a.startswith("--")]
    directory = Path(paths[0]) if paths else DEFAULT_DIR
    if not directory.is_dir():
        print(f"no such directory: {directory}")
        return 2

    disk = days_on_disk(directory)
    index_path = directory / "index.json"

    problems: list[str] = []
    notes: list[str] = []

    bundles: dict[str, dict] = {}
    for day in disk:
        try:
            bundles[day] = json.loads(
                (directory / f"{day}.json").read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError) as error:
            problems.append(f"{day}: unreadable ({error})")

    # The index carries the same `VERSION` the bundles do, and this script does
    # not import the generator to find out what it currently is. Taking it from
    # the data means a reindex can never silently downgrade the number and put
    # every browser's stored save out of step with what it is being served.
    versions = {b.get("version") for b in bundles.values()}
    if len(versions) > 1:
        problems.append(f"bundles disagree on version: {sorted(map(str, versions))}")
    version = next(iter(versions), None) if len(versions) == 1 else None

    if "--reindex" in argv:
        if version is None:
            problems.append("cannot reindex: no single bundle version to write")
        else:
            index_path.write_text(
                json.dumps({"version": version, "puzzles": disk}, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"reindexed {index_path} ({len(disk)} puzzles, version {version})")

    if not index_path.exists():
        problems.append("index.json is missing")
        listed: list[str] = []
    else:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        listed = index["puzzles"]
        if version is not None and index.get("version") != version:
            problems.append(
                f"index.json is version {index.get('version')} "
                f"but the bundles are version {version}"
            )
        for day in sorted(set(listed) - set(disk)):
            problems.append(f"{day}: listed in index.json but no bundle on disk")
        for day in sorted(set(disk) - set(listed)):
            problems.append(f"{day}: bundle on disk but missing from index.json")

    # Runway. The site serves the most recent day that is not in the future, so
    # an exhausted calendar does not error -- it silently reserves yesterday's
    # puzzle forever, which is the worst kind of outage because nothing looks
    # broken. This is the alarm for a schedule that quietly stopped firing.
    #
    # It does make the result depend on the wall clock, which is unusual for
    # CI. That is the intended trade: a red build is how you find out, and the
    # alternative is finding out from a player.
    if disk:
        today = date.today()
        latest = date.fromisoformat(disk[-1])
        runway = (latest - today).days
        if runway < 0:
            problems.append(
                f"the calendar ran out on {disk[-1]} and today is {today}: "
                f"every player is being served a stale puzzle"
            )
        elif runway < RUNWAY_WARNING:
            notes.append(
                f"only {runway} day{'' if runway == 1 else 's'} of puzzles left "
                f"after today (last is {disk[-1]}) -- is the schedule running?"
            )

    for day, bundle in bundles.items():
        day_problems, day_notes = check(day, bundle)
        problems.extend(day_problems)
        notes.extend(day_notes)

    if notes:
        print("notes:")
        for note in notes:
            print(f"  {note}")
    if problems:
        print("problems:")
        for problem in problems:
            print(f"  {problem}")

    print(
        f"\n{len(disk)} bundles, {len(listed)} indexed, "
        f"{len(problems)} problem{'' if len(problems) == 1 else 's'}, "
        f"{len(notes)} note{'' if len(notes) == 1 else 's'}"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
