"""南陆朱雀 - 天火持续伤害联动。"""

from __future__ import annotations

from typing import ClassVar, Dict

from ..battle import messages as msg
from ..battle.dot import trigger_all_sustained_damage, trigger_tianhuo_damage
from ..battle.effect_meta import stack_count
from ..battle.effects import (
    apply_fanji,
    apply_tianhuo_stacks,
    get_fanji_effect,
    get_tianhuo_effect,
)
from ..battle.events import DamageEvent, DamageSource, EffectAppliedEvent
from ..battle.types import BattleLogType, BattleSpirit, EffectType
from ..spirit_logic import BattleContext, SpiritLogic
from ._combat import target_enemy

ORDINARY_DOT_KINDS = frozenset({"burn", "poison", "parasite"})
FANJI_DURATION = 3
FANJI_TIANHUO_STACKS = 15
FENJIE_PRIMARY_STACKS = 30
FENJIE_ADJACENT_STACKS = 15
DEBUFF_TIANHUO_CHANCE = 0.75


def grant_tianhuo(
    ctx: BattleContext,
    source: BattleSpirit,
    target: BattleSpirit,
    stacks: int,
) -> bool:
    if not target.is_alive or stacks <= 0:
        return False
    if not apply_tianhuo_stacks(target, source.unique_id, stacks):
        return False
    effect = get_tianhuo_effect(target, source.unique_id)
    total = stack_count(effect) if effect else stacks
    ctx.add_log(
        BattleLogType.effect_applied,
        msg.gained_stacks(target.name, stacks, "天火", total=total),
        msg.data_effect(
            target.unique_id,
            source.unique_id,
            effectId=effect.id if effect else None,
            effectType=EffectType.debuff_tianhuo.value,
            stacks=stacks,
        ),
    )
    return True


class NanluZhuqueLogic(SpiritLogic):
    template_id = "nanluzhuque"
    SKILLS: ClassVar[Dict[str, str]] = {
        "nanluzhuque_skill1": "_skill_fanji",
        "nanluzhuque_skill2": "_skill_fenjie",
    }

    def on_damage(
        self,
        ctx: BattleContext,
        spirit: BattleSpirit,
        event: DamageEvent,
    ) -> None:
        if (
            spirit.template_id != self.template_id
            or not spirit.is_alive
            or event.source != DamageSource.dot
            or event.damage <= 0
            or not event.target.is_alive
            or event.target.owner_id == spirit.owner_id
        ):
            return

        if get_fanji_effect(event.target, spirit.unique_id):
            grant_tianhuo(ctx, spirit, event.target, 1)
        if event.dot_kind in ORDINARY_DOT_KINDS:
            trigger_tianhuo_damage(ctx, event.target)

    def on_effect_applied(
        self,
        ctx: BattleContext,
        spirit: BattleSpirit,
        event: EffectAppliedEvent,
    ) -> None:
        target = event.target
        if (
            spirit.template_id != self.template_id
            or not spirit.is_alive
            or not target.is_alive
            or target.owner_id == spirit.owner_id
            or EffectType.debuff_fanji not in event.prior_effect_types
        ):
            return
        rng = ctx.next_rng(
            "nanluzhuque_qunhuofuchen",
            spirit.unique_id,
            target.unique_id,
            event.effect_id or event.effect_type.value,
        )
        if rng.random() < DEBUFF_TIANHUO_CHANCE:
            grant_tianhuo(ctx, spirit, target, 1)

    def _skill_fanji(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: dict,
    ) -> None:
        del action
        for target in list(ctx.get_active_spirits(ctx.get_opponent_id(player_id))):
            prior_effect_types = [effect.type.value for effect in target.effects]
            if apply_fanji(target, actor.unique_id, duration_turns=FANJI_DURATION):
                effect = get_fanji_effect(target, actor.unique_id)
                ctx.add_log(
                    BattleLogType.effect_applied,
                    msg.effect_gained(target.name, "燔祭"),
                    msg.data_effect(
                        target.unique_id,
                        actor.unique_id,
                        effectId=effect.id if effect else None,
                        effectType=EffectType.debuff_fanji.value,
                        priorEffectTypes=prior_effect_types,
                    ),
                )
            grant_tianhuo(ctx, actor, target, FANJI_TIANHUO_STACKS)

    def _skill_fenjie(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: dict,
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        targets = [target] + ctx.get_adjacent_enemies(target)
        for current in targets:
            stacks = (
                FENJIE_PRIMARY_STACKS
                if current.unique_id == target.unique_id
                else FENJIE_ADJACENT_STACKS
            )
            grant_tianhuo(ctx, actor, current, stacks)
        for current in targets:
            if current.is_alive:
                trigger_all_sustained_damage(ctx, current)


nanluzhuque_logic = NanluZhuqueLogic()
