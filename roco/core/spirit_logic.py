"""Re-exports — prefer ``roco.core.spirits.base`` for new code."""

from __future__ import annotations

from .spirits.base import BattleContext, SpiritLogic

__all__ = ["BattleContext", "SpiritLogic"]


def __getattr__(name: str):
    if name in ("DamageEvent", "DamageSource", "EffectAppliedEvent"):
        from .battle.events import DamageEvent, DamageSource, EffectAppliedEvent

        return {
            "DamageEvent": DamageEvent,
            "DamageSource": DamageSource,
            "EffectAppliedEvent": EffectAppliedEvent,
        }[name]
    raise AttributeError(name)
