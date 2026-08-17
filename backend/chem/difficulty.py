"""How hard is this compound to make five ways?

Grades a target for the find-N-ways game. The question is not "can it be made"
-- almost everything can -- but "how many *different kinds* of chemistry reach
it, and would a student recognise any of them".

Three measures, in the order they matter:

1. **accessible rules** -- distinct rule templates that produce the target from
   substrates the player could plausibly name. This is the score the game is
   played against, so it is the primary axis. Raw route count is not usable:
   H2CO3 has 813 routes and 812 of them are one rule with the spectator ion
   swapped, which grades a lookup as a masterpiece.

2. **setup depth** -- how many moves of building it takes before a rule's
   substrates are all in hand. A rule available at move 1 is a gimme; one that
   needs a three-move intermediate is the last thing anybody finds. Reuses the
   hyperpath relaxation that par-golf scoring used.

3. **commonness of the target itself** -- a compound nobody has heard of makes a
   bad daily however many routes it has, so it is a gate rather than an axis.

The thresholds in `grade()` are a judgement call and deliberately in one place.
They are tuned so the buckets are all usefully populated rather than so the
words mean anything absolute; `python -m chem.difficulty` prints the histogram
they produce.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from chem import network
from chem.network import DEFAULT_SEEDS, Network, cheapest_moves
from chem.reaction import Reaction
from chem.rules.catalogue import rule_slug
from chem.rules.commonness import all_common, is_common

# Below this many accessible rules a target cannot carry a find-N-ways day: the
# game asks for five and wants headroom above it.
PLAYABLE_RULES = 3


class Grade(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    UNSUITABLE = "unsuitable"


@dataclass(frozen=True, slots=True)
class Assessment:
    target: str
    common: bool
    depth: int  # fewest moves to make the target at all
    rules: tuple[str, ...]  # every rule that reaches it from the palette
    accessible: tuple[str, ...]  # ...using only species a student would name
    # Move at which each accessible rule's substrates are all available.
    setup: dict[str, int]
    # One worked reaction per accessible rule -- the shallowest, so it is the
    # one a player could most reasonably have found. This is what the end of a
    # game shows for the ways you missed.
    examples: dict[str, Reaction]
    grade: Grade

    @property
    def ways(self) -> int:
        return len(self.accessible)

    @property
    def obscure(self) -> int:
        """Rules that work but route through species nobody would guess."""
        return len(self.rules) - len(self.accessible)

    @property
    def hardest_setup(self) -> int:
        return max(self.setup.values(), default=0)


def assess_all(palette: tuple[str, ...] = DEFAULT_SEEDS) -> dict[str, Assessment]:
    """Grade every species the palette can reach. One network build, ~3 seconds."""
    net = network.build(palette)
    cost = cheapest_moves(net)
    return {
        target: _assess(target, net, cost)
        for target in net.species
        if target not in set(palette)
    }


def assess(target: str, palette: tuple[str, ...] = DEFAULT_SEEDS) -> Assessment | None:
    """Grade one target against one palette. None if the palette cannot reach it."""
    net = network.build(palette)
    if target not in set(net.species):
        return None
    return _assess(target, net, cheapest_moves(net))


def grade(accessible: int, depth: int, common: bool) -> Grade:
    """The one place the thresholds live. Retune here, not at the call sites."""
    if not common or accessible < PLAYABLE_RULES:
        return Grade.UNSUITABLE
    if accessible >= 6 and depth <= 2:
        return Grade.EASY
    if accessible >= 4 and depth <= 3:
        return Grade.MEDIUM
    return Grade.HARD


def _assess(target: str, net: Network, cost: dict[str, int]) -> Assessment:
    by_rule: dict[str, list[Reaction]] = defaultdict(list)
    for reaction in net.reactions:
        if target in reaction.products and target not in reaction.reactants:
            by_rule[rule_slug(reaction.template) or reaction.template].append(reaction)

    depth = cost.get(target, -1)

    # The trophy rule, as reachability rather than as a filter on one reaction.
    # A substrate is only a substrate if the player can hold it *and* the target
    # at once, and the board never hands over the target -- so a rule whose
    # substrate is reachable only by first making the target is not a way, it is
    # the target laundered through one extra step. CO2 is the case that proves
    # it: every carbonate here descends from CO2, so barring it takes the three
    # decomposition ways away and leaves a compound with two.
    #
    # `cost` above is the shared map for the whole catalogue and recomputing it
    # per target costs about 45 ms, which over 1143 targets is a minute. It is
    # only ever wrong about a species made *from* the target, and such a species
    # is necessarily deeper than it -- every step costs a move -- so a candidate
    # no deeper than the target needs no second opinion. That skips about a
    # quarter of them and the pass costs 45s rather than 4s, which is the price
    # of the number being true. It runs weekly, in CI, next to a 100s generate.
    candidates = {x for rs in by_rule.values() for r in rs for x in r.reactants}
    if any(cost.get(x, -1) > depth for x in candidates):
        cost = cheapest_moves(net, without=target)

    setup: dict[str, int] = {}
    examples: dict[str, Reaction] = {}
    for rule, reactions in by_rule.items():
        usable = [
            r
            for r in reactions
            if all_common(r.reactants) and all(x in cost for x in r.reactants)
        ]
        if not usable:
            continue
        best = min(usable, key=lambda r: max(cost[x] for x in r.reactants))
        setup[rule] = max(cost[x] for x in best.reactants)
        examples[rule] = best

    accessible = tuple(sorted(setup, key=lambda rule: (setup[rule], rule)))
    common = is_common(target)
    return Assessment(
        target=target,
        common=common,
        depth=depth,
        rules=tuple(sorted(by_rule)),
        accessible=accessible,
        setup=setup,
        examples=examples,
        grade=grade(len(accessible), depth, common),
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    from collections import Counter

    assessments = assess_all()
    if argv:
        for target in argv:
            found = assessments.get(target)
            if found is None:
                print(f"{target}: not reachable from the full palette")
                continue
            _report(found)
        return 0

    counts = Counter(a.grade for a in assessments.values())
    print(f"graded {len(assessments)} species\n")
    for value in Grade:
        print(f"  {value.value:<12} {counts[value]:>5}")

    playable = [a for a in assessments.values() if a.grade is not Grade.UNSUITABLE]
    print(f"\n{len(playable)} playable targets, by ways available:")
    for ways, count in sorted(Counter(a.ways for a in playable).items()):
        print(f"  {ways:>2} ways   {count:>4} targets")

    for value in (Grade.EASY, Grade.MEDIUM, Grade.HARD):
        picks = sorted(
            (a for a in playable if a.grade is value), key=lambda a: -a.ways
        )[:8]
        print(f"\n{value.value}:")
        for a in picks:
            print(
                f"  {a.target:<12} {a.ways} ways, depth {a.depth},"
                f" {a.obscure} obscure route(s) hidden"
            )
    return 0


def _report(a: Assessment) -> None:
    print(f"{a.target} -- {a.grade.value}")
    print(f"  {a.ways} accessible ways, {a.obscure} obscure hidden, depth {a.depth}")
    for rule in a.accessible:
        print(f"    move {a.setup[rule]}  {rule}")
    print()


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
