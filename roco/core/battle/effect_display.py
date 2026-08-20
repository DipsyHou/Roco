"""状态栏效果显示：默认可叠加见 is_stackable_effect；能力值逐条、不合并。"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union

from .effect_meta import EffectCategory, effect_category, is_stackable_effect_type, stack_count
from .types import BattleEffect, EffectType

# 文档约定可叠加；其余默认不可叠加（逐条罗列，不用 *）
STACKABLE_BURN = EffectType.debuff_burn
STACKABLE_POISON = EffectType.debuff_poison
STACKABLE_FREEZE = EffectType.debuff_freeze
STACKABLE_WARMUP = EffectType.state_warmup
STACKABLE_GANGQI = EffectType.state_gangqi
STACKABLE_QUXIE = EffectType.state_quxie
STACKABLE_ZHENSHA = EffectType.state_zhensha
STACKABLE_ZHAOJIA = EffectType.state_zhaojia
STACKABLE_JIANWU = EffectType.state_jianwu
STACKABLE_HUOLI = EffectType.state_huoli

_STAT_NAMES: Dict[str, str] = {
    "atk": "物攻",
    "magAtk": "魔攻",
    "def": "物防",
    "magDef": "魔防",
    "speed": "速度",
    "hp": "HP",
}

def is_stackable_effect(eff: BattleEffect) -> bool:
    """状态栏合并显示的可叠加效果；能力值变化永不可叠加。"""
    if _is_stat_percent_effect(eff):
        return False
    return is_stackable_effect_type(eff.type)


def _effect_category(eff: BattleEffect) -> EffectCategory:
    return effect_category(eff.type)


def _is_stat_percent_effect(eff: BattleEffect) -> bool:
    return eff.type in (
        EffectType.buff_stat_percent_boost,
        EffectType.debuff_stat_percent_reduction,
    )


def _is_damage_percent_effect(eff: BattleEffect) -> bool:
    return eff.type in (
        EffectType.buff_damage_percent_boost,
        EffectType.debuff_damage_percent_reduction,
    )


def _is_stat_flat_effect(eff: BattleEffect) -> bool:
    return eff.type in (
        EffectType.buff_stat_flat_boost,
        EffectType.debuff_stat_flat_reduction,
    )


def _is_damage_flat_effect(eff: BattleEffect) -> bool:
    return eff.type in (
        EffectType.buff_damage_flat_boost,
        EffectType.debuff_damage_flat_reduction,
    )


def _is_taken_damage_flat_effect(eff: BattleEffect) -> bool:
    return eff.type in (
        EffectType.buff_taken_damage_flat_reduction,
        EffectType.debuff_taken_damage_flat_boost,
    )


def _turn_suffix(eff: BattleEffect) -> str:
    if eff.duration_turns is None or eff.duration_turns >= 900:
        return ""
    if eff.duration_turns <= 0:
        return ""
    return f"({eff.duration_turns}回合)"


def _copy_suffix(eff: BattleEffect) -> str:
    """圣域祭司「再现」复制出的负面效果统一追加「(复制)」标记（纯显示层）。"""
    return "(复制)" if eff.effect_tag == "shengyu_replicated" else ""


def _format_stat_percent_body(eff: BattleEffect) -> str:
    """物攻提升20%(3回合) — 不显示技能名。"""
    stat = _STAT_NAMES.get(eff.stat_type.value if eff.stat_type else "", "属性")
    pct = abs(int((eff.value or 0) * 100))
    verb = "提升" if eff.type == EffectType.buff_stat_percent_boost else "降低"
    return f"{stat}{verb}{pct}%{_copy_suffix(eff)}{_turn_suffix(eff)}"


def _format_damage_percent_body(eff: BattleEffect) -> str:
    pct = abs(int((eff.value or 0) * 100))
    verb = "提升" if eff.type == EffectType.buff_damage_percent_boost else "降低"
    return f"伤害{verb}{pct}%{_copy_suffix(eff)}{_turn_suffix(eff)}"


def _format_crit_rate_body(eff: BattleEffect) -> str:
    pct = abs(int((eff.value or 0) * 100))
    verb = "提升" if eff.type == EffectType.buff_crit_rate else "降低"
    return f"暴击率{verb}{pct}%{_copy_suffix(eff)}{_turn_suffix(eff)}"


def _format_crit_damage_body(eff: BattleEffect) -> str:
    pct = abs(int(eff.value or 0))
    verb = "提升" if eff.type == EffectType.buff_crit_damage else "降低"
    return f"暴击效果{verb}{pct}%{_copy_suffix(eff)}{_turn_suffix(eff)}"


def _format_taken_damage_reduction_body(eff: BattleEffect) -> str:
    pct = abs(int((eff.value or 0) * 100))
    return f"受到伤害减少{pct}%{_copy_suffix(eff)}{_turn_suffix(eff)}"


def _format_taken_damage_boost_body(eff: BattleEffect) -> str:
    pct = abs(int((eff.value or 0) * 100))
    kind = "持续伤害" if eff.effect_tag == "sustained_damage" else "伤害"
    name = f"{eff.display_name}：" if eff.display_name else ""
    return f"{name}受到的{kind}提高{pct}%{_copy_suffix(eff)}{_turn_suffix(eff)}"


def _format_stat_flat_body(eff: BattleEffect) -> str:
    """物攻降低12点(3回合) — 固定值版的 ``_format_stat_percent_body``。"""
    stat = _STAT_NAMES.get(eff.stat_type.value if eff.stat_type else "", "属性")
    amount = abs(eff.value or 0)
    verb = "提升" if eff.type == EffectType.buff_stat_flat_boost else "降低"
    return f"{stat}{verb}{amount:g}点{_copy_suffix(eff)}{_turn_suffix(eff)}"


def _format_damage_flat_body(eff: BattleEffect) -> str:
    amount = abs(eff.value or 0)
    verb = "提升" if eff.type == EffectType.buff_damage_flat_boost else "降低"
    return f"伤害{verb}{amount:g}点{_copy_suffix(eff)}{_turn_suffix(eff)}"


def _format_taken_damage_flat_body(eff: BattleEffect) -> str:
    amount = abs(eff.value or 0)
    verb = "减少" if eff.type == EffectType.buff_taken_damage_flat_reduction else "提高"
    return f"受到伤害{verb}{amount:g}点{_copy_suffix(eff)}{_turn_suffix(eff)}"


def _format_skill_energy_cost_reduction_body(eff: BattleEffect) -> str:
    label = eff.display_name or "技能能耗降低"
    amount = int(eff.value or 0)
    if amount > 0 and "降低" not in label and "点" not in label:
        label = f"{label}{amount}点"
    return f"{label}{_turn_suffix(eff)}"


def _format_skill_energy_cost_increase_body(eff: BattleEffect) -> str:
    label = eff.display_name or "技能能耗增加"
    amount = int(eff.value or 0)
    if amount > 0 and "增加" not in label and "点" not in label and "+" not in label:
        label = f"{label}{amount}点"
    return f"{label}{_turn_suffix(eff)}"


def _resolve_display_name(eff: BattleEffect) -> str:
    t = eff.type
    if t == EffectType.debuff_stun:
        return "眩晕"
    if t == STACKABLE_WARMUP:
        return "升温"
    if t == EffectType.state_tailwind:
        return "破风"
    if t == EffectType.state_wing_guard:
        return "羽翼守护"
    if t == EffectType.state_shunt:
        return "分流"
    if t == EffectType.state_expansion:
        return "扩容"
    if t == EffectType.state_lingqi:
        return "灵气"
    if t == EffectType.state_tongling:
        return "通灵"
    if t == EffectType.buff_debuff_immunity:
        return "净化"
    if t == EffectType.state_channeling_skill:
        return "愿力凝聚"
    if t == EffectType.buff_damage_cap:
        return "限伤"
    if t == STACKABLE_BURN:
        return "灼烧"
    if t == STACKABLE_POISON:
        return "中毒"
    if t == STACKABLE_FREEZE:
        return "冰冻"
    if t == EffectType.buff_infusion:
        return "浸润"
    if t == EffectType.state_gangqi:
        return "罡气"
    if t == EffectType.state_chejia:
        return "彻甲"
    if t == EffectType.state_cunjin:
        return "寸劲"
    if t == EffectType.state_quxie:
        return "驱邪"
    if t == EffectType.state_zhensha:
        return "镇煞"
    if t == EffectType.state_zhaojia:
        return "招架"
    if t == EffectType.debuff_flaw:
        return "破绽"
    if t == EffectType.state_huoli:
        return "火力"
    if t == EffectType.state_shifu:
        return "师傅"
    if t == EffectType.state_xueshen:
        return "学神"
    if t == EffectType.buff_laziji:
        return "辣子鸡"
    if t == EffectType.buff_shuizhuyu:
        return "水煮鱼"
    if t == EffectType.buff_damage_percent_boost:
        return "伤害提升"
    if t == EffectType.buff_def_pierce:
        return "恐怖"
    if eff.display_name and not (_is_stat_percent_effect(eff) or _is_damage_percent_effect(eff)):
        return eff.display_name
    return "未知效果"


def _burn_detail(eff: BattleEffect, source_names: Dict[str, str]) -> str:
    src = source_names.get(eff.source_id, "未知")
    return f"来自{src}"


def _stackable_group_key(
    eff: BattleEffect, source_names: Dict[str, str]
) -> Tuple[Union[str, EffectType], ...]:
    if eff.type == STACKABLE_BURN:
        return ("burn", eff.source_id)
    if eff.type == STACKABLE_POISON:
        return ("poison",)
    if eff.type == STACKABLE_FREEZE:
        return ("freeze",)
    if eff.type == STACKABLE_WARMUP:
        return ("warmup",)
    if eff.type == STACKABLE_GANGQI:
        return ("gangqi",)
    if eff.type == STACKABLE_QUXIE:
        return ("quxie",)
    if eff.type == STACKABLE_ZHENSHA:
        return ("zhensha",)
    if eff.type == STACKABLE_ZHAOJIA:
        return ("zhaojia",)
    if eff.type == STACKABLE_JIANWU:
        return ("jianwu", eff.source_id)
    if eff.type == STACKABLE_HUOLI:
        return ("huoli",)
    return ("?",)


def _format_stackable_group(
    effects: List[BattleEffect], source_names: Dict[str, str]
) -> str:
    eff = effects[0]
    category = _effect_category(eff)
    count = len(effects)

    if eff.type == STACKABLE_BURN:
        total = sum(stack_count(e) for e in effects)
        body = f"{_resolve_display_name(eff)} - {_burn_detail(eff, source_names)}"
        mult = f" * {total}"
        return f"[{category}]{body}{mult}"

    if eff.type == STACKABLE_WARMUP:
        total = max(stack_count(e) for e in effects)
        mult = f" * {total}"
        return f"[{category}]{_resolve_display_name(eff)}{mult}"

    if eff.type == STACKABLE_POISON:
        total = sum(stack_count(e) for e in effects)
        mult = f" * {total}"
        return f"[{category}]{_resolve_display_name(eff)}{mult}"

    if eff.type == STACKABLE_FREEZE:
        total = sum(stack_count(e) for e in effects)
        mult = f" * {total}"
        return f"[{category}]{_resolve_display_name(eff)}{mult}"

    if eff.type in (STACKABLE_GANGQI, STACKABLE_QUXIE, STACKABLE_ZHENSHA, STACKABLE_ZHAOJIA):
        total = max(stack_count(e) for e in effects)
        mult = f" * {total}"
        return f"[{category}]{_resolve_display_name(eff)}{mult}"

    if eff.type == STACKABLE_JIANWU:
        total = max(stack_count(e) for e in effects)
        mult = f" * {total}"
        return f"[{category}]{_resolve_display_name(eff)}{mult}{_turn_suffix(eff)}"

    if eff.type == STACKABLE_HUOLI:
        total = max(stack_count(e) for e in effects)
        mult = f" * {total}"
        return f"[{category}]{_resolve_display_name(eff)}{mult}"

    mult = f" * {count}"
    return f"[{category}]{_resolve_display_name(eff)}{mult}"


def _format_one(eff: BattleEffect, source_names: Dict[str, str]) -> str:
    category = _effect_category(eff)

    if _is_stat_percent_effect(eff):
        return f"[{category}]{_format_stat_percent_body(eff)}"
    if _is_damage_percent_effect(eff):
        return f"[{category}]{_format_damage_percent_body(eff)}"
    if eff.type == EffectType.buff_crit_rate:
        return f"[buff]{_format_crit_rate_body(eff)}"
    if eff.type == EffectType.buff_crit_damage:
        return f"[buff]{_format_crit_damage_body(eff)}"
    if _is_stat_flat_effect(eff):
        return f"[{category}]{_format_stat_flat_body(eff)}"
    if _is_damage_flat_effect(eff):
        return f"[{category}]{_format_damage_flat_body(eff)}"
    if _is_taken_damage_flat_effect(eff):
        return f"[{category}]{_format_taken_damage_flat_body(eff)}"
    if eff.type == EffectType.buff_taken_damage_percent_reduction:
        return f"[buff]{_format_taken_damage_reduction_body(eff)}"
    if eff.type == EffectType.debuff_taken_damage_percent_boost:
        return f"[debuff]{_format_taken_damage_boost_body(eff)}"
    if eff.type == EffectType.buff_skill_energy_cost_reduction:
        return f"[buff]{_format_skill_energy_cost_reduction_body(eff)}"
    if eff.type == EffectType.debuff_skill_energy_cost_increase:
        return f"[debuff]{_format_skill_energy_cost_increase_body(eff)}"

    name = _resolve_display_name(eff)
    if eff.type == STACKABLE_BURN:
        body = f"{name} - {_burn_detail(eff, source_names)}"
        total = stack_count(eff)
        mult = f" * {total}"
        return f"[{category}]{body}{mult}"
    if eff.type == STACKABLE_POISON:
        total = stack_count(eff)
        mult = f" * {total}"
        return f"[{category}]{name}{mult}"
    if eff.type == STACKABLE_FREEZE:
        total = stack_count(eff)
        mult = f" * {total}"
        return f"[{category}]{name}{mult}"
    if eff.type in (
        EffectType.state_shunt,
        EffectType.state_expansion,
        EffectType.state_lingqi,
        EffectType.state_gangqi,
        EffectType.state_quxie,
        EffectType.state_zhensha,
        EffectType.state_zhaojia,
        EffectType.state_jianwu,
        EffectType.state_huoli,
    ):
        total = stack_count(eff)
        mult = f" * {total}"
        return f"[{category}]{name}{mult}{_turn_suffix(eff)}"

    if eff.type in (EffectType.state_shifu, EffectType.state_xueshen):
        return f"[{category}]{name}{_turn_suffix(eff)}"

    if eff.type in (EffectType.buff_laziji, EffectType.buff_shuizhuyu):
        pct = abs(int((eff.value or 0) * 100))
        return f"[{category}]{name}：双攻+来源物攻{pct}%{turn if (turn := _turn_suffix(eff)) else ''}"

    turn = _turn_suffix(eff)
    if turn:
        return f"[{category}]{name}{turn}"
    return f"[{category}]{name}"


def format_spirit_effects(
    effects: List[BattleEffect],
    source_names: Dict[str, str],
    spirit: Optional[object] = None,
) -> List[str]:
    """将精灵效果列表格式化为状态栏行。"""
    emitted_stackable: set[Tuple[Union[str, EffectType], ...]] = set()
    lines: List[str] = []

    for eff in effects:
        if not is_stackable_effect(eff):
            lines.append(_format_one(eff, source_names))
            continue

        key = _stackable_group_key(eff, source_names)
        if key in emitted_stackable:
            continue
        emitted_stackable.add(key)
        group = [
            e
            for e in effects
            if is_stackable_effect(e) and _stackable_group_key(e, source_names) == key
        ]
        lines.append(_format_stackable_group(group, source_names))

    if spirit is not None:
        lines.extend(_format_virtual_state_lines(spirit))
    return lines


def _format_virtual_state_lines(spirit: object) -> List[str]:
    """显示不在 effects 内但应展示在状态栏的状态。

    具体内容由各精灵的 ``SpiritLogic.describe_extra_states`` 决定，
    避免本模块随精灵数量增长而堆积 ``template_id`` 特判。
    """
    from ..spirits import get_spirit_logic

    logic = get_spirit_logic(getattr(spirit, "template_id", ""))
    if logic is None:
        return []
    return list(logic.describe_extra_states(spirit))
