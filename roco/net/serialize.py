"""BattleState <-> JSON (additive; does not modify battle_types)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from roco.core.battle.extra_action import ExtraActionSlot
from roco.core.battle.types import (
    BaseStats,
    BattleEffect,
    BattleLogEntry,
    BattleLogType,
    BattlePhase,
    BattleSpirit,
    BattleState,
    DamageType,
    EffectType,
    PlayerBattleData,
    StatType,
)


# Bump when the wire shape changes incompatibly. The reader still accepts
# version-less payloads and the legacy snake_case keys for one transition; those
# fallbacks may be removed once all clients emit schemaVersion >= 1.
SCHEMA_VERSION = 1


class SchemaVersionError(ValueError):
    """Payload was produced by an incompatible serializer version."""


def check_schema_version(d: Dict[str, Any]) -> None:
    """Reject payloads this reader cannot parse correctly.

    A newer peer may add or reshape fields we would otherwise read as defaults,
    silently producing a wrong battle state instead of a clear failure. Payloads
    without the key are pre-versioning (treated as 0) and still accepted via the
    legacy fallbacks in the ``*_from_dict`` readers.
    """
    raw = d.get("schemaVersion", d.get("schema_version"))
    if raw is None:
        return
    try:
        version = int(raw)
    except (TypeError, ValueError):
        raise SchemaVersionError(f"无法识别的 schemaVersion: {raw!r}") from None
    if version > SCHEMA_VERSION:
        raise SchemaVersionError(
            f"对战数据版本为 {version}，本端仅支持到 {SCHEMA_VERSION}；请更新客户端。"
        )


def _enum_val(v: Any) -> str:
    return v.value if hasattr(v, "value") else str(v)


def _either(d: Dict[str, Any], camel: str, snake: str) -> Any:
    """Read an optional field, preferring camelCase over the legacy snake_case.

    Uses key presence rather than ``a or b``: falsy-but-meaningful values
    (``False``, ``0``, ``""``) must survive a round trip, and the writer omits
    these fields only when they are ``None``.
    """
    if camel in d:
        return d[camel]
    return d.get(snake)


def effect_to_dict(e: BattleEffect) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "id": e.id,
        "type": _enum_val(e.type),
        "sourceId": e.source_id,
        "durationTurns": e.duration_turns,
        "stacks": e.stacks,
    }
    if e.stat_type is not None:
        d["statType"] = _enum_val(e.stat_type)
    if e.value is not None:
        d["value"] = e.value
    if e.damage_type is not None:
        d["damageType"] = _enum_val(e.damage_type)
    if e.channel_phase is not None:
        d["channelPhase"] = e.channel_phase
    if e.channel_skill_id is not None:
        d["channelSkillId"] = e.channel_skill_id
    if e.effect_tag is not None:
        d["effectTag"] = e.effect_tag
    if e.display_name is not None:
        d["displayName"] = e.display_name
    return d


def effect_from_dict(d: Dict[str, Any]) -> BattleEffect:
    stat_raw = d.get("statType")
    dmg_raw = d.get("damageType")
    effect_type = EffectType(d["type"])
    duration_turns = d.get("durationTurns", d.get("duration_turns"))
    stacks = d.get("stacks", 0)
    old_remaining = d.get("remainingTurns", d.get("remaining_turns"))
    if old_remaining is not None and "durationTurns" not in d and "duration_turns" not in d:
        if effect_type in {
            EffectType.debuff_burn,
            EffectType.debuff_poison,
            EffectType.state_warmup,
            EffectType.state_shunt,
            EffectType.state_expansion,
        }:
            stacks = old_remaining
            duration_turns = None
        else:
            old_value = int(old_remaining)
            duration_turns = None if old_value == -1 else old_value
    return BattleEffect(
        id=d["id"],
        type=effect_type,
        source_id=d.get("sourceId") or d.get("source_id", ""),
        duration_turns=int(duration_turns) if duration_turns is not None else None,
        stacks=int(stacks or 0),
        stat_type=StatType(stat_raw) if stat_raw else None,
        value=d.get("value"),
        damage_type=DamageType(dmg_raw) if dmg_raw else None,
        channel_phase=_either(d, "channelPhase", "channel_phase"),
        channel_skill_id=_either(d, "channelSkillId", "channel_skill_id"),
        effect_tag=_either(d, "effectTag", "effect_tag"),
        display_name=_either(d, "displayName", "display_name"),
    )


def spirit_to_dict(s: BattleSpirit) -> Dict[str, Any]:
    bs = s.base_stats
    d: Dict[str, Any] = {
        "uniqueId": s.unique_id,
        "templateId": s.template_id,
        "ownerId": s.owner_id,
        "name": s.name,
        "baseStats": bs.to_dict(),
        "currentHp": s.current_hp,
        "maxHp": s.max_hp,
        "slot": s.slot,
        "charge": s.charge,
        "effects": [effect_to_dict(e) for e in s.effects],
        "skillCooldowns": dict(s.skill_cooldowns),
        "isAlive": s.is_alive,
    }
    if s.energy is not None:
        d["energy"] = s.energy
    if s.max_energy is not None:
        d["maxEnergy"] = s.max_energy
    if s.passive_triggered is not None:
        d["passiveTriggered"] = s.passive_triggered
    if s.last_attack_target_id is not None:
        d["lastAttackTargetId"] = s.last_attack_target_id
    if s.card_state is not None:
        d["cardState"] = s.card_state
    if s.battle_start_max_hp is not None:
        d["battleStartMaxHp"] = s.battle_start_max_hp
    if s.sync_attrs:
        d["syncAttrs"] = dict(s.sync_attrs)
    return d


def spirit_from_dict(d: Dict[str, Any]) -> BattleSpirit:
    bs_d = d.get("baseStats") or d.get("base_stats") or {}
    bs = BaseStats(
        hp=int(bs_d.get("hp", 0)),
        atk=int(bs_d.get("atk", 0)),
        mag_atk=int(bs_d.get("magAtk", bs_d.get("mag_atk", 0))),
        def_=int(bs_d.get("def", bs_d.get("def_", 0))),
        mag_def=int(bs_d.get("magDef", bs_d.get("mag_def", 0))),
        speed=int(bs_d.get("speed", 0)),
    )
    effects_raw = d.get("effects") or []
    card_state = _either(d, "cardState", "card_state")
    return BattleSpirit(
        unique_id=d.get("uniqueId") or d.get("unique_id", ""),
        template_id=d.get("templateId") or d.get("template_id", ""),
        owner_id=d.get("ownerId") or d.get("owner_id", ""),
        name=d.get("name", ""),
        base_stats=bs,
        current_hp=int(d.get("currentHp", d.get("current_hp", 0))),
        max_hp=int(d.get("maxHp", d.get("max_hp", 0))),
        slot=int(d.get("slot", 1)),
        charge=float(d.get("charge", 0.0)),
        effects=[effect_from_dict(e) for e in effects_raw],
        skill_cooldowns=dict(d.get("skillCooldowns") or d.get("skill_cooldowns") or {}),
        is_alive=bool(d.get("isAlive", d.get("is_alive", True))),
        energy=_either(d, "energy", "energy"),
        max_energy=_either(d, "maxEnergy", "max_energy"),
        passive_triggered=_either(d, "passiveTriggered", "passive_triggered"),
        last_attack_target_id=_either(d, "lastAttackTargetId", "last_attack_target_id"),
        card_state=card_state,
        battle_start_max_hp=_either(d, "battleStartMaxHp", "battle_start_max_hp"),
        sync_attrs=dict(_either(d, "syncAttrs", "sync_attrs") or {}),
    )


def log_to_dict(l: BattleLogEntry) -> Dict[str, Any]:
    return {
        "type": _enum_val(l.type),
        "turn": l.turn,
        "message": l.message,
        "data": l.data,
    }


def log_from_dict(d: Dict[str, Any]) -> BattleLogEntry:
    return BattleLogEntry(
        type=BattleLogType(d["type"]),
        turn=int(d.get("turn", 0)),
        message=d.get("message", ""),
        data=d.get("data"),
    )


def player_to_dict(p: PlayerBattleData) -> Dict[str, Any]:
    return {
        "playerId": p.player_id,
        "spirits": [spirit_to_dict(s) for s in p.spirits],
        "teamEnergy": p.team_energy,
        "maxTeamEnergy": p.max_team_energy,
        "teamEnergySpentTracker": p.team_energy_spent_tracker,
    }


def player_from_dict(d: Dict[str, Any]) -> PlayerBattleData:
    spirits_raw = d.get("spirits") or []
    return PlayerBattleData(
        player_id=d.get("playerId") or d.get("player_id", ""),
        spirits=[spirit_from_dict(s) for s in spirits_raw],
        team_energy=int(d.get("teamEnergy", d.get("team_energy", 10))),
        max_team_energy=int(d.get("maxTeamEnergy", d.get("max_team_energy", 10))),
        team_energy_spent_tracker=int(
            d.get("teamEnergySpentTracker", d.get("team_energy_spent_tracker", 0))
        ),
    )


def state_to_dict(state: BattleState) -> Dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "battleId": state.battle_id,
        "phase": _enum_val(state.phase),
        "actionCount": state.action_count,
        "players": {pid: player_to_dict(pd) for pid, pd in state.players.items()},
        "activeActorId": state.active_actor_id,
        "turnPreparedActorId": state.turn_prepared_actor_id,
        "activeTurnStunned": state.active_turn_stunned,
        "extraActionQueue": [s.to_dict() for s in state.extra_action_queue],
        "timelinePreview": list(state.timeline_preview),
        "battleLog": [log_to_dict(l) for l in state.battle_log],
        "winnerId": state.winner_id,
        "rngSeed": state.rng_seed,
        "rngCounters": dict(state.rng_counters),
    }


def _extra_queue_from_raw(d: Dict[str, Any]) -> list:
    raw = d.get("extraActionQueue") or d.get("extra_action_queue") or []
    return [ExtraActionSlot.from_dict(s) for s in raw]


def state_from_dict(d: Dict[str, Any]) -> BattleState:
    check_schema_version(d)
    players_raw = d.get("players") or {}
    players = {
        pid: player_from_dict(pd if isinstance(pd, dict) else {"playerId": pid, **pd})
        for pid, pd in players_raw.items()
    }
    logs_raw = d.get("battleLog") or d.get("battle_log") or []
    return BattleState(
        battle_id=d.get("battleId") or d.get("battle_id", ""),
        phase=BattlePhase(d.get("phase", BattlePhase.waiting_for_action.value)),
        action_count=int(d.get("actionCount", d.get("action_count", 0))),
        players=players,
        active_actor_id=d.get("activeActorId") or d.get("active_actor_id"),
        turn_prepared_actor_id=d.get("turnPreparedActorId") or d.get("turn_prepared_actor_id"),
        active_turn_stunned=bool(
            d.get("activeTurnStunned", d.get("active_turn_stunned", False))
        ),
        extra_action_queue=_extra_queue_from_raw(d),
        timeline_preview=list(
            d.get("timelinePreview") or d.get("timeline_preview") or []
        ),
        battle_log=[log_from_dict(l) for l in logs_raw],
        winner_id=d.get("winnerId") or d.get("winner_id"),
        rng_seed=d.get("rngSeed") or d.get("rng_seed") or "",
        rng_counters={
            str(k): int(v)
            for k, v in (d.get("rngCounters") or d.get("rng_counters") or {}).items()
        },
    )
