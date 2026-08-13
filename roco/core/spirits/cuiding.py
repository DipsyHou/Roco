"""翠顶夫人 — 技能 & 被动"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List

from ..battle.effects import apply_infusion, has_infusion, purge_random_buff
from ..battle.extra_action import ExtraActionSlot, ExtraActionUI, register_policy
from ..battle.types import BattleLogType, BattleSpirit, DamageType
from ._combat import deal_damage, deal_heal
from ..spirit_logic import BattleContext, DamageSource, SpiritLogic

CUIDING_DANCE_POLICY_ID = "cuiding_dance"


def _cuiding_dance_policy(_actor: BattleSpirit, action: Dict[str, Any]) -> bool:
    """共舞额外行动：与正常回合相同（普攻 / 技能 / 聚能 / 跳过）。"""
    del action
    return True


register_policy(
    CUIDING_DANCE_POLICY_ID,
    _cuiding_dance_policy,
    ExtraActionUI(hint="（共舞额外行动）"),
)


class CuidingLogic(SpiritLogic):
    template_id = "cuiding"
    SKILLS: ClassVar[Dict[str, str]] = {
        "cuiding_skill1": "_skill_warm_current",
        "cuiding_skill2": "_skill_ripple",
        "cuiding_skill3": "_skill_dance",
    }

    def _teammates_excluding_self(
        self, ctx: BattleContext, player_id: str, actor: BattleSpirit
    ) -> List[BattleSpirit]:
        return [
            spirit
            for spirit in ctx.get_active_spirits(player_id)
            if spirit.unique_id != actor.unique_id
        ]

    def _sorted_teammates(
        self, ctx: BattleContext, player_id: str, actor: BattleSpirit
    ) -> List[BattleSpirit]:
        return sorted(
            self._teammates_excluding_self(ctx, player_id, actor),
            key=lambda spirit: spirit.slot,
        )

    def _heal_ally(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        target: BattleSpirit,
        amount: float,
    ) -> int:
        actual = deal_heal(
            ctx,
            actor,
            target,
            amount,
            lambda a: f"{actor.name} 为 {target.name} 回复了 {a} 点血量！",
        )
        if actual > 0 and target.owner_id == player_id and actor.template_id == "cuiding":
            self._trigger_chenjing(ctx, player_id, actor, target)
        return actual

    def _trigger_chenjing(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        target: BattleSpirit,
    ) -> None:
        if has_infusion(target):
            ctx.gain_team_energy(
                player_id,
                1,
                reason="澄净",
                log_type=BattleLogType.passive_triggered,
            )
            return
        apply_infusion(target, actor.unique_id, duration_turns=1)
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{target.name} 获得了浸润（1回合）！",
            {"targetId": target.unique_id},
        )

    def _skill_warm_current(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = ctx.find_spirit_anywhere(action.get("targetId") or "")
        if not target or not target.is_alive or target.owner_id != player_id:
            return
        heal_amount = actor.max_hp * 0.10
        for ally in ctx.get_adjacent_allies(target, player_id):
            self._heal_ally(ctx, player_id, actor, ally, heal_amount)

    def _skill_ripple(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        opponent_id = ctx.get_opponent_id(player_id)
        raw = actor.max_hp * 0.08
        for enemy in ctx.get_active_spirits(opponent_id):
            deal_damage(
                ctx,
                actor,
                enemy,
                raw,
                DamageType.magical,
                lambda a, t=enemy: f"{actor.name} 的涟漪对 {t.name} 造成了 {a} 点魔法伤害！",
                source=DamageSource.skill,
            )
            removed = purge_random_buff(
                enemy, ctx.next_rng("cuiding_ripple", enemy.unique_id)
            )
            if removed:
                ctx.add_log(
                    BattleLogType.effect_removed,
                    f"{enemy.name} 的一个正面效果被驱散了！",
                    {"targetId": enemy.unique_id},
                )

    def _skill_dance(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        teammates = self._sorted_teammates(ctx, player_id, actor)
        heal_amount = actor.max_hp * 0.10
        for ally in ctx.get_active_spirits(player_id):
            self._heal_ally(ctx, player_id, actor, ally, heal_amount)
        ctx.queue_extra_actions([
            ExtraActionSlot(
                actor_id=ally.unique_id,
                policy_id=CUIDING_DANCE_POLICY_ID,
                source="dance",
            )
            for ally in teammates
            if ally.is_alive
        ])
        if teammates:
            names = "、".join(ally.name for ally in teammates)
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{actor.name} 的共舞使 {names} 立刻获得一次额外行动！",
                {"actorId": actor.unique_id},
            )
        for ally in ctx.get_active_spirits(player_id):
            ctx.delay_action(ally, 0.50)
            ctx.add_log(
                BattleLogType.effect_applied,
                f"{ally.name} 的下一回合将延后50%！",
                {"targetId": ally.unique_id},
            )


cuiding_logic = CuidingLogic()
