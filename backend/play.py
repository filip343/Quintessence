"""The game: find five different ways to make the day's compound.

    python play.py                 a random target
    python play.py CuSO4           a chosen one
    python play.py --cut 0         harder: the palette is elements
    python play.py --demo          a scripted walkthrough

You hold a palette. Mix any two things in it and keep what comes out. Every time
you reach the target by a *different kind of reaction*, that is a new way --
finding the same neutralisation with a different spectator ion does not count
twice, which is the whole point.

There is no fail state and no move limit. `main.py` is the engine workbench;
this is the thing a player would see.
"""

from __future__ import annotations

import random
import sys
from typing import Iterable, Iterator

from chem import network
from chem.balance import balance
from chem.data import ELEMENTAL_FORMULA
from chem.network import cheapest_moves
from chem.difficulty import Grade, assess_all
from chem.generate import DEFAULT_CUT, WANT_WAYS, Puzzle, generate
from chem.reaction import Reaction
from chem.rules import combine, decompose, display_name
from chem.rules.catalogue import rule_slug

PROMPT = "> "

FOUND, MISSING = "[#]", "[ ]"

HELP = """commands
  mix <a> <b>       combine two species  (or just: <a> <b>)
  heat <formula>    what a species does on its own
  list              the inventory
  ways              which kinds of reaction you have found
  target            what you are making, and how it is going
  give up           show the ways you missed
  help, quit"""


def main(argv: list[str]) -> int:
    cut, argv = _take_option(argv, "--cut", DEFAULT_CUT)
    scripted = "--demo" in argv
    names = [a for a in argv if not a.startswith("--")]

    puzzle = _deal(names[0] if names else None, cut)
    if puzzle is None:
        print("could not deal a hand for that target")
        return 1

    source = _scripted(_demo_script(puzzle)) if scripted else _interactive()
    game = Game(puzzle, source)
    game.introduce()

    for line in source:
        if not game.command(line):
            break
    game.finish()
    return 0


class Game:
    def __init__(self, puzzle: Puzzle, source: Iterator[str]) -> None:
        self.puzzle = puzzle
        self.source = source  # `_choose` reads the answer from the same stream
        self.inventory: list[str] = list(puzzle.palette)
        self.found: dict[str, Reaction] = {}
        self.moves = 0
        self.misses = 0

    # -- presentation ----------------------------------------------------

    def introduce(self) -> None:
        target = self.puzzle.target
        print(f"\n  make  {target}   ({display_name(target)})")
        print(f"  find {self.wanted} different ways to make it -- {self.puzzle.ways} exist\n")
        self.show_inventory()
        print("\n  'help' for commands\n")

    @property
    def wanted(self) -> int:
        return min(WANT_WAYS, self.puzzle.ways)

    @property
    def won(self) -> bool:
        return len(self.found) >= self.wanted

    def show_inventory(self) -> None:
        print(f"  you have ({len(self.inventory)}):")
        # the target is shown but flagged -- it is kept so you can see you made
        # it, not so you can build with it. See `_usable`.
        shown = [
            f"{item}*" if item == self.puzzle.target else item for item in self.inventory
        ]
        for index in range(0, len(shown), 5):
            print("    " + "  ".join(f"{item:<10}" for item in shown[index : index + 5]))
        if self.puzzle.target in self.inventory:
            print("    * made it -- kept as your answer, not usable as a reagent")

    def show_ways(self) -> None:
        print(f"  {len(self.found)} of {self.wanted}   {self.grid()}")
        for rule, reaction in self.found.items():
            print(f"    {FOUND} {rule:<26} {_equation(reaction)}")
        if not self.found:
            print("    nothing yet")

    def grid(self) -> str:
        return " ".join(
            [FOUND] * len(self.found) + [MISSING] * max(0, self.wanted - len(self.found))
        )

    # -- commands --------------------------------------------------------

    def command(self, line: str) -> bool:
        """Run one line. False ends the session."""
        head, _, rest = line.strip().partition(" ")
        head, rest = head.lower(), rest.strip()

        if head in ("quit", "exit", "q"):
            return False
        elif head in ("help", "h", "?"):
            print(HELP)
        elif head in ("list", "l", "inventory"):
            self.show_inventory()
        elif head == "ways":
            self.show_ways()
        elif head == "target":
            self.show_target()
        elif head in ("give", "giveup", "reveal"):
            self.reveal()
            return False
        elif head == "heat":
            self.heat(rest)
        elif head == "mix":
            self.mix(rest)
        elif head and not rest:
            print(f"  ? try 'mix {head} <something>' -- 'help' for commands")
        elif head:
            self.mix(f"{head} {rest}")  # bare "NaOH H2SO4" works too
        print()
        return not self.won

    def show_target(self) -> None:
        target = self.puzzle.target
        print(f"  making {target} ({display_name(target)})")
        print(f"  {len(self.found)}/{self.wanted} ways   {self.moves} moves")

    def mix(self, argument: str) -> None:
        parts = argument.replace("+", " ").split()
        if len(parts) != 2:
            print("  usage: mix <a> <b>")
            return
        first, second = (self._resolve(p) for p in parts)
        if first is None or second is None:
            missing = [p for p, f in zip(parts, (first, second)) if f is None]
            print(f"  you do not have: {', '.join(missing)}")
            return
        if not self._usable(first, second):
            return

        reactions = combine(first, second)
        if not reactions:
            self.misses += 1
            print(f"  {first} + {second}  ->  no reaction")
            return
        self._apply(reactions)

    def heat(self, argument: str) -> None:
        species = self._resolve(argument)
        if species is None:
            print(f"  you do not have {argument}")
            return
        if not self._usable(species):
            return
        reactions = decompose(species)
        if not reactions:
            self.misses += 1
            print(f"  heating {species} does nothing")
            return
        self._apply(reactions)

    def reveal(self) -> None:
        """Every way, worked. The teaching moment -- so play it either way."""
        target = self.puzzle.target
        missed = [r for r in self.puzzle.rules if r not in self.found]
        print(f"  every way to make {target} from this palette:\n")
        for rule in self.puzzle.rules:
            yours = self.found.get(rule)
            mark = FOUND if yours else MISSING
            # Show the player's own equation where they found one: the same rule
            # with their spectator ions is the version they will recognise.
            reaction = yours or self.puzzle.examples.get(rule)
            print(f"    {mark} {rule}")
            if reaction is not None:
                print(f"        {_equation(reaction)}")
                if reaction.note:
                    print(f"        {reaction.note}")
        if missed:
            print(f"\n  {len(missed)} you did not find")

    # -- the loop --------------------------------------------------------

    def _apply(self, reactions: list[Reaction]) -> None:
        reaction = self._choose(reactions)
        if reaction is None:
            return
        self.moves += 1
        print(f"  {_equation(reaction)}")
        if reaction.note:
            print(f"      {reaction.note}")
        for product in reaction.products:
            if product not in self.inventory:
                self.inventory.append(product)
        self._score(reaction)

    def _choose(self, reactions: list[Reaction]) -> Reaction | None:
        """One move, one product. Which one is the player's decision.

        A triprotic acid with a base gives three different salts and burning a
        multivalent metal gives two: the engine has no amounts, so it offers
        every product the tables support rather than picking for you. Taking all
        of them would hand over several species for one move -- and would score
        a way you never chose.
        """
        if len(reactions) == 1:
            return reactions[0]

        print(f"  {len(reactions)} products are possible:")
        for index, reaction in enumerate(reactions, start=1):
            held = "*" if reaction.product in self.inventory else " "
            print(f"   {held}{index}) {reaction.product:<12} {_equation(reaction)}")
            if reaction.note:
                print(f"          {reaction.note}")
        print(f"  which one? [1-{len(reactions)}, n = change your mind]")

        answer = next(self.source, "n").strip().lower()
        if answer.isdigit() and 1 <= int(answer) <= len(reactions):
            return reactions[int(answer) - 1]
        print("  nothing taken")
        return None

    def _score(self, reaction: Reaction) -> None:
        """Credit a new way if this reaction made the target by a fresh rule."""
        if self.puzzle.target not in reaction.products:
            return
        rule = rule_slug(reaction.template) or reaction.template
        if rule in self.found:
            print(f"      {self.puzzle.target}, but you already have {rule}")
            return
        self.found[rule] = reaction
        print(f"      NEW WAY -- {rule}   ({len(self.found)}/{self.wanted})")
        print(f"      {self.grid()}")

    def finish(self) -> None:
        if not self.won:
            return
        target = self.puzzle.target
        print(f"  {target} -- {len(self.found)}/{self.wanted} ways in {self.moves} moves")
        print(f"  {self.grid()}\n")
        self.reveal()
        extra = len(self.puzzle.rules) - len(self.found)
        if extra > 0:
            print(f"\n  {extra} more way(s) exist -- keep going for the leaderboard")

    def _usable(self, *species: str) -> bool:
        """The target is a trophy, not a reagent.

        `Na2SO4 + H2SO4 -> NaHSO4` and then `NaHSO4 + NaOH -> Na2SO4` is two
        real reactions and a fake way: it consumes the target to produce the
        target, so it shows nothing about how to make it. Any route needing the
        target is circular by definition, which is why refusing it as an input
        costs no legitimate route -- if NaHSO4 is reachable honestly, that way
        still counts.
        """
        if self.puzzle.target not in species:
            return True
        print(f"  {self.puzzle.target} is what you are making -- you cannot build with it")
        print("    a route that consumes the target is not a way to make it")
        return False

    def _resolve(self, text: str) -> str | None:
        if not text:
            return None
        for item in self.inventory:
            if item.lower() == text.lower():
                return item
        elemental = ELEMENTAL_FORMULA.get(text.capitalize())
        return elemental if elemental in self.inventory else None


# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------


def _deal(target: str | None, cut: int) -> Puzzle | None:
    if target is not None:
        return generate(target, cut=cut)
    graded = assess_all()
    pool = sorted(t for t, a in graded.items() if a.grade is not Grade.UNSUITABLE)
    for candidate in random.sample(pool, min(20, len(pool))):
        puzzle = generate(candidate, cut=cut)
        if puzzle is not None and puzzle.ways >= WANT_WAYS:
            return puzzle
    return None


def _demo_script(puzzle: Puzzle) -> list[str]:
    """A walkthrough that really solves the hand, whatever was dealt.

    Built from the palette's own network rather than hardcoded, so `--demo`
    stays honest for any target: if the generator deals a hand the engine cannot
    actually solve, this produces a short script and the demo visibly fails
    rather than printing a scripted success.
    """
    net = network.build(puzzle.palette)
    cost = cheapest_moves(net)

    makers: dict[str, list[Reaction]] = {}
    finals: dict[str, Reaction] = {}
    for reaction in net.reactions:
        for product in reaction.products:
            makers.setdefault(product, []).append(reaction)
        if puzzle.target in reaction.products:
            rule = rule_slug(reaction.template) or reaction.template
            best = finals.get(rule)
            if best is None or _depth(reaction, cost) < _depth(best, cost):
                finals[rule] = reaction

    lines = ["target", "list"]
    have = set(puzzle.palette)
    for rule in puzzle.rules[:WANT_WAYS]:
        reaction = finals.get(rule)
        if reaction is not None:
            lines += _steps(reaction, have, makers, cost)
    return lines + ["ways"]


def _steps(
    reaction: Reaction,
    have: set[str],
    makers: dict[str, list[Reaction]],
    cost: dict[str, int],
    depth: int = 0,
) -> list[str]:
    """Commands that build this reaction's substrates, then fire it."""
    if depth > 6:
        return []
    lines: list[str] = []
    for substrate in reaction.reactants:
        if substrate in have:
            continue
        options = [r for r in makers.get(substrate, []) if r is not reaction]
        if not options:
            continue
        lines += _steps(
            min(options, key=lambda r: _depth(r, cost)), have, makers, cost, depth + 1
        )
    # The script has to answer its own pick prompts, or every multi-product
    # move eats the next command line and the walkthrough desynchronises.
    if len(reaction.reactants) == 1:
        lines.append(f"heat {reaction.reactants[0]}")
        offered = decompose(reaction.reactants[0])
    else:
        lines.append(f"mix {' '.join(reaction.reactants)}")
        offered = combine(*reaction.reactants)

    if len(offered) > 1:
        choice = next(
            (i for i, r in enumerate(offered, start=1) if r.products == reaction.products),
            1,
        )
        lines.append(str(choice))

    have.update(reaction.products)
    return lines


def _depth(reaction: Reaction, cost: dict[str, int]) -> int:
    return max((cost.get(x, 99) for x in reaction.reactants), default=99)


def _equation(reaction: Reaction) -> str:
    balanced = balance(reaction)
    return balanced.equation() if balanced else reaction.equation()


def _take_option(argv: list[str], flag: str, default: int) -> tuple[int, list[str]]:
    if flag not in argv:
        return default, argv
    index = argv.index(flag)
    return int(argv[index + 1]), argv[:index] + argv[index + 2 :]


def _interactive() -> Iterator[str]:
    while True:
        try:
            yield input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            return


def _scripted(lines: Iterable[str]) -> Iterator[str]:
    for line in lines:
        print(f"{PROMPT}{line}")
        yield line


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
