"""呱呱 — 师傅 / 学会了 / 学神。"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from ..battle.events import DamageSource
from ..battle.extra_action import ExtraActionSlot, ExtraActionUI, register_policy
from ..battle.types import (
    BattleLogType,
    ActionType,
    BattleSpirit,
    DamageType,
    EffectType,
    StatType,
    TargetType,
)
from ..battle.utils import get_effective_stat, make_effect
from ._combat import deal_atk_ratio, deal_damage, target_ally, target_enemy
from ..spirit_logic import BattleContext, SpiritLogic

TEMPLATE_ID = "guagua"
LEARNED_USED_KEY = "guagua_learned_used"
LEARNED_TARGET_KEY = "guagua_learned_target_id"
LEARNED_POLICY_ID = "guagua_learned"
LEARNED_SOURCE = "guagua_learned"
BIYOUWOSHI_TAG = "guagua_biyouwoshi"
PASSIVE_ATK_BONUS = 0.10
PASSIVE_CRIT_RATE_BONUS = 0.20
PASSIVE_CRIT_DAMAGE_BONUS = 50.0
LEARNED_RATIO = 0.48
BAIJIA_RATIO = 1.00
BAIJIA_EXTRA_RATIO = 0.48
XUESHEN_RATIO = 0.32
XUESHEN_DURATION = 5
SPEED_BUFF = 0.10


def _learned_policy(actor: BattleSpirit, action: Dict[str, Any]) -> bool:
    if action.get("type") == ActionType.skip.value:
        return True
    return (
        actor.template_id == TEMPLATE_ID
        and action.get("type") == ActionType.use_skill.value
        and action.get("skillId") == "guagua_learned"
    )


register_policy(
    LEARNED_POLICY_ID,
    _learned_policy,
    ExtraActionUI(
        hint="（呱呱额外行动：自动学会了！）",
        allow_normal_attack=False,
        allow_gather=False,
        allow_skip=True,
        allowed_skill_ids=("guagua_learned",),
    ),
)


def _has_effect(spirit: BattleSpirit, eff_type: EffectType) -> bool:
    return any(effect.type == eff_type for effect in spirit.effects)


def _remove_effects(spirit: BattleSpirit, eff_type: EffectType) -> None:
    spirit.effects = [effect for effect in spirit.effects if effect.type != eff_type]


def _apply_state_once(
    spirit: BattleSpirit,
    eff_type: EffectType,
    source_id: str,
    *,
    display_name: str,
    duration_turns: int | None = None,
) -> None:
    existing = next((effect for effect in spirit.effects if effect.type == eff_type), None)
    if existing:
        existing.source_id = source_id
        existing.duration_turns = duration_turns
        existing.display_name = display_name
        return
    spirit.effects.append(
        make_effect(
            eff_type,
            source_id,
            duration_turns=duration_turns,
            display_name=display_name,
        )
    )


def _refresh_biyouwoshi(master: BattleSpirit, source_id: str, duration_turns: int = 2) -> None:
    """Refresh the temporary buff package learned by the master."""
    master.effects = [effect for effect in master.effects if effect.effect_tag != BIYOUWOSHI_TAG]
    for stat in (StatType.atk, StatType.mag_atk):
        master.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                source_id,
                duration_turns=duration_turns,
                stat_type=stat,
                value=PASSIVE_ATK_BONUS,
                effect_tag=BIYOUWOSHI_TAG,
                display_name="必有我师",
            )
        )
    master.effects.append(
        make_effect(
            EffectType.buff_crit_rate,
            source_id,
            duration_turns=duration_turns,
            value=PASSIVE_CRIT_RATE_BONUS,
            effect_tag=BIYOUWOSHI_TAG,
            display_name="必有我师：暴击率提升30%",
        )
    )
    master.effects.append(
        make_effect(
            EffectType.buff_crit_damage,
            source_id,
            duration_turns=duration_turns,
            value=PASSIVE_CRIT_DAMAGE_BONUS,
            effect_tag=BIYOUWOSHI_TAG,
            display_name="必有我师：暴击效果提升60%",
        )
    )


def _master_on_team(ctx: BattleContext, owner_id: str) -> Optional[BattleSpirit]:
    for ally in ctx.get_all_spirits(owner_id):
        if ally.is_alive and _has_effect(ally, EffectType.state_shifu):
            return ally
    return None


def _bound_master(spirit: BattleSpirit) -> Optional[BattleSpirit]:
    ctx = getattr(spirit, "_stat_engine", None)
    if ctx is None:
        return None
    return _master_on_team(ctx, spirit.owner_id)


def _pending_learned_target(ctx: BattleContext, actor: BattleSpirit) -> Optional[BattleSpirit]:
    target_id = actor.sync_attrs.get(LEARNED_TARGET_KEY)
    if not target_id:
        return None
    target = ctx.find_spirit_anywhere(str(target_id))
    opponent_id = ctx.get_opponent_id(actor.owner_id)
    if target and target.is_alive and target.owner_id == opponent_id:
        return target
    return None


def _master_attack(master: BattleSpirit) -> tuple[float, DamageType]:
    """师傅双攻的较高值及其对应伤害属性：物攻更高→物理，魔攻更高→魔法（相等按物理）。"""
    atk = get_effective_stat(master, StatType.atk)
    mag = get_effective_stat(master, StatType.mag_atk)
    if mag > atk:
        return mag, DamageType.magical
    return atk, DamageType.physical


def _random_attack_target_or_enemy(
    ctx: BattleContext,
    owner_id: str,
    targets: List[BattleSpirit],
    rng,
) -> Optional[BattleSpirit]:
    """从本次攻击的存活目标里随机挑一个；若一个都不存在，则改为随机一个存活敌方精灵。"""
    candidates = [target for target in targets if target.is_alive]
    if not candidates:
        opponent_id = ctx.get_opponent_id(owner_id)
        candidates = [enemy for enemy in ctx.get_active_spirits(opponent_id) if enemy.is_alive]
    if not candidates:
        return None
    return rng.choice(candidates)


class GuaguaLogic(SpiritLogic):
    template_id = TEMPLATE_ID
    SKILLS: ClassVar[Dict[str, str]] = {
        "guagua_learned": "_skill_learned_manual",
        "guagua_skill1": "_skill_serve_tea",
        "guagua_skill2": "_skill_baijia",
        "guagua_skill3": "_skill_xueshen",
    }

    def on_unit_created(self, spirit: BattleSpirit) -> None:
        if spirit.template_id == TEMPLATE_ID:
            spirit.sync_attrs.setdefault(LEARNED_USED_KEY, 0)
            spirit.sync_attrs.setdefault(LEARNED_TARGET_KEY, None)

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        if spirit.template_id != TEMPLATE_ID:
            return
        spirit.sync_attrs[LEARNED_USED_KEY] = 0
        spirit.sync_attrs[LEARNED_TARGET_KEY] = None
        first = next((ally for ally in ctx.get_all_spirits(spirit.owner_id) if ally.slot == 1), None)
        if first is None or first.unique_id == spirit.unique_id:
            return
        _apply_state_once(first, EffectType.state_shifu, spirit.unique_id, display_name="师傅")
        ctx.add_log(
            BattleLogType.passive_triggered,
            f"{spirit.name} 开局拜 {first.name} 为师傅！",
            {"sourceId": spirit.unique_id, "targetId": first.unique_id},
        )

    def on_turn_start(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        del ctx
        if actor.template_id == TEMPLATE_ID:
            actor.sync_attrs[LEARNED_USED_KEY] = 0
            actor.sync_attrs[LEARNED_TARGET_KEY] = None

    def get_stat_percent_bonus(self, spirit: BattleSpirit, stat: StatType) -> float:
        if spirit.template_id != TEMPLATE_ID or stat not in (StatType.atk, StatType.mag_atk):
            return 0.0
        return PASSIVE_ATK_BONUS if _bound_master(spirit) is not None else 0.0

    def get_crit_rate_bonus(
        self, spirit: BattleSpirit, target: Optional[BattleSpirit] = None
    ) -> float:
        del target
        if spirit.template_id != TEMPLATE_ID:
            return 0.0
        return PASSIVE_CRIT_RATE_BONUS if _bound_master(spirit) is not None else 0.0

    def get_crit_damage_bonus(
        self, spirit: BattleSpirit, target: Optional[BattleSpirit] = None
    ) -> float:
        del target
        if spirit.template_id != TEMPLATE_ID:
            return 0.0
        return PASSIVE_CRIT_DAMAGE_BONUS if _bound_master(spirit) is not None else 0.0



    def can_use_skill(self, spirit: BattleSpirit, skill) -> Optional[tuple]:
        if spirit.template_id == TEMPLATE_ID and skill.id == "guagua_learned":
            if spirit.sync_attrs.get(LEARNED_TARGET_KEY):
                return True, ""
            return False, "只能在必有我师的额外行动中使用"
        return None

    def can_execute_action(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        action: Dict[str, Any],
        *,
        in_extra_action: bool,
        stunned: bool,
    ) -> Optional[tuple]:
        del ctx, in_extra_action, stunned
        if actor.template_id != TEMPLATE_ID:
            return None
        if (
            action.get("type") == ActionType.use_skill.value
            and action.get("skillId") == "guagua_skill1"
            and action.get("targetId") == actor.unique_id
        ):
            return (False, "师傅请喝茶不能选择自身为目标")
        return None

    def get_skill_target_type(
        self,
        ctx: BattleContext,
        spirit: BattleSpirit,
        skill,
    ) -> Optional[TargetType]:
        del ctx
        if spirit.template_id == TEMPLATE_ID and skill.id == "guagua_learned" and spirit.sync_attrs.get(LEARNED_TARGET_KEY):
            return TargetType.none
        return None

    def get_attack_launch_targets(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        action: Dict[str, Any],
        skill,
    ) -> Optional[List[BattleSpirit]]:
        if actor.template_id == TEMPLATE_ID and skill.id == "guagua_learned":
            target = _pending_learned_target(ctx, actor)
            return [target] if target is not None else []
        return None

    def execute_normal_attack(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> bool:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return True
        deal_atk_ratio(
            ctx,
            actor,
            target,
            1.0,
            lambda a: f"{actor.name} 对 {target.name} 造成了 {a} 点物理伤害！",
            source=DamageSource.attack,
            crit_rng=ctx.next_rng("guagua_normal_crit", actor.unique_id, target.unique_id),
        )
        if target.is_alive:
            actor.last_attack_target_id = target.unique_id
        return True

    def on_ally_attack(
        self,
        ctx: BattleContext,
        observer: BattleSpirit,
        actor: BattleSpirit,
        action: Dict[str, Any],
        targets: List[BattleSpirit],
    ) -> None:
        del action
        if observer.template_id != TEMPLATE_ID or not observer.is_alive:
            return
        if int(observer.sync_attrs.get(LEARNED_USED_KEY, 0)) >= 1:
            return
        master = _master_on_team(ctx, observer.owner_id)
        if master is None or master.unique_id != actor.unique_id:
            return
        rng = ctx.next_rng("guagua_learned_target", observer.unique_id, actor.unique_id)
        target = _random_attack_target_or_enemy(ctx, observer.owner_id, targets, rng)
        if target is None:
            return
        observer.sync_attrs[LEARNED_USED_KEY] = 1
        observer.sync_attrs[LEARNED_TARGET_KEY] = target.unique_id
        ctx.queue_extra_actions([
            ExtraActionSlot(
                actor_id=observer.unique_id,
                policy_id=LEARNED_POLICY_ID,
                source=LEARNED_SOURCE,
            )
        ])
        ctx.add_log(
            BattleLogType.passive_triggered,
            f"{observer.name} 观察师傅出手，获得一次额外行动，准备自动使用「学会了！」！",
            {"sourceId": observer.unique_id, "teacherId": actor.unique_id, "targetId": target.unique_id},
        )

    def on_attack(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        action: Dict[str, Any],
        targets: List[BattleSpirit],
    ) -> None:
        del action
        if actor.template_id != TEMPLATE_ID or not _has_effect(actor, EffectType.state_xueshen):
            return
        master = _master_on_team(ctx, actor.owner_id)
        if master is None:
            return
        rng = ctx.next_rng("guagua_xueshen_target", actor.unique_id)
        target = _random_attack_target_or_enemy(ctx, actor.owner_id, targets, rng)
        if target is None:
            return
        power, dtype = _master_attack(master)
        raw = power * XUESHEN_RATIO
        dealt = deal_damage(
            ctx,
            master,
            target,
            raw,
            dtype,
            lambda a: f"{actor.name} 的「学神」使师傅 {master.name} 追击 {target.name}，造成了 {a} 点附加伤害！",
            source=DamageSource.additional,
            crit_rng=ctx.next_rng("guagua_xueshen_crit", master.unique_id, target.unique_id),
        )
        if dealt > 0:
            ctx.add_log(
                BattleLogType.passive_triggered,
                f"{actor.name} 的「学神不学形」触发！",
                {"sourceId": actor.unique_id, "teacherId": master.unique_id, "targetId": target.unique_id},
            )

    def _skill_learned_manual(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = _pending_learned_target(ctx, actor) or target_enemy(ctx, player_id, action.get("targetId"))
        if target:
            self._cast_learned(ctx, actor, target)
        actor.sync_attrs[LEARNED_TARGET_KEY] = None

    def _cast_learned(self, ctx: BattleContext, actor: BattleSpirit, target: BattleSpirit) -> None:
        deal_atk_ratio(
            ctx,
            actor,
            target,
            LEARNED_RATIO,
            lambda a: f"{actor.name} 使用「学会了！」对 {target.name} 造成了 {a} 点物理伤害！",
            source=DamageSource.skill,
            crit_rng=ctx.next_rng("guagua_learned_crit", actor.unique_id, target.unique_id),
        )
        master = _master_on_team(ctx, actor.owner_id)
        if master is None:
            return
        _refresh_biyouwoshi(master, actor.unique_id, duration_turns=2)
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{master.name} 获得「必有我师」加成，持续2回合！",
            {"sourceId": actor.unique_id, "targetId": master.unique_id},
        )

    def _skill_serve_tea(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_ally(ctx, player_id, action.get("targetId"))
        if not target or target.unique_id == actor.unique_id:
            allies = [ally for ally in ctx.get_active_spirits(player_id) if ally.unique_id != actor.unique_id]
            if not allies:
                return
            target = allies[0]
        for ally in ctx.get_all_spirits(player_id):
            _remove_effects(ally, EffectType.state_shifu)
        _apply_state_once(target, EffectType.state_shifu, actor.unique_id, display_name="师傅")
        actor.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                actor.unique_id,
                duration_turns=2,
                stat_type=StatType.speed,
                value=SPEED_BUFF,
                display_name="师傅请喝茶",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 请 {target.name} 喝茶，改拜其为师傅，并使自身速度提高10%！",
            {"sourceId": actor.unique_id, "targetId": target.unique_id},
        )

    def _skill_baijia(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        deal_atk_ratio(
            ctx,
            actor,
            target,
            BAIJIA_RATIO,
            lambda a: f"{actor.name} 使用「百家拳法」对 {target.name} 造成了 {a} 点物理伤害！",
            source=DamageSource.skill,
            crit_rng=ctx.next_rng("guagua_baijia_crit", actor.unique_id, target.unique_id),
        )
        if not target.is_alive:
            return
        master = _master_on_team(ctx, actor.owner_id)
        if master is None:
            return
        power, dtype = _master_attack(master)
        deal_damage(
            ctx,
            master,
            target,
            power * BAIJIA_EXTRA_RATIO,
            dtype,
            lambda a: f"{actor.name} 借师傅 {master.name} 之长，对 {target.name} 追加造成了 {a} 点附加伤害！",
            source=DamageSource.additional,
            crit_rng=ctx.next_rng("guagua_baijia_extra_crit", actor.unique_id, target.unique_id),
        )

    def _skill_xueshen(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        _apply_state_once(
            actor,
            EffectType.state_xueshen,
            actor.unique_id,
            display_name="学神",
            duration_turns=XUESHEN_DURATION,
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 获得「学神」状态！",
            {"sourceId": actor.unique_id, "targetId": actor.unique_id},
        )


guagua_logic = GuaguaLogic()
