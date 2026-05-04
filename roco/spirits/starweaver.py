"""星能使 — 技能 & 被动（全局共振在 engine 中实现）"""

from __future__ import annotations

from typing import Any, Dict

from ..battle_types import BattleLogType, EffectType, BattleSpirit
from ..battle_utils import apply_damage, make_effect, purge_debuffs
from ..spirit_logic import BattleContext, SpiritLogic


class StarweaverLogic(SpiritLogic):
    template_id = "starweaver"

    def on_init(self, spirit: BattleSpirit) -> None:
        spirit.energy = 4
        spirit.max_energy = 8

    def execute_skill(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        opponent_id = ctx.get_opponent_id(player_id)
        sk = action.get("skillId")
        if sk == "starweaver_skill1":
            self._skill_pulse(ctx, actor, opponent_id)
        elif sk == "starweaver_skill2":
            self._skill_purify(ctx, actor, action)
        elif sk == "starweaver_skill3":
            self._skill_burst(ctx, actor, opponent_id)

    def _skill_pulse(self, ctx: BattleContext, actor: BattleSpirit, opponent_id: str) -> None:
        targets = list(ctx.get_field_spirits(opponent_id))
        for target in targets:
            actual = apply_damage(target, 40)
            ctx.add_log(
                BattleLogType.damage_dealt,
                f"{actor.name} 的星能脉冲对 {target.name} 造成了 {actual} 点固伤！",
                {"attackerId": actor.unique_id, "targetId": target.unique_id, "damage": actual},
            )
            if not target.is_alive:
                ctx.add_log(BattleLogType.spirit_defeated, f"{target.name} 被击败了！", {"targetId": target.unique_id})
        gain = len(targets)
        actor.energy = min((actor.energy or 0) + gain, actor.max_energy or 8)
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 回复了 {gain} 点能量！当前能量：{actor.energy}",
            {"targetId": actor.unique_id},
        )

    def _skill_purify(self, ctx: BattleContext, actor: BattleSpirit, action: Dict[str, Any]) -> None:
        tid = action.get("targetId")
        if not tid:
            return
        target = ctx.find_spirit_anywhere(tid)
        if not target or not target.is_alive or not target.is_on_field:
            return
        removed = purge_debuffs(target)
        if removed:
            ctx.add_log(
                BattleLogType.effect_removed,
                f"{target.name} 的 {len(removed)} 个负面效果被净化了！",
                {"targetId": target.unique_id},
            )
        target.effects.append(
            make_effect(
                EffectType.debuff_immunity,
                actor.unique_id,
                remaining_turns=3,
                is_debuff=False,
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{target.name} 获得了2回合负面效果免疫！",
            {"targetId": target.unique_id},
        )

    def _skill_burst(self, ctx: BattleContext, actor: BattleSpirit, opponent_id: str) -> None:
        consumed = getattr(actor, "_starweaver_consumed_energy", 0) or 0
        fixed_dmg = 20 * consumed
        for target in ctx.get_field_spirits(opponent_id):
            actual = apply_damage(target, fixed_dmg)
            ctx.add_log(
                BattleLogType.damage_dealt,
                f"{actor.name} 的星能爆发对 {target.name} 造成了 {actual} 点固伤！",
                {"attackerId": actor.unique_id, "targetId": target.unique_id, "damage": actual},
            )
            if not target.is_alive:
                ctx.add_log(BattleLogType.spirit_defeated, f"{target.name} 被击败了！", {"targetId": target.unique_id})
        actor.is_on_field = False
        ctx.add_log(
            BattleLogType.spirit_withdrawn,
            f"{actor.name} 使用星能爆发后下场了！",
            {"spiritId": actor.unique_id},
        )
        actor.energy = min(4, actor.max_energy or 8)
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 获得了4点能量！",
            {"targetId": actor.unique_id},
        )


starweaver_logic = StarweaverLogic()
