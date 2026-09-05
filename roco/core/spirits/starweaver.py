"""黑猫巫师 — 技能 & 被动"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

from ..battle import messages as msg
from ..battle.types import (
    BattleLogType,
    BattleSpirit,
    DamageType,
    EffectType,
)
from ..battle.utils import make_effect, purge_debuffs
from ._combat import deal_damage, deal_mag_ratio, grant_personal_energy
from ..spirit_logic import BattleContext, DamageSource, SpiritLogic


class StarweaverLogic(SpiritLogic):
    template_id = "starweaver"
    SKILLS: ClassVar[Dict[str, str]] = {
        "starweaver_skill1": "_skill_pulse",
        "starweaver_skill2": "_skill_purify",
        "starweaver_skill3": "_skill_burst",
    }

    def on_unit_created(self, spirit: BattleSpirit) -> None:
        # 开局秘能在 on_battle_start 经统一入口发放，以便吃到月盈等加成。
        spirit.energy = 0
        spirit.max_energy = 8

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        if spirit.template_id != self.template_id:
            return
        grant_personal_energy(ctx, spirit, 4)

    def get_resource_label(self) -> Optional[str]:
        """黑猫巫师用个人秘能付费，不消耗队伍能量。"""
        return "秘能"

    def can_use_skill(self, spirit: BattleSpirit, skill) -> Optional[tuple]:
        if skill.energy_cost is None:
            return None
        ec = skill.energy_cost
        if ec == -1 and (spirit.energy or 0) <= 0:
            return (False, "秘能不足")
        if ec > 0 and (spirit.energy or 0) < ec:
            return (False, f"需要{ec}点秘能")
        return (True, "")

    def consume_skill_resources(self, spirit: BattleSpirit, skill) -> None:
        if skill.energy_cost is None:
            return
        ec = skill.energy_cost
        if ec == -1:
            spirit._consumed_energy = spirit.energy or 0
            spirit.energy = 0
        elif ec > 0:
            spirit.energy = (spirit.energy or 0) - ec

    def should_use_team_energy(self, spirit: BattleSpirit, skill) -> bool:
        return False

    def on_ally_attack(
        self,
        ctx: BattleContext,
        observer: BattleSpirit,
        actor: BattleSpirit,
        action: Dict[str, Any],
        targets: list,
    ) -> None:
        del action, actor
        if observer.template_id != "starweaver" or not observer.is_alive:
            return
        if (observer.energy or 0) < 1:
            return
        candidates = [s for s in targets if s.is_alive]
        if not candidates:
            return
        target = ctx.next_rng("starweaver_resonance", observer.unique_id).choice(
            candidates
        )
        observer.energy -= 1
        deal_damage(
            ctx,
            observer,
            target,
            40,
            DamageType.fixed,
            lambda a: msg.skill_damage(observer.name, "共振", target.name, a, kind=msg.KIND_FIXED),
            source=DamageSource.additional,
        )

    def _skill_pulse(
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
            deal_mag_ratio(
                ctx,
                actor,
                target,
                0.20,
                lambda a, t=target: msg.skill_damage(
                    actor.name, "汲取", t.name, a, kind=msg.KIND_MAGICAL
                ),
                source=DamageSource.skill,
            )
        gain = len(targets)
        grant_personal_energy(ctx, actor, gain)

    def _skill_purify(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id
        tid = action.get("targetId")
        if not tid:
            return
        target = ctx.find_spirit_anywhere(tid)
        if not target or not target.is_alive or target.owner_id != actor.owner_id:
            return
        removed = purge_debuffs(target)
        if removed:
            ctx.add_log(
                BattleLogType.effect_removed,
                msg.purged_debuffs(target.name, len(removed)),
                {"targetId": target.unique_id},
            )
        target.effects.append(
            make_effect(
                EffectType.buff_debuff_immunity,
                actor.unique_id,
                duration_turns=2,
                display_name="净化",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(target.name, "净化"),
            {"targetId": target.unique_id},
        )

    def _skill_burst(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        opponent_id = ctx.get_opponent_id(player_id)
        consumed = getattr(actor, "_consumed_energy", 0) or 0
        ratio = (40 + 5 * consumed) / 100.0
        for target in ctx.get_active_spirits(opponent_id):
            deal_mag_ratio(
                ctx,
                actor,
                target,
                ratio,
                lambda a, t=target: msg.skill_damage(
                    actor.name, "星爆", t.name, a, kind=msg.KIND_MAGICAL
                ),
                source=DamageSource.skill,
            )
        actor.effects.append(
            make_effect(EffectType.debuff_stun, actor.unique_id, duration_turns=2)
        )
        grant_personal_energy(ctx, actor, 4)
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(actor.name, "眩晕"),
            {"targetId": actor.unique_id},
        )


starweaver_logic = StarweaverLogic()
