"""The reaction network: everything reachable from a set of starting species.

The brief's directed hypergraph, materialised. Each reaction is a hyperedge from
its reactants to its products; the closure below fires every template on every
pair until nothing new appears, which is the same walk the puzzle generator does
when it looks for a shortest hyperpath.

Only new pairs are tried each round -- a pair both of whose members were known
last round was tried last round -- so the cost is the number of *reachable*
pairs, not the number of rounds times all pairs.

`cheapest_moves` is the Dijkstra-style relaxation the brief describes: firing a
reaction costs 1 plus the cost of assembling its inputs. That is what par
measures, and it is here rather than in the generator because it is a property
of the network, not of a puzzle.
"""

from __future__ import annotations

from dataclasses import dataclass

from chem.data.elements import ELEMENTAL_FORMULA
from chem.data.oxides import WATER
from chem.reaction import Reaction
from chem.rules.reactions import combine, decompose

# Every curated element as a species, plus water. Elements no template accepts
# (the noble gases, gold, the metals with no curated ions) simply produce
# nothing and drop out of the closure.
ALL_ELEMENTS: tuple[str, ...] = tuple(sorted(set(ELEMENTAL_FORMULA.values())))

DEFAULT_SEEDS: tuple[str, ...] = ALL_ELEMENTS + (WATER,)


@dataclass(frozen=True, slots=True)
class Network:
    seeds: tuple[str, ...]
    species: tuple[str, ...]  # every species reachable, seeds included
    reactions: tuple[Reaction, ...]

    @property
    def reacting_species(self) -> tuple[str, ...]:
        """Species that take part in at least one reaction, either side."""
        involved = {
            formula
            for reaction in self.reactions
            for formula in reaction.reactants + reaction.products
        }
        return tuple(formula for formula in self.species if formula in involved)


def build(seeds: tuple[str, ...] = DEFAULT_SEEDS) -> Network:
    """Fire every template until no new species appears."""
    known: list[str] = list(dict.fromkeys(seeds))
    seen: set[str] = set(known)
    reactions: dict[tuple[tuple[str, ...], tuple[str, ...]], Reaction] = {}
    frontier = list(known)

    def record(reaction: Reaction) -> list[str]:
        reactions.setdefault((reaction.reactants, reaction.products), reaction)
        return [product for product in reaction.products if product not in seen]

    while frontier:
        fresh: list[str] = []
        for first in frontier:
            for reaction in decompose(first):
                fresh.extend(record(reaction))
            # `known` already contains the frontier, so this covers new+new as
            # well as new+old. Any pair not seen here has two old members and
            # was tried in an earlier round.
            for second in known:
                for reaction in combine(first, second):
                    fresh.extend(record(reaction))
        fresh = [formula for formula in dict.fromkeys(fresh) if formula not in seen]
        seen.update(fresh)
        known.extend(fresh)
        frontier = fresh

    return Network(
        seeds=tuple(seeds),
        species=tuple(sorted(seen)),
        reactions=tuple(reactions.values()),
    )


def cheapest_moves(network: Network) -> dict[str, int]:
    """Minimum reactions to reach each species from the seeds -- the par metric.

    Firing a reaction costs one move plus the cost of assembling its inputs, so
    a product's cost is `max(cost of each reactant) + 1`. Relaxed to a fixed
    point; species the seeds cannot reach are absent from the result.
    """
    cost: dict[str, int] = {formula: 0 for formula in network.seeds}
    changed = True
    while changed:
        changed = False
        for reaction in network.reactions:
            inputs = [cost.get(reactant) for reactant in reaction.reactants]
            if any(value is None for value in inputs):
                continue
            candidate = max(inputs) + 1  # type: ignore[type-var]
            for product in reaction.products:
                if candidate < cost.get(product, candidate + 1):
                    cost[product] = candidate
                    changed = True
    return cost
