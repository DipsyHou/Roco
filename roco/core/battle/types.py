"""Shared battle model — enums + dataclasses for JSON-friendly state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .extra_action import ExtraActionSlot


class DamageType(str, Enum):
    physical = "physical"
    magical = "magical"
    fixed = "fixed"


class TargetType(str, Enum):
    single_enemy = "single_enemy"
    all_enemies = "all_enemies"
    all_allies = "all_allies"
    single_ally = "single_ally"
    single_ally_on_field = "single_ally_on_field"
    any_on_field = "any_on_field"
    self = "self"
    none = "none"


def targets_allies(tt: TargetType) -> bool:
    """True when the skill's declared range is ally-side (for future hooks / validation)."""
    return tt in (
        TargetType.single_ally,
        TargetType.single_ally_on_field,
        TargetType.all_allies,
    )


def targets_enemies(tt: TargetType) -> bool:
    """True when the skill's declared range is enemy-side."""
    return tt in (TargetType.single_enemy, TargetType.all_enemies)


def requires_target_pick(tt: TargetType) -> bool:
    """True when UI / client must pick a concrete ``targetId`` before submit."""
    return tt in (
        TargetType.single_enemy,
        TargetType.single_ally,
        TargetType.single_ally_on_field,
        TargetType.any_on_field,
    )


class EffectType(str, Enum):
    buff_stat_percent_boost = "buff_stat_percent_boost"
    debuff_stat_percent_reduction = "debuff_stat_percent_reduction"
    buff_stat_flat_boost = "buff_stat_flat_boost"
    debuff_stat_flat_reduction = "debuff_stat_flat_reduction"
    buff_damage_percent_boost = "buff_damage_percent_boost"
    debuff_damage_percent_reduction = "debuff_damage_percent_reduction"
    buff_damage_flat_boost = "buff_damage_flat_boost"
    debuff_damage_flat_reduction = "debuff_damage_flat_reduction"
    debuff_taken_damage_percent_boost = "debuff_taken_damage_percent_boost"
    buff_taken_damage_percent_reduction = "buff_taken_damage_percent_reduction"
    debuff_taken_damage_flat_boost = "debuff_taken_damage_flat_boost"
    buff_taken_damage_flat_reduction = "buff_taken_damage_flat_reduction"
    buff_damage_cap = "buff_damage_cap"
    buff_crit_rate = "buff_crit_rate"
    buff_crit_damage = "buff_crit_damage"
    buff_infusion = "buff_infusion"
    debuff_stun = "debuff_stun"
    buff_debuff_immunity = "buff_debuff_immunity"
    state_channeling_skill = "state_channeling_skill"
    state_warmup = "state_warmup"
    debuff_burn = "debuff_burn"
    debuff_poison = "debuff_poison"
    state_tailwind = "state_tailwind"
    state_wing_guard = "state_wing_guard"
    state_shunt = "state_shunt"
    state_expansion = "state_expansion"
    debuff_freeze = "debuff_freeze"
    debuff_frostbite = "debuff_frostbite"
    debuff_parasite = "debuff_parasite"
    state_lingqi = "state_lingqi"
    state_tongling = "state_tongling"
    buff_skill_energy_cost_reduction = "buff_skill_energy_cost_reduction"
    debuff_skill_energy_cost_increase = "debuff_skill_energy_cost_increase"
    # 巴哈姆特
    state_gangqi = "state_gangqi"
    state_chejia = "state_chejia"
    state_cunjin = "state_cunjin"
    state_quxie = "state_quxie"
    state_zhensha = "state_zhensha"
    state_zhaojia = "state_zhaojia"
    # 帕尔萨斯
    buff_def_pierce = "buff_def_pierce"
    # 梅花德尔勒
    state_jianwu = "state_jianwu"
    state_loudong_baichu = "state_loudong_baichu"
    debuff_flaw = "debuff_flaw"
    # 藤椒小巴
    state_huoli = "state_huoli"
    buff_laziji = "buff_laziji"
    buff_shuizhuyu = "buff_shuizhuyu"


class StatType(str, Enum):
    hp = "hp"
    atk = "atk"
    mag_atk = "magAtk"
    def_ = "def"
    mag_def = "magDef"
    speed = "speed"


class ActionType(str, Enum):
    normal_attack = "normal_attack"
    use_skill = "use_skill"
    gather_energy = "gather_energy"
    skip = "skip"  # 仅眩晕等自动跳过，不回复能量


class BattlePhase(str, Enum):
    waiting_for_action = "waiting_for_action"
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
    special: bool = False
    # True：本次出手会打出伤害段，算「发动攻击」。纯控制/上异常等保持 False。
    launches_attack: bool = False


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
    duration_turns: Optional[int] = None
    stacks: int = 0
    stat_type: Optional[StatType] = None
    value: Optional[float] = None
    damage_type: Optional[DamageType] = None
    channel_phase: Optional[int] = None
    channel_skill_id: Optional[str] = None
    effect_tag: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class BattleSpirit:
    unique_id: str
    template_id: str
    owner_id: str
    name: str
    base_stats: BaseStats
    current_hp: int
    max_hp: int
    slot: int = 1
    charge: float = 0.0
    effects: List[BattleEffect] = field(default_factory=list)
    skill_cooldowns: Dict[str, int] = field(default_factory=dict)
    is_alive: bool = True
    energy: Optional[int] = None
    max_energy: Optional[int] = None
    passive_triggered: Optional[bool] = None
    last_attack_target_id: Optional[str] = None
    card_state: Optional[Dict[str, Any]] = None
    # 对战开始时的生命上限；用于灵气层数上限，局内 max_hp 变化不影响它。
    battle_start_max_hp: Optional[int] = None
    # Spirit-private state that must survive online snapshots
    # (e.g. 藤椒 pending_free / committed_dish).
    sync_attrs: Dict[str, Any] = field(default_factory=dict)


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
    team_energy: int = 10
    max_team_energy: int = 10
    team_energy_spent_tracker: int = 0  # 当前行动回合内消耗的队伍能量（行动开始时清零）


@dataclass
class BattleState:
    battle_id: str
    phase: BattlePhase
    action_count: int
    players: Dict[str, PlayerBattleData]
    active_actor_id: Optional[str] = None
    turn_prepared_actor_id: Optional[str] = None
    active_turn_stunned: bool = False
    # 统一的额外行动队列；队首即当前正在等待玩家操作的额外行动；非空表示当前处在“额外行动期”。
    extra_action_queue: List["ExtraActionSlot"] = field(default_factory=list)
    timeline_preview: List[str] = field(default_factory=list)
    battle_log: List[BattleLogEntry] = field(default_factory=list)
    winner_id: Optional[str] = None
    # Deterministic RNG: server-generated seed + per-domain draw counters.
    rng_seed: str = ""
    rng_counters: Dict[str, int] = field(default_factory=dict)


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
    if "discardHandIndices" in d:
        out["discardHandIndices"] = d["discardHandIndices"]
    if "discard_hand_indices" in d:
        out["discardHandIndices"] = d["discard_hand_indices"]
    if "cardHandIndex" in d:
        out["cardHandIndex"] = d["cardHandIndex"]
    if "card_hand_index" in d:
        out["cardHandIndex"] = d["card_hand_index"]
    if "newCardId" in d:
        out["newCardId"] = d["newCardId"]
    if "new_card_id" in d:
        out["newCardId"] = d["new_card_id"]
    if "consumeHandIndex" in d:
        out["consumeHandIndex"] = d["consumeHandIndex"]
    if "consume_hand_index" in d:
        out["consumeHandIndex"] = d["consume_hand_index"]
    if "consumeHandIndices" in d:
        out["consumeHandIndices"] = d["consumeHandIndices"]
    if "consume_hand_indices" in d:
        out["consumeHandIndices"] = d["consume_hand_indices"]
    if "previewDish" in d:
        out["previewDish"] = bool(d["previewDish"])
    if "preview_dish" in d:
        out["previewDish"] = bool(d["preview_dish"])
    return out
