"""Deterministic, seeded random source for battles.

All in-battle randomness (crit rolls, random targeting, buff purges, card
draws) should flow through here so that a battle is fully reproducible from its
``rng_seed`` plus the ordered sequence of actions. Each *domain* keeps an
independent counter, so unrelated draws don't perturb one another's sequence.
"""

from __future__ import annotations

import random
from typing import Any, Dict


def seeded_random(*parts: Any) -> random.Random:
    """Return a ``random.Random`` seeded by ``parts`` joined with ':'.

    Stable across processes/platforms for the same inputs.
    """
    return random.Random(":".join(str(p) for p in parts))


class RandomSource:
    """Domain-counted RNG bound to a battle seed.

    ``counters`` is a live reference to ``BattleState.rng_counters`` so that
    counter progress is serialized with the battle and replays continue from
    the correct position.
    """

    def __init__(self, seed: str, counters: Dict[str, int]) -> None:
        self._seed = seed
        self._counters = counters

    def next(self, domain: str, *parts: Any) -> random.Random:
        """Advance ``domain``'s counter and return a fresh seeded RNG."""
        n = self._counters.get(domain, 0)
        self._counters[domain] = n + 1
        return seeded_random(self._seed, domain, n, *parts)
