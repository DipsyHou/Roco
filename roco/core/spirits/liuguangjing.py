"""流光镜 — 映像伤害 / 映像能量 / 阴阳 / 镜倾 / 流转"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

from ..battle import messages as msg
from ..battle.effect_meta import stack_count
from ..battle.types import BattleLogType, BattleSpirit, DamageType, EffectType
from ..battle.utils import make_effect
from ._combat import deal_damage, target_enemy
from ..spirit_logic import BattleContext, SpiritLogic

TEMPLATE_ID = "liuguangjing"
YINYANG_PENDING_KEY = "yinyangPending"
YINYANG_ENERGY_GAIN = 2
GATHER_ADVANCE = 0.24
MIRROR_POUR_RATIO = 0.06
FLOW_ENERGY_COST = 6
FLOW_ENERGY_BONUS = 1


def get_mirror_damage(spirit: BattleSpirit) -> int:
    for eff in spirit.effects:
        if eff.type == EffectType.state_mirror_damage:
            return stack_count(eff)
    return 0


def get_mirror_energy(spirit: BattleSpirit) -> int:
    for eff in spirit.effects:
        if eff.type == EffectType.state_mirror_energy:
            return stack_count(eff)
    return 0


def _add_stack_effect(
    spirit: BattleSpirit,
    effect_type: EffectType,
    amount: int,
    display_name: str,
) -> int:
    if amount <= 0 or spirit.template_id != TEMPLATE_ID:
        return 0
    existing = next((e for e in spirit.effects if e.type == effect_type), None)
    if existing is None:
        spirit.effects.append(
            make_effect(
                effect_type,
                spirit.unique_id,
                stacks=amount,
                display_name=display_name,
            )
        )
        return amount
    existing.stacks = stack_count(existing) + amount
    return amount


def add_mirror_damage(spirit: BattleSpirit, amount: int) -> int:
    return _add_stack_effect(
        spirit, EffectType.state_mirror_damage, amount, "映像伤害"
    )


def add_mirror_energy(spirit: BattleSpirit, amount: int) -> int:
    return _add_stack_effect(
        spirit, EffectType.state_mirror_energy, amount, "映像能量"
    )


def spend_mirror_energy(spirit: BattleSpirit, amount: int) -> int:
    existing = next(
        (e for e in spirit.effects if e.type == EffectType.state_mirror_energy),
        None,
    )
    if existing is None or amount <= 0:
        return 0
    have = stack_count(existing)
    spent = min(have, amount)
    remaining = have - spent
    if remaining <= 0:
        spirit.effects = [
            e for e in spirit.effects if e.type != EffectType.state_mirror_energy
        ]
    else:
        existing.stacks = remaining
    return spent


def clear_half_mirror_damage(spirit: BattleSpirit) -> None:
    existing = next(
        (e for e in spirit.effects if e.type == EffectType.state_mirror_damage),
        None,
    )
    if existing is None:
        return
    remaining = stack_count(existing) // 2
    if remaining <= 0:
        spirit.effects = [
            e for e in spirit.effects if e.type != EffectType.state_mirror_damage
        ]
    else:
        existing.stacks = remaining


def _pending_yinyang(spirit: BattleSpirit) -> bool:
    return bool((spirit.sync_attrs or {}).get(YINYANG_PENDING_KEY))


def _set_pending_yinyang(spirit: BattleSpirit, pending: bool) -> None:
    attrs = dict(spirit.sync_attrs or {})
    if pending:
        attrs[YINYANG_PENDING_KEY] = True
    else:
        attrs.pop(YINYANG_PENDING_KEY, None)
    spirit.sync_attrs = attrs


class LiuguangjingLogic(SpiritLogic):
    template_id = TEMPLATE_ID
    SKILLS: ClassVar[Dict[str, str]] = {
        "liuguangjing_skill1": "_skill_yinyang",
        "liuguangjing_skill2": "_skill_mirror_pour",
    }

    def on_ally_damage_recorded(
        self,
        ctx: BattleContext,
        observer: BattleSpirit,
        attacker: BattleSpirit,
        defender: BattleSpirit,
        amount: int,
    ) -> None:
        del ctx, attacker, defender
        if observer.template_id != TEMPLATE_ID or not observer.is_alive or amount <= 0:
            return
        add_mirror_damage(observer, amount)

    def on_team_energy_spent(
        self,
        ctx: BattleContext,
        player_id: str,
        observer: BattleSpirit,
        amount: int,
        spender: BattleSpirit,
    ) -> None:
        del player_id, spender
        if observer.template_id != TEMPLATE_ID or not observer.is_alive or amount <= 0:
            return
        add_mirror_energy(observer, amount)
        self._try_flow_convert(ctx, observer)

    def on_team_energy_gained(
        self,
        ctx: BattleContext,
        player_id: str,
        observer: BattleSpirit,
        amount: int,
        source: Optional[BattleSpirit],
    ) -> None:
        del ctx, player_id, source
        if observer.template_id != TEMPLATE_ID or not observer.is_alive or amount <= 0:
            return
        add_mirror_energy(observer, amount)

    def on_gather_energy(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        if actor.template_id != TEMPLATE_ID or not actor.is_alive:
            return
        ctx.advance_action(actor, GATHER_ADVANCE)

    def on_turn_start(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        if actor.template_id != TEMPLATE_ID or not _pending_yinyang(actor):
            return
        _set_pending_yinyang(actor, False)
        self._try_yinyang_gain(ctx, actor)

    def _energy_at_most_half(self, ctx: BattleContext, player_id: str) -> bool:
        pd = ctx.state.players.get(player_id)
        if pd is None or pd.max_team_energy <= 0:
            return False
        # 不大于 50%：energy * 2 <= max，避免浮点
        return pd.team_energy * 2 <= pd.max_team_energy

    def _try_yinyang_gain(self, ctx: BattleContext, actor: BattleSpirit) -> int:
        if not self._energy_at_most_half(ctx, actor.owner_id):
            return 0
        gained = ctx.gain_team_energy(
            actor.owner_id, YINYANG_ENERGY_GAIN, source=actor
        )
        if gained > 0:
            ctx.add_log(
                BattleLogType.passive_triggered,
                msg.passive(actor.name, "阴阳"),
                {"actorId": actor.unique_id, "energy": gained},
            )
        return gained

    def _try_flow_convert(self, ctx: BattleContext, actor: BattleSpirit) -> int:
        """我方耗能后：能量未满且映像能量 ≥6 时耗 6 额外 +1。"""
        pd = ctx.state.players.get(actor.owner_id)
        if pd is None or pd.team_energy >= pd.max_team_energy:
            return 0
        if get_mirror_energy(actor) < FLOW_ENERGY_COST:
            return 0
        spend_mirror_energy(actor, FLOW_ENERGY_COST)
        bonus = ctx.gain_team_energy(
            actor.owner_id,
            FLOW_ENERGY_BONUS,
            source=actor,
            notify=True,
        )
        if bonus <= 0:
            add_mirror_energy(actor, FLOW_ENERGY_COST)
            return 0
        ctx.add_log(
            BattleLogType.passive_triggered,
            msg.passive(actor.name, "流转"),
            {"actorId": actor.unique_id, "energy": bonus},
        )
        return bonus

    def _skill_yinyang(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        self._try_yinyang_gain(ctx, actor)
        _set_pending_yinyang(actor, True)

    def _skill_mirror_pour(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        mirror = get_mirror_damage(actor)
        amount = int(mirror * MIRROR_POUR_RATIO + 1e-9)
        if amount > 0:
            deal_damage(
                ctx,
                actor,
                target,
                float(amount),
                DamageType.fixed,
                lambda a: msg.skill_damage(
                    actor.name, "镜倾", target.name, a, kind=msg.KIND_FIXED
                ),
            )
            for adj in ctx.get_adjacent_enemies(target):
                deal_damage(
                    ctx,
                    actor,
                    adj,
                    float(amount),
                    DamageType.fixed,
                    lambda a, t=adj: msg.skill_damage(
                        actor.name, "镜倾", t.name, a, kind=msg.KIND_FIXED
                    ),
                )
        clear_half_mirror_damage(actor)


liuguangjing_logic = LiuguangjingLogic()
