"""Shared battle model — enums + dataclasses for JSON-friendly state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DamageType(str, Enum):
    physical = "physical"
    magical = "magical"
    fixed = "fixed"


class TargetType(str, Enum):
    single_enemy = "single_enemy"
    all_enemies = "all_enemies"
    single_ally = "single_ally"
    single_ally_on_field = "single_ally_on_field"
    any_on_field = "any_on_field"
    self = "self"
    none = "none"


class EffectType(str, Enum):
    stat_percent_modify = "stat_percent_modify"
    stat_flat_modify = "stat_flat_modify"
    stun = "stun"
    damage_modify = "damage_modify"
    attack_enhance = "attack_enhance"
    next_damage_reduction = "next_damage_reduction"
    debuff_immunity = "debuff_immunity"
    channeling_skill = "channeling_skill"


class StatType(str, Enum):
    hp = "hp"
    atk = "atk"
    mag_atk = "magAtk"
    def_ = "def"
    mag_def = "magDef"
    speed = "speed"


class DamageModifySubType(str, Enum):
    physical_increase = "physical_increase"
    physical_decrease = "physical_decrease"
    magical_increase = "magical_increase"
    magical_decrease = "magical_decrease"
    all_increase = "all_increase"
    all_decrease = "all_decrease"


class ActionType(str, Enum):
    normal_attack = "normal_attack"
    use_skill = "use_skill"
    deploy = "deploy"
    withdraw = "withdraw"
    swap = "swap"
    skip = "skip"


class BattlePhase(str, Enum):
    select_starters = "select_starters"
    waiting_for_actions = "waiting_for_actions"
    processing = "processing"
    finished = "finished"


class BattleLogType(str, Enum):
    turn_start = "turn_start"
    action_executed = "action_executed"
    damage_dealt = "damage_dealt"
    heal_applied = "heal_applied"
    effect_applied = "effect_applied"
    effect_removed = "effect_removed"
    spirit_defeated = "spirit_defeated"
    spirit_deployed = "spirit_deployed"
    spirit_withdrawn = "spirit_withdrawn"
    spirit_swapped = "spirit_swapped"
    passive_triggered = "passive_triggered"
    battle_end = "battle_end"
    stunned = "stunned"


@dataclass
class BaseStats:
    hp: int
    atk: int
    mag_atk: int
    def_: int
    mag_def: int
    speed: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hp": self.hp,
            "atk": self.atk,
            "magAtk": self.mag_atk,
            "def": self.def_,
            "magDef": self.mag_def,
            "speed": self.speed,
        }


@dataclass
class PassiveSkillDef:
    id: str
    name: str
    description: str


@dataclass
class SkillDef:
    id: str
    name: str
    description: str
    cooldown: int
    target_type: TargetType
    energy_cost: Optional[int] = None


@dataclass
class SpiritTemplate:
    id: str
    name: str
    description: str
    base_stats: BaseStats
    passive_skill: PassiveSkillDef
    normal_attack: SkillDef
    skills: List[SkillDef]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "baseStats": self.base_stats.to_dict(),
            "passiveSkill": {
                "id": self.passive_skill.id,
                "name": self.passive_skill.name,
                "description": self.passive_skill.description,
            },
            "normalAttack": {
                "id": self.normal_attack.id,
                "name": self.normal_attack.name,
                "description": self.normal_attack.description,
                "cooldown": self.normal_attack.cooldown,
                "targetType": self.normal_attack.target_type.value,
            },
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "cooldown": s.cooldown,
                    "targetType": s.target_type.value,
                    **({"energyCost": s.energy_cost} if s.energy_cost is not None else {}),
                }
                for s in self.skills
            ],
        }


@dataclass
class BattleEffect:
    id: str
    type: EffectType
    source_id: str
    remaining_turns: int
    is_debuff: bool
    stat_type: Optional[StatType] = None
    value: Optional[float] = None
    damage_modify_sub_type: Optional[DamageModifySubType] = None
    reduction_percent: Optional[float] = None
    enhance_type: Optional[str] = None  # aoe | stun | magic_damage
    magic_damage_ratio: Optional[float] = None
    channel_phase: Optional[int] = None
    channel_skill_id: Optional[str] = None


@dataclass
class BattleSpirit:
    unique_id: str
    template_id: str
    owner_id: str
    name: str
    base_stats: BaseStats
    current_hp: int
    max_hp: int
    effects: List[BattleEffect] = field(default_factory=list)
    skill_cooldowns: Dict[str, int] = field(default_factory=dict)
    is_on_field: bool = False
    is_alive: bool = True
    energy: Optional[int] = None
    max_energy: Optional[int] = None
    passive_triggered: Optional[bool] = None


@dataclass
class BattleLogEntry:
    type: BattleLogType
    turn: int
    message: str
    data: Optional[Dict[str, Any]] = None


@dataclass
class PlayerBattleData:
    player_id: str
    spirits: List[BattleSpirit]
    has_submitted_action: bool = False


@dataclass
class BattleState:
    battle_id: str
    phase: BattlePhase
    current_turn: int
    players: Dict[str, PlayerBattleData]
    battle_log: List[BattleLogEntry] = field(default_factory=list)
    winner_id: Optional[str] = None


def player_action_from_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize client payload to engine shape (camelCase optional)."""
    at = d.get("type") or d.get("actionType")
    out: Dict[str, Any] = {"type": at, "playerId": d.get("playerId") or d.get("player_id")}
    if "actorId" in d:
        out["actorId"] = d["actorId"]
    if "actor_id" in d:
        out["actorId"] = d["actor_id"]
    if "skillId" in d:
        out["skillId"] = d["skillId"]
    if "skill_id" in d:
        out["skillId"] = d["skill_id"]
    if "targetId" in d:
        out["targetId"] = d["targetId"]
    if "target_id" in d:
        out["targetId"] = d["target_id"]
    if "deployId" in d:
        out["deployId"] = d["deployId"]
    if "deploy_id" in d:
        out["deployId"] = d["deploy_id"]
    if "withdrawId" in d:
        out["withdrawId"] = d["withdrawId"]
    if "withdraw_id" in d:
        out["withdrawId"] = d["withdraw_id"]
    return out
