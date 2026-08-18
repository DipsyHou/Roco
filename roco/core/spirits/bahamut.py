"""巴哈姆特 — 罡气 / 彻甲(暴击刺客) / 寸劲(反击坦克) / 驱邪 / 镇煞 / 招架"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from ..battle.extra_action import ExtraActionSlot, ExtraActionUI, register_policy
from ..battle.events import DamageEvent
from ..battle.types import (
    ActionType,
    BattleLogType,
    BattleSpirit,
    DamageType,
    EffectType,
    StatType,
)
from ..battle.utils import (
    get_effective_stat,
    is_action_blocked,
    make_effect,
)
from ._combat import deal_damage, target_enemy
from ..spirit_logic import BattleContext, DamageSource, SpiritLogic

TEMPLATE_ID = "bahamut"

GANGQI_CAP = 10
QUXIE_CAP = 4
ZHENSHA_CAP = 2
ZHAOJIA_CAP = 5
ZHAOJIA_POLICY_ID = "bahamut_zhaojia"

CHEJIA_CRIT_RATE = {2: 0.25, 3: 0.50, 4: 0.50}
CHEJIA_CRIT_DMG = {2: 40.0, 3: 40.0, 4: 80.0}
ZHAOJIA_DR_PER_STACK = 0.05


# --------------- helpers ---------------

def _has_effect(spirit: BattleSpirit, eff_type: EffectType) -> bool:
    return any(e.type == eff_type for e in spirit.effects)


def _get_stacks(spirit: BattleSpirit, eff_type: EffectType) -> int:
    eff = next((e for e in spirit.effects if e.type == eff_type), None)
    return max(0, eff.stacks) if eff else 0


def _add_stacks(
    spirit: BattleSpirit,
    eff_type: EffectType,
    amount: int,
    cap: int,
    source_id: str = "",
) -> None:
    if amount <= 0:
        return
    eff = next((e for e in spirit.effects if e.type == eff_type), None)
    if eff:
        eff.stacks = min(cap, eff.stacks + amount)
    else:
        spirit.effects.append(
            make_effect(eff_type, source_id or spirit.unique_id, stacks=min(cap, amount))
        )


def _remove_stacks(spirit: BattleSpirit, eff_type: EffectType, amount: int) -> int:
    """Remove stacks and return actual amount removed; delete effect if zero."""
    eff = next((e for e in spirit.effects if e.type == eff_type), None)
    if not eff:
        return 0
    removed = min(eff.stacks, amount)
    eff.stacks -= removed
    if eff.stacks <= 0:
        spirit.effects = [e for e in spirit.effects if e.type != eff_type]
    return removed


def _remove_effect(spirit: BattleSpirit, eff_type: EffectType) -> None:
    spirit.effects = [e for e in spirit.effects if e.type != eff_type]


# --------------- policy ---------------

def _zhaojia_policy(actor: BattleSpirit, action: Dict[str, Any]) -> bool:
    if action.get("type") != ActionType.use_skill.value:
        return False
    return action.get("skillId") in ("bahamut_zhaojia_jiequan", "bahamut_zhaojia_fanpu")


register_policy(
    ZHAOJIA_POLICY_ID,
    _zhaojia_policy,
    ExtraActionUI(
        hint="（招架额外行动：截拳/反扑）",
        allow_normal_attack=False,
        allow_gather=False,
        special_skills=True,
    ),
)


# --------------- 巴哈姆特 ---------------

class BahamutLogic(SpiritLogic):
    template_id = TEMPLATE_ID
    SKILLS: ClassVar[Dict[str, str]] = {
        "bahamut_skill1": "_skill_jifengquan",
        "bahamut_skill2": "_skill_yingji",
        "bahamut_skill3": "_skill_longzhiwu",
        "bahamut_zhaojia_jiequan": "_skill_jiequan",
        "bahamut_zhaojia_fanpu": "_skill_fanpu",
    }

    # ===== lifecycle =========================================================

    def on_battle_start(self, ctx: BattleContext, spirit: BattleSpirit) -> None:
        if spirit.template_id != TEMPLATE_ID:
            return
        _add_stacks(spirit, EffectType.state_gangqi, GANGQI_CAP, GANGQI_CAP)
        if spirit.slot == 1:
            spirit.effects.append(make_effect(EffectType.state_chejia, spirit.unique_id))
            ctx.add_log(
                BattleLogType.passive_triggered,
                f"{spirit.name} 位于队伍首位，获得「彻甲」路线！",
                {"targetId": spirit.unique_id},
            )
        else:
            spirit.effects.append(make_effect(EffectType.state_cunjin, spirit.unique_id))
            ctx.add_log(
                BattleLogType.passive_triggered,
                f"{spirit.name} 位于队伍非首位，获得「寸劲」路线！",
                {"targetId": spirit.unique_id},
            )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{spirit.name} 开局获得 {GANGQI_CAP} 层罡气！",
            {"targetId": spirit.unique_id, "gangqi": GANGQI_CAP},
        )

    # ===== turn hooks ========================================================

    def on_turn_start(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        if actor.template_id != TEMPLATE_ID or not actor.is_alive:
            return
        if is_action_blocked(actor):
            return
        zhaojia = _get_stacks(actor, EffectType.state_zhaojia)
        if zhaojia <= 0:
            return
        ctx.add_log(
            BattleLogType.passive_triggered,
            f"{actor.name} 的招架触发额外行动（{zhaojia} 层）！",
            {"targetId": actor.unique_id, "zhaojiaStacks": zhaojia},
        )
        ctx.queue_extra_actions(
            [ExtraActionSlot(
                actor_id=actor.unique_id,
                policy_id=ZHAOJIA_POLICY_ID,
                source="bahamut_zhaojia",
            )],
            front=True,
        )

    # ===== route marking (once per action, NOT per hit) =======================

    def _try_apply_route_mark(
        self,
        ctx: BattleContext,
        attacker: BattleSpirit,
        target: BattleSpirit,
    ) -> None:
        """每使用一次普攻/技能，消耗 1 罡气给主目标叠 1 层 驱邪/镇煞。"""
        if not attacker.is_alive or not target.is_alive:
            return
        gangqi = _get_stacks(attacker, EffectType.state_gangqi)
        if gangqi <= 0:
            return

        if _has_effect(attacker, EffectType.state_chejia):
            quxie = _get_stacks(target, EffectType.state_quxie)
            if quxie >= QUXIE_CAP:
                return
            _remove_stacks(attacker, EffectType.state_gangqi, 1)
            _add_stacks(target, EffectType.state_quxie, 1, QUXIE_CAP, attacker.unique_id)

        elif _has_effect(attacker, EffectType.state_cunjin):
            zhensha = _get_stacks(target, EffectType.state_zhensha)
            if zhensha >= ZHENSHA_CAP:
                return
            _remove_stacks(attacker, EffectType.state_gangqi, 1)
            _add_stacks(target, EffectType.state_zhensha, 1, ZHENSHA_CAP, attacker.unique_id)

    # ===== damage hooks ======================================================

    def on_damage(
        self, ctx: BattleContext, spirit: BattleSpirit, event: DamageEvent
    ) -> None:
        if spirit.template_id != TEMPLATE_ID or not spirit.is_alive:
            return
        if event.target.unique_id != spirit.unique_id:
            return
        if event.damage <= 0:
            return

        cur = _get_stacks(spirit, EffectType.state_zhaojia)

        # 已有招架时，受到伤害自动 +1（招架自增强）
        if 0 < cur < ZHAOJIA_CAP:
            _add_stacks(spirit, EffectType.state_zhaojia, 1, ZHAOJIA_CAP)

        # 寸劲路线：镇煞满 2 层的敌人造成伤害时，获得 1 层招架（初始来源）
        if _has_effect(spirit, EffectType.state_cunjin):
            attacker = event.attacker
            if attacker and attacker.is_alive:
                if _get_stacks(attacker, EffectType.state_zhensha) >= ZHENSHA_CAP:
                    if _get_stacks(spirit, EffectType.state_zhaojia) < ZHAOJIA_CAP:
                        _add_stacks(spirit, EffectType.state_zhaojia, 1, ZHAOJIA_CAP)

    def get_damage_reduction(self, spirit: BattleSpirit) -> float:
        if spirit.template_id != TEMPLATE_ID:
            return 0.0
        return _get_stacks(spirit, EffectType.state_zhaojia) * ZHAOJIA_DR_PER_STACK

    # ===== crit hooks (彻甲) ==================================================

    def get_crit_rate_bonus(
        self, spirit: BattleSpirit, target: Optional[BattleSpirit] = None
    ) -> float:
        if spirit.template_id != TEMPLATE_ID:
            return 0.0
        if not _has_effect(spirit, EffectType.state_chejia):
            return 0.0
        if target is None:
            return 0.0
        quxie = _get_stacks(target, EffectType.state_quxie)
        return CHEJIA_CRIT_RATE.get(quxie, 0.0)

    def get_crit_damage_bonus(
        self, spirit: BattleSpirit, target: Optional[BattleSpirit] = None
    ) -> float:
        if spirit.template_id != TEMPLATE_ID:
            return 0.0
        if not _has_effect(spirit, EffectType.state_chejia):
            return 0.0
        if target is None:
            return 0.0
        quxie = _get_stacks(target, EffectType.state_quxie)
        return CHEJIA_CRIT_DMG.get(quxie, 0.0)

    def _log_crit(self, ctx: BattleContext, attacker: BattleSpirit, target: BattleSpirit) -> None:
        ctx.add_log(
            BattleLogType.damage_dealt,
            f"暴击！{attacker.name} 对 {target.name} 的伤害触发了暴击！",
            {"attackerId": attacker.unique_id, "targetId": target.unique_id},
        )

    # ===== normal attack ======================================================

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
        self._try_apply_route_mark(ctx, actor, target)
        self._deal_physical(
            ctx, actor, target, get_effective_stat(actor, StatType.atk) * 1.0,
            "普通攻击",
        )
        actor.last_attack_target_id = target.unique_id
        return True

    # ===== skills =============================================================

    # --- 疾风拳 ---
    def _skill_jifengquan(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        self._try_apply_route_mark(ctx, actor, target)
        atk = get_effective_stat(actor, StatType.atk)
        for i in range(3):
            if not target.is_alive:
                break
            deal_damage(
                ctx,
                actor,
                target,
                atk * 0.50,
                DamageType.physical,
                lambda a, n=i + 1: (
                    f"{actor.name} 的疾风拳第{n}段对 {target.name} 造成了 {a} 点物理伤害！"
                ),
                source=DamageSource.skill,
                crit_rng=ctx.next_rng("bahamut_crit", actor.unique_id),
                on_crit=lambda: self._log_crit(ctx, actor, target),
            )

    # --- 迎击 ---
    def _skill_yingji(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del ctx, player_id, action
        if _get_stacks(actor, EffectType.state_zhaojia) >= ZHAOJIA_CAP:
            return
        _add_stacks(actor, EffectType.state_zhaojia, 1, ZHAOJIA_CAP)

    # --- 龙之舞 ---
    def _skill_longzhiwu(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        actor.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                actor.unique_id,
                stat_type=StatType.atk,
                value=0.20,
                display_name="龙之舞",
            )
        )
        actor.effects.append(
            make_effect(
                EffectType.buff_stat_percent_boost,
                actor.unique_id,
                stat_type=StatType.speed,
                value=0.20,
                display_name="龙之舞",
            )
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 使用龙之舞，物攻+20%、速度+20%！",
            {"targetId": actor.unique_id},
        )

    # --- 截拳（招架额外行动专用）---
    def _skill_jiequan(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        stacks = _get_stacks(actor, EffectType.state_zhaojia)
        if stacks <= 0:
            return
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        self._try_apply_route_mark(ctx, actor, target)
        atk = get_effective_stat(actor, StatType.atk)
        for i in range(stacks):
            if not target.is_alive:
                break
            deal_damage(
                ctx,
                actor,
                target,
                atk * 0.30,
                DamageType.physical,
                lambda a, n=i + 1: (
                    f"{actor.name} 的截拳第{n}段对 {target.name} 造成了 {a} 点物理伤害！"
                ),
                source=DamageSource.skill,
                crit_rng=ctx.next_rng("bahamut_crit", actor.unique_id),
                on_crit=lambda: self._log_crit(ctx, actor, target),
            )
        _remove_effect(actor, EffectType.state_zhaojia)

    # --- 反扑（招架额外行动专用）---
    def _skill_fanpu(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        stacks = _get_stacks(actor, EffectType.state_zhaojia)
        if stacks <= 0:
            return
        target = target_enemy(ctx, player_id, action.get("targetId"))
        if not target:
            return
        self._try_apply_route_mark(ctx, actor, target)
        atk = get_effective_stat(actor, StatType.atk)
        opponent_id = ctx.get_opponent_id(player_id)

        deal_damage(
            ctx,
            actor,
            target,
            atk * 0.30,
            DamageType.physical,
            lambda a: f"{actor.name} 的反扑对 {target.name} 造成了 {a} 点物理伤害！",
            source=DamageSource.skill,
            crit_rng=ctx.next_rng("bahamut_crit", actor.unique_id),
            on_crit=lambda: self._log_crit(ctx, actor, target),
        )

        enemies = ctx.get_active_spirits(opponent_id)
        for i in range(stacks):
            alive_enemies = [e for e in enemies if e.is_alive]
            if not alive_enemies:
                break
            bounce_target = ctx.next_rng("bahamut_bounce", actor.unique_id).choice(
                alive_enemies
            )
            deal_damage(
                ctx,
                actor,
                bounce_target,
                atk * 0.30,
                DamageType.physical,
                lambda a, n=i + 1, t=bounce_target: (
                    f"{actor.name} 的反扑弹射第{n}段对 {t.name} 造成了 {a} 点物理伤害！"
                ),
                source=DamageSource.skill,
                crit_rng=ctx.next_rng("bahamut_crit", actor.unique_id),
                on_crit=lambda t=bounce_target: self._log_crit(ctx, actor, t),
            )

        _remove_effect(actor, EffectType.state_zhaojia)

    # ===== action validation ==================================================

    def can_execute_action(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        action: Dict[str, Any],
        *,
        in_extra_action: bool,
        stunned: bool,
    ) -> Optional[tuple]:
        del in_extra_action, stunned
        if actor.template_id != TEMPLATE_ID:
            return None
        at = action.get("type")
        if at != ActionType.use_skill.value:
            return None
        sk = action.get("skillId")
        if sk not in ("bahamut_zhaojia_jiequan", "bahamut_zhaojia_fanpu"):
            return None
        slot = ctx.current_extra_slot()
        if slot is None or slot.policy_id != ZHAOJIA_POLICY_ID:
            return (False, "截拳和反扑只能在招架额外行动中使用")
        return None

    # ===== helpers ============================================================

    def _deal_physical(
        self,
        ctx: BattleContext,
        actor: BattleSpirit,
        target: BattleSpirit,
        raw: float,
        verb: str,
    ) -> int:
        return deal_damage(
            ctx,
            actor,
            target,
            raw,
            DamageType.physical,
            lambda a: f"{actor.name} 的{verb}对 {target.name} 造成了 {a} 点物理伤害！",
            source=DamageSource.attack,
            crit_rng=ctx.next_rng("bahamut_crit", actor.unique_id),
            on_crit=lambda: self._log_crit(ctx, actor, target),
        )


bahamut_logic = BahamutLogic()
