"""Battle enum definitions and target helpers."""

from __future__ import annotations

from enum import Enum


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
    """True when the skill's declared range is ally-side."""
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
    state_gangqi = "state_gangqi"
    state_chejia = "state_chejia"
    state_cunjin = "state_cunjin"
    state_quxie = "state_quxie"
    state_zhensha = "state_zhensha"
    state_zhaojia = "state_zhaojia"
    buff_def_pierce = "buff_def_pierce"
    state_jianwu = "state_jianwu"
    debuff_flaw = "debuff_flaw"
    state_huoli = "state_huoli"
    state_shifu = "state_shifu"
    state_xueshen = "state_xueshen"
    buff_laziji = "buff_laziji"
    buff_shuizhuyu = "buff_shuizhuyu"
    state_roudun = "state_roudun"
    # 护盾系统（见 docs/mechanics.md §22 与 battle/shield.py）
    state_shield = "state_shield"
    # 石化刺蜥蜴：硬化肌肤（固伤减免状态）/ 棘皮（受击转盾标记）/ 再生（受击加防减费）
    state_yinghuajifu = "state_yinghuajifu"
    state_jipi = "state_jipi"
    state_zaisheng = "state_zaisheng"
    state_shengen = "state_shengen"
    # 机械方方：多色模块 / 超限模块
    state_module_qianghua = "state_module_qianghua"
    state_module_jisu = "state_module_jisu"
    state_module_diyu = "state_module_diyu"
    state_module_chaoxian = "state_module_chaoxian"


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
    skip = "skip"


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
