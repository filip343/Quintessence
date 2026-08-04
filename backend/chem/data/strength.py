"""One strength scale, shared by acids and bases.

Coarse bands, fine enough to order displacement and no finer. A stronger acid
drives a weaker one out of its salt; the same holds for bases.
"""

from __future__ import annotations

from enum import Enum


class Strength(Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    VERY_WEAK = "very weak"

    @property
    def rank(self) -> int:
        return _RANK[self]


_RANK: dict[Strength, int] = {
    Strength.STRONG: 3,
    Strength.MODERATE: 2,
    Strength.WEAK: 1,
    Strength.VERY_WEAK: 0,
}
