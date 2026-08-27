"""Lightweight board features for AI scoring."""

from __future__ import annotations

from typing import List

from ..battle.effects import get_total_burn_stacks
from ..battle.shield import has_shield_from
from ..battle.engine import BattleEngine
from ..battle.stats import is_debuff_effect
from ..battle.types import BattleSpirit, EffectType


def hp_ratio(spirit: BattleSpirit) -> float:
    max_hp = max(1, spirit.base_stats.hp)
    return max(0.0, spirit.current_hp) / max_hp


def alive(spirits: List[BattleSpirit]) -> List[BattleSpirit]:
    return [s for s in spirits if s.is_alive]


def allies(engine: BattleEngine, player_id: str) -> List[BattleSpirit]:
    return alive(engine.get_all_spirits(player_id))


def enemies(engine: BattleEngine, player_id: str) -> List[BattleSpirit]:
    return alive(engine.get_all_spirits(engine.get_opponent_id(player_id)))


def lowest_hp_ally(engine: BattleEngine, player_id: str) -> BattleSpirit | None:
    pool = allies(engine, player_id)
    if not pool:
        return None
    return min(pool, key=lambda s: hp_ratio(s))


def lowest_hp_enemy(engine: BattleEngine, player_id: str) -> BattleSpirit | None:
    pool = enemies(engine, player_id)
    if not pool:
        return None
    return min(pool, key=lambda s: (s.current_hp, hp_ratio(s)))


def team_energy(engine: BattleEngine, player_id: str) -> int:
    pd = engine.state.players.get(player_id)
    return pd.team_energy if pd else 0


def debuff_count(spirit: BattleSpirit) -> int:
    return sum(1 for e in spirit.effects if is_debuff_effect(e.type))


def ally_with_most_debuffs(engine: BattleEngine, player_id: str) -> BattleSpirit | None:
    pool = allies(engine, player_id)
    if not pool:
        return None
    best = max(pool, key=lambda s: debuff_count(s))
    return best if debuff_count(best) > 0 else None


def enemy_burn_total(engine: BattleEngine, player_id: str) -> int:
    return sum(get_total_burn_stacks(e) for e in enemies(engine, player_id))


def pick_burn_target(engine: BattleEngine, player_id: str) -> BattleSpirit | None:
    """Prefer an enemy that already has burn, else lowest HP."""
    pool = enemies(engine, player_id)
    if not pool:
        return None
    burned = [e for e in pool if get_total_burn_stacks(e) > 0]
    if burned:
        return max(burned, key=lambda e: get_total_burn_stacks(e))
    return lowest_hp_enemy(engine, player_id)


def offense_score(spirit: BattleSpirit) -> int:
    """Simple carry heuristic used by support AIs."""
    return (spirit.base_stats.atk + spirit.base_stats.mag_atk) * 10 + spirit.base_stats.speed


def sorted_allies_by_offense(engine: BattleEngine, player_id: str) -> List[BattleSpirit]:
    return sorted(
        allies(engine, player_id),
        key=lambda s: (-offense_score(s), -s.base_stats.hp, s.slot, s.unique_id),
    )


def main_c_ally(engine: BattleEngine, player_id: str) -> BattleSpirit | None:
    pool = sorted_allies_by_offense(engine, player_id)
    return pool[0] if pool else None


def has_effect(spirit: BattleSpirit, effect_type: EffectType) -> bool:
    return any(e.type == effect_type for e in spirit.effects)


def ally_missing_shield_from(engine: BattleEngine, player_id: str, source_id: str) -> BattleSpirit | None:
    for spirit in sorted_allies_by_offense(engine, player_id):
        if not has_shield_from(spirit, source_id):
            return spirit
    return None


def all_allies_shielded_from(engine: BattleEngine, player_id: str, source_id: str) -> bool:
    return all(has_shield_from(spirit, source_id) for spirit in allies(engine, player_id))


def lowest_hp_enemy_with_tiebreak(engine: BattleEngine, player_id: str) -> BattleSpirit | None:
    pool = enemies(engine, player_id)
    if not pool:
        return None
    return min(pool, key=lambda s: (hp_ratio(s), s.current_hp, s.slot, s.unique_id))
