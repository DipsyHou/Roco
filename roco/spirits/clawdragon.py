"""锐爪龙 — 技能 & 被动"""

from __future__ import annotations

import random
from typing import Any, Dict

from ..battle_types import ActionType, BattleLogType, EffectType, BattleSpirit
from ..battle_utils import make_effect
from ..spirit_logic import BattleContext, SpiritLogic


class ClawdragonLogic(SpiritLogic):
    template_id = "clawdragon"

    def execute_skill(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        sk = action.get("skillId")
        if sk == "clawdragon_skill1":
            self._skill_enhance(ctx, actor)
        elif sk == "clawdragon_skill2":
            self._skill_stun(ctx, actor)
        elif sk == "clawdragon_skill3":
            self._skill_aoe(ctx, actor)

    def on_after_skill(self, ctx: BattleContext, player_id: str, actor: BattleSpirit) -> None:
        opponent_id = ctx.get_opponent_id(player_id)
        enemy_field = ctx.get_field_spirits(opponent_id)
        if not enemy_field:
            return
        random_target = random.choice(enemy_field)
        ctx.add_log(
            BattleLogType.passive_triggered,
            f"{actor.name} 的追击本能触发，自动追击 {random_target.name}！",
            {"actorId": actor.unique_id, "targetId": random_target.unique_id},
        )
        ctx.execute_normal_attack(
            player_id,
            {
                "type": ActionType.normal_attack.value,
                "playerId": player_id,
                "actorId": actor.unique_id,
                "targetId": random_target.unique_id,
            },
            True,
        )

    def _skill_enhance(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        actor.effects.append(
            make_effect(
                EffectType.attack_enhance,
                actor.unique_id,
                remaining_turns=4,
                is_debuff=False,
                enhance_type="magic_damage",
                magic_damage_ratio=1.5,
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 强化了普攻，额外造成魔法伤害！持续3回合。",
            {"targetId": actor.unique_id},
        )

    def _skill_stun(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        actor.effects.append(
            make_effect(
                EffectType.attack_enhance,
                actor.unique_id,
                remaining_turns=-1,
                is_debuff=False,
                enhance_type="stun",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 的下一次主动普攻将附带眩晕效果！",
            {"targetId": actor.unique_id},
        )

    def _skill_aoe(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        actor.effects.append(
            make_effect(
                EffectType.attack_enhance,
                actor.unique_id,
                remaining_turns=-1,
                is_debuff=False,
                enhance_type="aoe",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 的下一次主动普攻将打击全体敌人！",
            {"targetId": actor.unique_id},
        )


clawdragon_logic = ClawdragonLogic()
