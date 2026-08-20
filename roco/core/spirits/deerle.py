"""梅花德尔勒 — 看破 / 剑花 / 穿刺 / 敏锐

设计确认：
1. 只有普通攻击（不含技能）会清除/扩散「破绽」。
2. 「破绽」持续时间并列最短时，取列表中最靠前（最早存在于 effects 里）的一条。
3. 候选敌人不足两个时，把破绽全部给现有候选（不足两个就给一个）。
4. 「看破」新赋予的破绽与目标已有的破绽是两条独立效果，不覆盖、不叠加。
5. 「漏洞百出」触发的额外行动追加到队列末尾（``queue_extra_actions`` 默认行为）。
6. 剑舞叠层封顶 6 层：达到上限后继续叠加静默吸收，不单独提示（参考巴哈姆特
   招架 ``ZHAOJIA_CAP`` 的处理）。
7. 「漏洞百出」仅对施加者生效；其「伤害提高 25%」走造成伤害加成管线，而非抬高物攻倍率。
8. 普攻仅在已有「剑舞」时叠层；剑舞过期后普攻不会自动重建（需剑花或开局被动）。
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List

from ..battle.effect_meta import stack_count
from ..battle.types import (
    BattleLogType,
    BattleSpirit,
    DamageType,
    EffectType,
    StatType,
)
from ..battle.extra_action import ExtraActionSlot
from ..battle.utils import make_effect
from ..battle.events import DamageSource
from ._combat import deal_atk_ratio, target_enemy
from ..spirit_logic import BattleContext, SpiritLogic

FLAW_DEF_REDUCTION = 0.05
FLAW_DURATION = 3
JIANWU_CAP = 6
JIANWU_ATK_PER_STACK = 0.05
JIANWU_SPEED_PER_STACK = 0.20
JIANWU_DURATION = 5
FLAW_LOUDONG_THRESHOLD = 3
LOUDONG_DAMAGE_BOOST = 0.25
LOUDONG_HIT_TAG = "deerle_loudong_hit"
PIERCE_ATK_RATIO = 1.0
NORMAL_ATK_RATIO = 1.0
KEEN_ATK_RATIO = 0.25


def _get_flaws(spirit: BattleSpirit) -> List[Any]:
    return [e for e in spirit.effects if e.type == EffectType.debuff_flaw]


def _get_jianwu(spirit: BattleSpirit):
    return next((e for e in spirit.effects if e.type == EffectType.state_jianwu), None)


def _get_own_loudong(target: BattleSpirit, actor: BattleSpirit):
    """仅返回由 ``actor`` 施加的「漏洞百出」。"""
    return next(
        (
            e
            for e in target.effects
            if e.type == EffectType.state_loudong_baichu and e.source_id == actor.unique_id
        ),
        None,
    )


def _has_loudong(spirit: BattleSpirit) -> bool:
    return any(e.type == EffectType.state_loudong_baichu for e in spirit.effects)


class DeerleLogic(SpiritLogic):
    template_id = "deerle"
    SKILLS: ClassVar[Dict[str, str]] = {
        "deerle_skill1": "_skill_jianhua",
        "deerle_skill2": "_skill_stab",
        "deerle_skill3": "_skill_keen",
    }

    # --- 生命周期 ---

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        if spirit.template_id != self.template_id:
            return
        spirit.effects.append(
            make_effect(
                EffectType.state_jianwu,
                spirit.unique_id,
                stacks=1,
                duration_turns=JIANWU_DURATION,
                display_name="剑舞",
            )
        )
        opponent_id = ctx.get_opponent_id(spirit.owner_id)
        enemies = ctx.get_active_spirits(opponent_id)
        picked = ctx.next_rng("deerle_open", spirit.unique_id).sample(
            enemies, min(2, len(enemies))
        )
        for enemy in picked:
            self._apply_flaw(ctx, spirit, enemy)

    # --- 能力值加成（剑舞层数）---

    def get_stat_percent_bonus(self, spirit: BattleSpirit, stat: StatType) -> float:
        if spirit.template_id != self.template_id:
            return 0.0
        eff = _get_jianwu(spirit)
        if not eff:
            return 0.0
        stacks = stack_count(eff)
        if stat == StatType.atk:
            return stacks * JIANWU_ATK_PER_STACK
        if stat == StatType.speed:
            return stacks * JIANWU_SPEED_PER_STACK
        return 0.0

    def describe_avatar_badge(self, spirit: BattleSpirit):
        if spirit.template_id != self.template_id:
            return None
        eff = _get_jianwu(spirit)
        stacks = stack_count(eff) if eff else 0
        return ("梅花德尔勒", f"{stacks}/{JIANWU_CAP}")

    # --- 破绽施加 ---

    def _apply_flaw(self, ctx: BattleContext, actor: BattleSpirit, target: BattleSpirit) -> None:
        if not target.is_alive:
            return
        target.effects.append(
            make_effect(
                EffectType.debuff_flaw,
                actor.unique_id,
                stat_type=StatType.def_,
                value=FLAW_DEF_REDUCTION,
                duration_turns=FLAW_DURATION,
                display_name="破绽",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{target.name} 获得了「破绽」（{FLAW_DURATION}回合）！",
            {"targetId": target.unique_id, "sourceId": actor.unique_id},
        )

    def _spread_flaws(self, ctx: BattleContext, actor: BattleSpirit, exclude: BattleSpirit) -> None:
        opponent_id = ctx.get_opponent_id(actor.owner_id)
        candidates = [
            s for s in ctx.get_active_spirits(opponent_id) if s.unique_id != exclude.unique_id
        ]
        picked = ctx.next_rng("deerle_spread", actor.unique_id).sample(
            candidates, min(2, len(candidates))
        )
        for enemy in picked:
            self._apply_flaw(ctx, actor, enemy)

    def _clear_shortest_flaw(self, ctx: BattleContext, target: BattleSpirit) -> None:
        flaws = _get_flaws(target)
        if not flaws:
            return
        shortest = min(
            flaws,
            key=lambda e: e.duration_turns if e.duration_turns is not None else 10**9,
        )
        target.effects.remove(shortest)
        ctx.add_log(
            BattleLogType.effect_removed,
            f"{target.name} 的一条「破绽」被清除了！",
            {"targetId": target.unique_id},
        )

    def _with_loudong_damage_boost(self, actor: BattleSpirit):
        """本次普攻临时挂上造成伤害 +20%，结算后立刻撤掉。"""
        boost = make_effect(
            EffectType.buff_damage_percent_boost,
            actor.unique_id,
            value=LOUDONG_DAMAGE_BOOST,
            damage_type=DamageType.physical,
            effect_tag=LOUDONG_HIT_TAG,
            display_name="漏洞百出",
        )
        actor.effects.append(boost)
        return boost

    def _clear_loudong_hit_boost(self, actor: BattleSpirit) -> None:
        actor.effects = [
            e
            for e in actor.effects
            if not (
                e.type == EffectType.buff_damage_percent_boost
                and e.effect_tag == LOUDONG_HIT_TAG
            )
        ]

    # --- 普通攻击：破绽扩散 + 剑舞叠层 + 漏洞百出判定 ---

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

        loudong = _get_own_loudong(target, actor)
        if loudong is not None:
            self._with_loudong_damage_boost(actor)
        try:
            deal_atk_ratio(
                ctx,
                actor,
                target,
                NORMAL_ATK_RATIO,
                lambda a: f"{actor.name} 对 {target.name} 造成了 {a} 点物理伤害！",
            )
        finally:
            self._clear_loudong_hit_boost(actor)

        actor.last_attack_target_id = target.unique_id

        if loudong is not None and loudong in target.effects:
            target.effects.remove(loudong)
            ctx.add_log(
                BattleLogType.effect_removed,
                f"{target.name} 的「漏洞百出」被触发并解除！",
                {"targetId": target.unique_id},
            )
            ctx.queue_extra_actions(
                [ExtraActionSlot(actor_id=actor.unique_id, source="loudong_baichu")]
            )

        if _get_flaws(target):
            self._clear_shortest_flaw(ctx, target)
            self._spread_flaws(ctx, actor, target)

        # 仅叠层；剑舞过期后需剑花重新开启，普攻不重建
        eff = _get_jianwu(actor)
        if eff:
            eff.stacks = min(JIANWU_CAP, stack_count(eff) + 1)
        return True

    # --- 技能 ---

    def _skill_jianhua(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        eff = _get_jianwu(actor)
        if eff:
            eff.duration_turns = JIANWU_DURATION
            eff.stacks = min(JIANWU_CAP, stack_count(eff) + 1)
        else:
            eff = make_effect(
                EffectType.state_jianwu,
                actor.unique_id,
                stacks=1,
                duration_turns=JIANWU_DURATION,
                display_name="剑舞",
            )
            actor.effects.append(eff)
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 释放了剑花，剑舞层数：{eff.stacks}！",
            {"targetId": actor.unique_id},
        )

    def _skill_stab(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        self._apply_flaw(ctx, actor, target)
        deal_atk_ratio(
            ctx,
            actor,
            target,
            PIERCE_ATK_RATIO,
            lambda a: f"{actor.name} 的穿刺对 {target.name} 造成了 {a} 点物理伤害！",
            source=DamageSource.skill,
        )

    def _skill_keen(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        opponent_id = ctx.get_opponent_id(player_id)
        targets = list(ctx.get_active_spirits(opponent_id))
        for target in targets:
            deal_atk_ratio(
                ctx,
                actor,
                target,
                KEEN_ATK_RATIO,
                lambda a, t=target: f"{actor.name} 的敏锐对 {t.name} 造成了 {a} 点物理伤害！",
                source=DamageSource.skill,
            )
        for target in targets:
            if not target.is_alive:
                continue
            if (
                len(_get_flaws(target)) >= FLAW_LOUDONG_THRESHOLD
                and not _has_loudong(target)
            ):
                target.effects.append(
                    make_effect(
                        EffectType.state_loudong_baichu,
                        actor.unique_id,
                        display_name="漏洞百出",
                    )
                )
                ctx.add_log(
                    BattleLogType.effect_applied,
                    f"{target.name} 获得了「漏洞百出」！",
                    {"targetId": target.unique_id},
                )


deerle_logic = DeerleLogic()
