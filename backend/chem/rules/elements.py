"""Element classification lookups over `chem.data.elements`."""

from __future__ import annotations

from chem.data.elements import AMPHOTERIC_OXIDE_ELEMENTS, IS_METAL, METALLOIDS, NOBLE_GASES


def is_metal(symbol: str) -> bool:
    """True if `symbol` is a metal. Raises KeyError for uncurated elements."""
    try:
        return IS_METAL[symbol]
    except KeyError:
        raise KeyError(f"element {symbol!r} is not in the curated element table") from None


def is_nonmetal(symbol: str) -> bool:
    """True for nonmetals, including noble gases and acidic-oxide metalloids."""
    return not is_metal(symbol)


def is_metalloid(symbol: str) -> bool:
    return symbol in METALLOIDS


def has_amphoteric_oxide(symbol: str) -> bool:
    """True if this element's oxide is amphoteric -- out of scope for v1."""
    return symbol in AMPHOTERIC_OXIDE_ELEMENTS


def is_reactive(symbol: str) -> bool:
    """False for noble gases, which take part in no reaction template."""
    return symbol not in NOBLE_GASES


def is_curated(symbol: str) -> bool:
    return symbol in IS_METAL
