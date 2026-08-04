"""A workbench for the reaction rules -- the crafting loop, at the terminal.

    python main.py          interactive
    python main.py --demo   replay a scripted session

Hold an inventory of species, mix two of them, add the product. Anything the
rule templates do not cover reports no reaction, which is the honest answer --
the engine never guesses.

Equations are shown balanced, through ChemPy. A reaction whose coefficients do
not come out as clean positive integers is shown unbalanced with a note rather
than fudged.
"""

from __future__ import annotations

import sys
from typing import Iterable, Iterator

from chem.balance import balance
from chem.data import (
    ACID_FORMULAS,
    ACIDS,
    ACIDS_BY_FORMULA,
    AMMONIA,
    ANHYDRIDES,
    BASES_BY_FORMULA,
    ELEMENT_OF_FORMULA,
    ELEMENTAL_FORMULA,
    HYDRIDES,
    POSITIVE_OXIDATION_STATES,
    WATER,
)
from chem.formulas import parse_charge
from chem.reaction import Reaction
from chem.rules import (
    classify,
    combine,
    decompose,
    ions_of,
    routes_to,
    routes_to_ammonia,
    routes_to_base,
    routes_to_element,
    solubility,
)

PROMPT = "> "

STARTING_INVENTORY: tuple[str, ...] = (
    "H2",
    "O2",
    "N2",
    "Cl2",
    "Br2",
    "I2",
    "S",
    "C",
    "Si",
    "P",
    "Na",
    "K",
    "Mg",
    "Ca",
    "Ba",
    "Al",
    "Fe",
    "Cr",
    "Cu",
    "Zn",
    "Pb",
    "Ag",
    WATER,
)

DEMO_SCRIPT: tuple[str, ...] = (
    # --- an acid, from its element ---
    "mix S O2",  # one element, two anhydrides
    "1",
    "mix SO3 H2O",
    "mix H2 Cl2",  # a hydracid, for later
    # --- a base, two different ways ---
    "mix Na H2O",
    "mix Ca O2",
    "mix CaO H2O",
    "mix Cu O2",
    "1",
    "mix CuO H2O",  # only strong-base oxides hydrate
    # --- salts. a polyprotic acid offers the acid salt too ---
    "mix H2SO4 NaOH",  # neutralisation: normal salt or acid salt
    "1",
    "mix H2SO4 Ca(OH)2",
    "1",
    "info CaSO4",
    "mix Zn H2SO4",  # metal + acid
    "mix Cu H2SO4",  # below hydrogen: nothing
    # --- the oxidation-state policy, same metal, two answers ---
    "mix Fe Cl2",
    "mix Fe H2SO4",
    # --- ion exchange, driven by something coming out of solution ---
    "mix FeCl3 NaOH",
    "mix Na2SO4 FeCl3",  # nothing precipitates, so nothing happens
    # --- carbonate: build it, then take it apart ---
    "mix C O2",
    "1",
    "mix CaO CO2",
    "heat CaCO3",
    # --- ammonia: into an ammonium salt and back out again ---
    "mix H2 N2",
    "mix NH3 H2O",
    "mix NH3 HCl",  # no water -- the gas takes the proton
    "mix NH4Cl NaOH",  # and back out
    "heat NH4OH",
    # --- the halogen order ---
    "mix Na Br2",
    "mix Cl2 NaBr",
    "mix Br2 NaCl",  # wrong way round
    # --- reduction: the only way back to a free metal from an oxide ---
    "mix CuO H2",
    "mix CuO C",
    "mix Al O2",
    "mix Al2O3 C",  # too high in the series for carbon
    "mix Fe O2",
    "1",
    "mix Fe2O3 Al",  # but a more active metal will do it
    # --- acid salts: the same acid, one proton at a time ---
    "mix CO2 H2O",
    "mix H2CO3 NaOH",
    "2",  # take the hydrogencarbonate this time
    "heat NaHCO3",
    # --- chromate <-> dichromate, the longest chain in the game ---
    "mix Cr O2",
    "2",  # CrO3, the acidic one
    "mix CrO3 H2O",
    "mix K H2O",
    "mix H2CrO4 KOH",
    "mix K2CrO4 H2SO4",
    "2",  # the dichromate, not the displaced acid
    "mix K2Cr2O7 KOH",
    "routes Cu",
    "routes NaOH",
    "list",
)

HELP = """commands
  list                  show the inventory
  mix <a> <b>           combine two species; pick a product if several
  heat <formula>        decomposition -- what a species does on its own
  info <formula>        what the engine thinks a species is
  routes <formula>      ways to make an acid, base, metal or ammonia
  acids                 the acid table
  reset                 back to the starting inventory
  help, quit"""


def main(argv: list[str]) -> int:
    scripted = "--demo" in argv
    source = _scripted(DEMO_SCRIPT) if scripted else _interactive()

    print("chemistry workbench -- 'help' for commands\n")
    inventory = list(STARTING_INVENTORY)
    show_inventory(inventory)

    for line in source:
        command, _, rest = line.strip().partition(" ")
        command, rest = command.lower(), rest.strip()

        if command in ("quit", "exit", "q"):
            break
        elif command in ("help", "h", "?"):
            print(HELP)
        elif command in ("list", "l", ""):
            show_inventory(inventory)
        elif command == "reset":
            inventory = list(STARTING_INVENTORY)
            show_inventory(inventory)
        elif command == "acids":
            show_acids()
        elif command == "info":
            show_info(resolve(rest, inventory) or rest)
        elif command == "routes":
            show_routes(resolve(rest, inventory) or rest)
        elif command == "mix":
            do_mix(rest, inventory, source)
        elif command == "heat":
            do_heat(resolve(rest, inventory) or rest, inventory)
        else:
            print(f"  ? unknown command {command!r} -- try 'help'")
        print()

    return 0


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def do_mix(argument: str, inventory: list[str], source: Iterator[str]) -> None:
    parts = argument.replace("+", " ").split()
    if len(parts) != 2:
        print("  usage: mix <a> <b>   e.g. mix N2 O2")
        return

    first, second = (resolve(part, inventory) for part in parts)
    if first is None or second is None:
        missing = [part for part, found in zip(parts, (first, second)) if found is None]
        print(f"  not in the inventory: {', '.join(missing)}")
        return

    reactions = combine(first, second)
    if not reactions:
        print(f"  {first} + {second} -> no reaction")
        print("    no implemented template accepts this pair")
        return

    print(f"  {first} + {second} can give:")
    for index, reaction in enumerate(reactions, start=1):
        marker = " " if reaction.product not in inventory else "*"
        print(f"   {marker}{index}) {reaction.product:<8} {reaction.note}".rstrip())
        print(f"        {equation(reaction)}   [{reaction.template}]")

    chosen = pick(reactions, source)
    for reaction in chosen:
        for product in reaction.products:
            if product in inventory:
                print(f"  already had {product}")
            else:
                inventory.append(product)
                print(f"  + {product} added to the inventory")


def pick(reactions: list[Reaction], source: Iterator[str]) -> list[Reaction]:
    """Ask which product to keep. One reaction needs no asking."""
    if len(reactions) == 1:
        return reactions

    print(f"  which product? [1-{len(reactions)}, a=all, n=none]")
    answer = next(source, "n").strip().lower()

    if answer in ("a", "all"):
        return reactions
    if answer.isdigit() and 1 <= int(answer) <= len(reactions):
        return [reactions[int(answer) - 1]]
    return []


def show_inventory(inventory: list[str]) -> None:
    print(f"  inventory ({len(inventory)}):")
    for index in range(0, len(inventory), 6):
        print("    " + "  ".join(f"{item:<8}" for item in inventory[index : index + 6]))


def do_heat(species: str, inventory: list[str]) -> None:
    reactions = decompose(species)
    if not reactions:
        print(f"  heating {species} does nothing the engine models")
        return
    for reaction in reactions:
        print(f"  {equation(reaction)}   [{reaction.template}]")
        for product in reaction.products:
            if product in inventory:
                print(f"  already had {product}")
            else:
                inventory.append(product)
                print(f"  + {product} added to the inventory")


def show_info(formula: str) -> None:
    species_class = classify(formula)
    print(f"  {formula} -- {species_class.value}")

    element = ELEMENT_OF_FORMULA.get(formula)
    if element is not None:
        states = POSITIVE_OXIDATION_STATES.get(element, ())
        shown = ", ".join(f"+{state}" for state in states) or "none"
        print(f"    element {element}; oxidation states in oxides: {shown}")

    anhydride = ANHYDRIDES.get(formula)
    if anhydride is not None:
        acid = ACIDS.get(anhydride.anion)
        print(f"    {anhydride.name} -- anhydride of {acid.name if acid else '?'}")
        if not anhydride.hydrates:
            print("    does NOT hydrate; its acid needs the salt route")

    acid = ACIDS_BY_FORMULA.get(formula)
    if acid is not None:
        protons = -parse_charge(acid.anion)
        print(
            f"    {acid.name} -- {acid.strength.value}, {protons} acidic H, anion {acid.anion}"
        )
        if acid.decomposes_to:
            print(f"    unstable: falls apart into {' + '.join(acid.decomposes_to)}")

    base = BASES_BY_FORMULA.get(formula)
    if base is not None:
        print(f"    {base.name} -- {base.strength.value}, cation {base.cation}")
        if base.decomposes_to:
            print(f"    unstable: falls apart into {' + '.join(base.decomposes_to)}")

    ions = ions_of(formula)
    if ions is not None:
        cation, anion = ions
        print(f"    ions: {cation} + {anion} -- {solubility(cation, anion).value}")


def show_routes(formula: str) -> None:
    element = ELEMENT_OF_FORMULA.get(formula)
    routes = (
        routes_to(formula)
        or routes_to_base(formula)
        or (routes_to_ammonia() if formula == AMMONIA else [])
        or (routes_to_element(element) if element is not None else [])
    )
    if not routes:
        print(f"  nothing in the tables says how to make {formula}")
        return

    record = (
        ACIDS_BY_FORMULA.get(formula)
        or BASES_BY_FORMULA.get(formula)
        or HYDRIDES.get(formula)
    )
    title = formula if record is None else f"{formula} ({record.name})"
    print(f"  {title} can be made by:")
    for route in routes:
        print(f"    - {route}")


def show_acids() -> None:
    print(f"  acids ({len(ACIDS)}):")
    for anion, acid in ACIDS.items():
        tier = " " if acid.common else "."
        stability = "" if acid.stable else f"  unstable -> {' + '.join(acid.decomposes_to)}"
        print(
            f"   {tier} {ACID_FORMULAS[anion]:<9} {acid.name:<22}"
            f" {acid.strength.value:<10} {anion}{stability}"
        )


# --------------------------------------------------------------------------
# Input plumbing
# --------------------------------------------------------------------------


def equation(reaction: Reaction) -> str:
    """The balanced equation, or the unbalanced one with a note if it will not."""
    balanced = balance(reaction)
    if balanced is not None:
        return balanced.equation()
    return f"{reaction.equation()}   (does not balance cleanly)"


def resolve(text: str, inventory: list[str]) -> str | None:
    """Match user input to an inventory species. Accepts "n2", "N", "H2O"."""
    if not text:
        return None
    for item in inventory:
        if item.lower() == text.lower():
            return item
    elemental = ELEMENTAL_FORMULA.get(text.capitalize())
    if elemental is not None and elemental in inventory:
        return elemental
    return None


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
