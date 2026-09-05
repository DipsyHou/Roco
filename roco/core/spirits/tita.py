"""缇塔 — 分流 / 扩容（被动）/ 缓冲 / 过载"""

from __future__ import annotations

from typing import Any, ClassVar, Dict

from ..battle import messages as msg
from ..battle.effect_meta import stack_count
from ..battle.types import BattleLogType, BattleSpirit, EffectType, StatType
from ..battle.utils import get_state_stack_count, is_debuff_immune, make_effect
from ._combat import deal_atk_ratio, deal_mag_ratio, target_enemy
from ..spirit_logic import BattleContext, SpiritLogic

EXPANSION_CAP_BONUS = 2
BUFFER_ENERGY_THRESHOLD = 5
OVERLOAD_MAG_RATIO = 2.0
OVERLOAD_SPEED_PENALTY = 0.20
OVERLOAD_SLOW_TURNS = 2


class TitaLogic(SpiritLogic):
    template_id = "tita"
    SKILLS: ClassVar[Dict[str, str]] = {
        "tita_skill1": "_skill_shunt",
        "tita_skill2": "_skill_overload",
    }

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
            lambda a: msg.physical_hit(actor.name, target.name, a),
        )
        return True

    def get_team_energy_cap_bonus(self, ctx: BattleContext, spirit: BattleSpirit) -> int:
        del ctx
        if spirit.template_id != self.template_id or not spirit.is_alive:
            return 0
        return EXPANSION_CAP_BONUS

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        if spirit.template_id != self.template_id:
            return
        max_cap = ctx.sync_team_energy_cap(spirit.owner_id)
        ctx.add_log(
            BattleLogType.passive_triggered,
            msg.passive(spirit.name, "扩容"),
            {"targetId": spirit.unique_id, "maxTeamEnergy": max_cap},
        )

    def on_turn_start(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        self._decay_shunt_on_turn_start(ctx, actor)

    def _decay_shunt_on_turn_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        stacks = get_state_stack_count(spirit, EffectType.state_shunt)
        if stacks <= 0:
            return
        eff = next((e for e in spirit.effects if e.type == EffectType.state_shunt), None)
        if not eff:
            return
        eff.stacks = stack_count(eff) - 1
        if stack_count(eff) <= 0:
            spirit.effects = [e for e in spirit.effects if e.id != eff.id]
            ctx.add_log(
                BattleLogType.effect_removed,
                msg.effect_lost(spirit.name, "分流"),
                {"targetId": spirit.unique_id},
            )

    def on_ally_turn_end(
        self,
        ctx: BattleContext,
        player_id: str,
        observer: BattleSpirit,
        actor: BattleSpirit,
    ) -> None:
        del actor
        if observer.template_id != "tita" or not observer.is_alive:
            return
        if get_state_stack_count(observer, EffectType.state_shunt) > 0:
            ctx.gain_team_energy(
                player_id,
                1,
                reason=f"{observer.name} 的分流使队伍回复 1 点能量",
            )
        self._try_buffer_passive(ctx, player_id, observer)

    def on_spirit_defeated(
        self,
        ctx: BattleContext,
        spirit: BattleSpirit,
        defeated: BattleSpirit,
    ) -> None:
        del spirit
        if defeated.template_id == "tita":
            ctx.sync_team_energy_cap(defeated.owner_id)

    def _try_buffer_passive(
        self,
        ctx: BattleContext,
        player_id: str,
        tita: BattleSpirit,
    ) -> None:
        if ctx.get_team_energy_spent(player_id) < BUFFER_ENERGY_THRESHOLD:
            return
        ctx.gain_team_energy(
            player_id,
            1,
            reason=f"{tita.name} 的缓冲触发，队伍回复 1 点能量",
            log_type=BattleLogType.passive_triggered,
        )

    def _apply_speed_down(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        target: BattleSpirit,
        *,
        ratio: float = OVERLOAD_SPEED_PENALTY,
        turns: int = OVERLOAD_SLOW_TURNS,
    ) -> None:
        if not target.is_alive or is_debuff_immune(target):
            return
        target.effects.append(
            make_effect(
                EffectType.debuff_stat_percent_reduction,
                actor.unique_id,
                duration_turns=turns,
                stat_type=StatType.speed,
                value=ratio,
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(target.name, "过载"),
            {"targetId": target.unique_id},
        )

    def _set_state_stacks(
        self,
        spirit: BattleSpirit,
        eff_type: EffectType,
        stacks: int,
        display_name: str,
    ) -> None:
        existing = next((e for e in spirit.effects if e.type == eff_type), None)
        if existing:
            existing.stacks = stacks
        else:
            spirit.effects.append(
                make_effect(
                    eff_type,
                    spirit.unique_id,
                    stacks=stacks,
                    display_name=display_name,
                )
            )

    def _skill_shunt(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        self._set_state_stacks(actor, EffectType.state_shunt, 2, "分流")
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(actor.name, "分流", stacks=2),
            {"targetId": actor.unique_id, "stacks": 2},
        )

    def _skill_overload(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        deal_mag_ratio(
            ctx,
            actor,
            target,
            OVERLOAD_MAG_RATIO,
            lambda a: msg.skill_damage(
                actor.name, "过载", target.name, a, kind=msg.KIND_MAGICAL
            ),
        )
        self._apply_speed_down(ctx, actor, target)
        self._apply_speed_down(ctx, actor, actor)


tita_logic = TitaLogic()
