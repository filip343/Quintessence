"""Deal a playable hand: a target, and a palette that reaches it several ways.

    python -m chem.generate CuSO4            one puzzle
    python -m chem.generate --sample 12      a spread across the grades

Target-first, as the brief requires -- choosing a palette independently of the
target produces unsolvable days. The walk runs backward from the target and the
result is checked forward:

1. Group the target's routes by rule. Each rule is a distinct "way".
2. For each rule, resolve one route's substrates backward until every branch
   bottoms out at the **cut** -- the depth at which we stop building and start
   dealing. That leaf set is what the rule costs.
3. Greedily take the rules whose leaf sets are cheapest to add, until the
   palette budget is spent or enough ways are covered. This is set cover, not
   backtracking: at the budget we keep the best coverage found rather than
   retrying route choices, which is what makes it terminate predictably.
4. **Verify forward.** Build the network from the chosen palette and count the
   rules it really enables. Step 2 reasons about one route at a time and cannot
   see whether the substrates are co-buildable, so its count is a proposal. The
   forward number is the one the puzzle ships with.

The cut is the difficulty dial, and it is independent of the target. At cut 0 the
palette is elements and the player rebuilds everything; at cut 2 they are handed
acids and bases and the day is short. Resolving all the way to elements every
time would deal roughly the same two dozen species daily and waste the variety
in a 1183-species network, which is why the cut is a parameter rather than a
constant.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from chem import network
from chem.data.oxides import WATER
from chem.difficulty import Grade, assess
from chem.network import Network, cheapest_moves
from chem.reaction import Reaction
from chem.rules.catalogue import rule_slug
from chem.rules.commonness import is_common

# How many ways a day asks for, and the most species it may deal to get there.
WANT_WAYS = 5
PALETTE_BUDGET = 15

# Where the backward walk stops. 1 = deal anything one move from the elements.
DEFAULT_CUT = 1

# How many routes per rule to resolve before picking one. Bounded because
# `double_displacement` alone can offer several hundred variants of the same
# chemistry, and the shallowest handful already contain the sensible ones.
_ROUTES_CONSIDERED = 24


@dataclass(frozen=True, slots=True)
class Puzzle:
    target: str
    palette: tuple[str, ...]
    cut: int
    ways: int  # forward-verified, not the backward proposal
    proposed: int  # what the backward pass expected, for comparison
    rules: tuple[str, ...]
    setup: dict[str, int]
    examples: dict[str, Reaction]  # one worked reaction per way
    grade: Grade

    @property
    def bonus(self) -> int:
        """Rules the palette enables that the backward pass never planned for."""
        return self.ways - self.proposed


def generate(
    target: str,
    cut: int = DEFAULT_CUT,
    budget: int = PALETTE_BUDGET,
    want: int = WANT_WAYS,
    seed: int | None = None,
) -> Puzzle | None:
    """Deal a hand for `target`, or None if no palette within budget reaches it."""
    net, cost, makers = _global()
    if target not in makers:
        return None

    requirements = _requirements(target, cost, makers, cut, seed)
    if not requirements:
        return None

    palette = _cover(requirements, budget, want, target)
    palette.add(WATER)  # every branch needs it and it is free at any cut
    # Belt and braces. `_resolve` already refuses to walk through the target,
    # so this should never fire -- but a palette containing the trophy is the
    # one defect that cannot be recovered from downstream, because the board
    # silently refuses to select it and the day just plays short.
    palette.discard(target)

    verified = assess(target, tuple(sorted(palette)))
    if verified is None or not verified.accessible:
        return None

    return Puzzle(
        target=target,
        palette=tuple(sorted(palette)),
        cut=cut,
        ways=verified.ways,
        proposed=sum(1 for rule in requirements if requirements[rule] <= palette),
        rules=verified.accessible,
        setup=verified.setup,
        examples=verified.examples,
        grade=verified.grade,
    )


# --------------------------------------------------------------------------
# Backward: what each way costs
# --------------------------------------------------------------------------


def _requirements(
    target: str,
    cost: dict[str, int],
    makers: dict[str, list[Reaction]],
    cut: int,
    seed: int | None,
) -> dict[str, frozenset[str]]:
    """Rule -> the leaf species one of its routes needs.

    Routes are tried shallowest first so a rule is costed by its easiest form.
    A route whose resolution hits a dead end -- a species that is common but has
    no common route of its own, like MgCrO4 -- is skipped rather than dealt, so
    a palette never contains a starting material nobody could have expected.
    """
    by_rule: dict[str, list[Reaction]] = defaultdict(list)
    for reaction in makers[target]:
        if all(is_common(x) for x in reaction.reactants):
            by_rule[rule_slug(reaction.template) or reaction.template].append(reaction)

    shuffler = random.Random(seed)
    home = _elements_in(target)
    requirements: dict[str, frozenset[str]] = {}

    for rule, reactions in by_rule.items():
        shuffler.shuffle(reactions)  # break ties differently each day
        reactions.sort(key=lambda r: max(cost.get(x, 99) for x in r.reactants))

        # Resolving is the expensive step and `double_displacement` can offer
        # hundreds of variants, so only the shallowest few are costed. Among
        # those, prefer the one dragging in fewest foreign elements: this is
        # where AgF and ZnBr2 get into a palette, not in the rule choice.
        costed: list[tuple[int, int, frozenset[str]]] = []
        for reaction in reactions[:_ROUTES_CONSIDERED]:
            leaves = _resolve(reaction.reactants, cost, makers, cut, target)
            if leaves is None:
                continue
            foreign = {e for s in leaves for e in _elements_in(s)} - home - _FREE_ELEMENTS
            costed.append((len(foreign), len(leaves), leaves))

        if costed:
            requirements[rule] = min(costed)[2]
    return requirements


def _resolve(
    species: tuple[str, ...],
    cost: dict[str, int],
    makers: dict[str, list[Reaction]],
    cut: int,
    target: str,
) -> frozenset[str] | None:
    """Walk back to the cut. None if any branch dead-ends above it.

    `target` is refused everywhere, not merely left out of the answer. The board
    will not let anyone select the trophy, so a branch that needs it is dead in
    play whatever this walk decides -- and if the target happens to sit at or
    below the cut, it would otherwise be *dealt*, handing the player a bottle
    they can never pick up. Both readings are the same rule: nothing is made
    from the thing being made.
    """
    leaves: set[str] = set()
    seen: set[str] = set()
    frontier = list(species)

    while frontier:
        current = frontier.pop()
        if current == target:
            return None  # circular: this branch is built out of the trophy
        if current in seen:
            continue
        seen.add(current)

        if cost.get(current, 99) <= cut:
            leaves.add(current)
            continue

        routes = [
            r
            for r in makers.get(current, [])
            if target not in r.reactants and all(is_common(x) for x in r.reactants)
        ]
        if not routes:
            return None  # above the cut and unmakeable from common things
        cheapest = min(routes, key=lambda r: max(cost.get(x, 99) for x in r.reactants))
        frontier += [x for x in cheapest.reactants if x not in seen]

    return frozenset(leaves)


# --------------------------------------------------------------------------
# Set cover: which ways to buy
# --------------------------------------------------------------------------


def _cover(
    requirements: dict[str, frozenset[str]],
    budget: int,
    want: int,
    target: str = "",
) -> set[str]:
    """Greedily buy the cheapest ways until the budget or `want` is reached.

    Cheapest means fewest *new* species, so rules that share substrates with
    what is already dealt come almost free -- which is what keeps a palette at
    ten species while covering seven ways.

    Size alone is not enough. Minimising it will happily buy chromium to save
    one slot, and a baking-soda puzzle that deals `Cr` and `CuBr2` is not a
    puzzle. The second key is how many *foreign elements* a rule drags in --
    elements the target does not itself contain -- which keeps a palette looking
    like a chemistry set assembled for this question. It is a preference only:
    it changes which correct hand is dealt, never whether one is correct.
    """
    palette: set[str] = set()
    remaining = dict(requirements)
    covered = 0
    home = _elements_in(target)

    def price(rule: str) -> tuple[int, int, str]:
        fresh = remaining[rule] - palette
        foreign = {e for s in fresh for e in _elements_in(s)} - home - _FREE_ELEMENTS
        return len(fresh), len(foreign), rule

    while remaining and covered < want:
        rule = min(remaining, key=price)
        candidate = palette | remaining[rule]
        if len(candidate) > budget and palette:
            break
        palette = candidate
        del remaining[rule]
        covered += 1

    # spend whatever budget is left on ways that now cost nothing extra
    for rule, needed in sorted(remaining.items()):
        if needed <= palette:
            continue
        if len(palette | needed) <= budget:
            palette |= needed
    return palette


# Hydrogen and oxygen are never foreign: water, acids and bases carry them into
# every palette regardless of the target, so counting them would flatten the
# preference to nothing.
_FREE_ELEMENTS: frozenset[str] = frozenset({"H", "O"})

_SYMBOL = re.compile(r"[A-Z][a-z]?")


@lru_cache(maxsize=4096)
def _elements_in(formula: str) -> frozenset[str]:
    """Element symbols in a formula. A heuristic for ranking hands, nothing more.

    This is the one place the codebase reads a formula by pattern rather than by
    table lookup, and it is safe here precisely because nothing depends on it
    being right: a miscount picks a slightly worse palette, never an incorrect
    one. Anything load-bearing goes through `chem.data.salts` or ChemPy.
    """
    return frozenset(_SYMBOL.findall(formula))


# --------------------------------------------------------------------------
# The global network, built once
# --------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _global() -> tuple[Network, dict[str, int], dict[str, list[Reaction]]]:
    net = network.build()
    makers: dict[str, list[Reaction]] = defaultdict(list)
    for reaction in net.reactions:
        for product in reaction.products:
            makers[product].append(reaction)
    return net, cheapest_moves(net), makers


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    from chem.difficulty import assess_all
    from chem.rules.display import display_name

    cut = DEFAULT_CUT
    if "--cut" in argv:
        index = argv.index("--cut")
        cut = int(argv[index + 1])
        argv = argv[:index] + argv[index + 2 :]

    if "--sample" in argv:
        index = argv.index("--sample")
        count = int(argv[index + 1])
        graded = assess_all()
        pool = sorted(t for t, a in graded.items() if a.grade is not Grade.UNSUITABLE)
        targets = random.Random(0).sample(pool, min(count, len(pool)))
    else:
        targets = argv or ["CuSO4"]

    for target in targets:
        puzzle = generate(target, cut=cut)
        if puzzle is None:
            print(f"{target}: no palette within budget\n")
            continue
        print(f"{puzzle.target} -- {display_name(puzzle.target)}  [{puzzle.grade.value}]")
        print(f"  find {puzzle.ways} ways   (cut {puzzle.cut}, {puzzle.bonus:+d} unplanned)")
        print(f"  palette ({len(puzzle.palette)}): {' '.join(puzzle.palette)}")
        for rule in puzzle.rules:
            print(f"    move {puzzle.setup[rule]}  {rule}")
        print()
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
