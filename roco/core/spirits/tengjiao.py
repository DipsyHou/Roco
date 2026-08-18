"""藤椒小巴 — 热火朝天 / 浇油 / 炝锅 / 出锅！"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional, Tuple

from ..battle.extra_action import ExtraActionSlot, ExtraActionUI, register_policy
from ..battle.types import (
    ActionType,
    BattleEffect,
    BattleLogType,
    BattleSpirit,
    EffectType,
    StatType,
    TargetType,
)
from ..battle.utils import apply_burn_stacks, make_effect
from ._combat import deal_atk_ratio, target_ally, target_enemy
from ..spirit_logic import BattleContext, SpiritLogic

TEMPLATE_ID = "tengjiao"
FREE_POLICY_ID = "tengjiao_free_serve"
PENDING_FREE_KEY = "pending_free"
COMMITTED_DISH_KEY = "committed_dish"

DISH_LAZIJI = "laziji"
DISH_SHUIZHUYU = "shuizhuyu"
DISH_MAOXUEWANG = "maoxuewang"

HUOLI_THRESHOLDS: Tuple[Tuple[int, str], ...] = (
    (10, DISH_LAZIJI),
    (20, DISH_SHUIZHUYU),
    (30, DISH_MAOXUEWANG),
)

LAZIJI_RATIO = 0.10
LAZIJI_DURATION = 3
SHUIZHUYU_RATIO = 0.10
SHUIZHUYU_DURATION = 2
MAOXUEWANG_AMP = 0.15
MAOXUEWANG_DURATION = 3
OIL_ATK_BONUS = 0.20
OIL_DURATION = 3
OIL_HUOLI = 5
HUOLI_PER_BURN = 3
DISH_TAG_PREFIX = "dish:"
SUSTAINED_TAG = "sustained_damage"


def _pending_free(spirit: BattleSpirit) -> List[str]:
    raw = spirit.sync_attrs.get(PENDING_FREE_KEY)
    return list(raw) if raw else []


def _set_pending_free(spirit: BattleSpirit, pending: List[str]) -> None:
    if pending:
        spirit.sync_attrs[PENDING_FREE_KEY] = list(pending)
    else:
        spirit.sync_attrs.pop(PENDING_FREE_KEY, None)


def _committed_dish(spirit: BattleSpirit) -> Optional[str]:
    raw = spirit.sync_attrs.get(COMMITTED_DISH_KEY)
    return str(raw) if raw else None


def _set_committed_dish(spirit: BattleSpirit, dish: Optional[str]) -> None:
    if dish:
        spirit.sync_attrs[COMMITTED_DISH_KEY] = dish
    else:
        spirit.sync_attrs.pop(COMMITTED_DISH_KEY, None)


def _huoli_stacks(spirit: BattleSpirit) -> int:
    eff = next((e for e in spirit.effects if e.type == EffectType.state_huoli), None)
    return max(0, eff.stacks) if eff else 0


def _set_huoli(spirit: BattleSpirit, stacks: int) -> None:
    stacks = max(0, stacks)
    eff = next((e for e in spirit.effects if e.type == EffectType.state_huoli), None)
    if stacks <= 0:
        if eff:
            spirit.effects = [e for e in spirit.effects if e.type != EffectType.state_huoli]
        return
    if eff:
        eff.stacks = stacks
    else:
        spirit.effects.append(
            make_effect(EffectType.state_huoli, spirit.unique_id, stacks=stacks)
        )


def _refresh_or_apply(
    target: BattleSpirit,
    *,
    eff_type: EffectType,
    source_id: str,
    duration: int,
    value: Optional[float] = None,
    display_name: Optional[str] = None,
    effect_tag: Optional[str] = None,
) -> None:
    existing = next((e for e in target.effects if e.type == eff_type), None)
    if existing and existing.source_id == source_id:
        existing.duration_turns = duration
        if value is not None:
            existing.value = value
        if effect_tag is not None:
            existing.effect_tag = effect_tag
        if display_name is not None:
            existing.display_name = display_name
        return
    if existing:
        target.effects = [e for e in target.effects if e is not existing]
    target.effects.append(
        make_effect(
            eff_type,
            source_id,
            duration_turns=duration,
            value=value,
            display_name=display_name,
            effect_tag=effect_tag,
        )
    )


def _refresh_maoxuewang(target: BattleSpirit, source_id: str) -> None:
    existing = next(
        (
            e
            for e in target.effects
            if e.type == EffectType.debuff_taken_damage_percent_boost
            and e.display_name == "毛血旺"
        ),
        None,
    )
    if existing:
        existing.duration_turns = MAOXUEWANG_DURATION
        existing.value = MAOXUEWANG_AMP
        existing.source_id = source_id
        existing.effect_tag = SUSTAINED_TAG
        return
    target.effects.append(
        make_effect(
            EffectType.debuff_taken_damage_percent_boost,
            source_id,
            duration_turns=MAOXUEWANG_DURATION,
            value=MAOXUEWANG_AMP,
            display_name="毛血旺",
            effect_tag=SUSTAINED_TAG,
        )
    )


def _dish_cap(effect: BattleEffect) -> Optional[int]:
    if (
        effect.type == EffectType.debuff_taken_damage_percent_boost
        and effect.display_name == "毛血旺"
    ):
        return MAOXUEWANG_DURATION
    tag = effect.effect_tag or ""
    if not tag.startswith(DISH_TAG_PREFIX):
        return None
    try:
        return int(tag[len(DISH_TAG_PREFIX) :])
    except ValueError:
        return None


def _free_serve_policy(actor: BattleSpirit, action: Dict[str, Any]) -> bool:
    if action.get("type") != ActionType.use_skill.value:
        return False
    return action.get("skillId") == "tengjiao_skill3"


register_policy(
    FREE_POLICY_ID,
    _free_serve_policy,
    ExtraActionUI(
        hint="（热火朝天：出锅！辣子鸡请选己方，其余菜无需选目标）",
        allow_normal_attack=False,
        allow_gather=False,
        allowed_skill_ids=("tengjiao_skill3",),
    ),
)


class TengjiaoLogic(SpiritLogic):
    template_id = TEMPLATE_ID
    SKILLS: ClassVar[Dict[str, str]] = {
        "tengjiao_skill1": "_skill_oil",
        "tengjiao_skill2": "_skill_wok",
        "tengjiao_skill3": "_skill_serve",
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
            lambda a: f"{actor.name} 对 {target.name} 造成了 {a} 点物理伤害！",
        )
        actor.last_attack_target_id = target.unique_id
        return True

    def on_team_energy_spent(
        self,
        ctx: BattleContext,
        player_id: str,
        observer: BattleSpirit,
        amount: int,
        spender: BattleSpirit,
    ) -> None:
        del spender
        if observer.template_id != TEMPLATE_ID or not observer.is_alive:
            return
        if amount <= 0:
            return
        self._add_huoli(ctx, observer, amount)

    def get_skill_energy_cost(self, spirit: BattleSpirit, skill, base_cost: int) -> int:
        if skill.id == "tengjiao_skill3" and _pending_free(spirit):
            return 0
        return base_cost

    def get_skill_target_type(
        self,
        ctx: BattleContext,
        spirit: BattleSpirit,
        skill,
    ) -> Optional[TargetType]:
        if skill.id != "tengjiao_skill3":
            return None
        dish = self.peek_serve_dish(ctx, spirit)
        if dish == DISH_LAZIJI:
            return TargetType.single_ally
        if dish == DISH_SHUIZHUYU:
            return TargetType.self
        if dish == DISH_MAOXUEWANG:
            return TargetType.all_enemies
        return TargetType.none

    def peek_serve_dish(self, ctx: BattleContext, actor: BattleSpirit) -> Optional[str]:
        """Forced free dish, or a dish already committed for UI; else ``None``."""
        committed = _committed_dish(actor)
        if committed:
            return committed
        slot = ctx.current_extra_slot()
        if slot and slot.source.startswith("tengjiao_free:"):
            return slot.source.split(":", 1)[1]
        return None

    def prepare_serve_dish(self, ctx: BattleContext, actor: BattleSpirit) -> str:
        """Commit the dish for the upcoming 出锅 (roll if not yet known)."""
        existing = self.peek_serve_dish(ctx, actor)
        if existing:
            _set_committed_dish(actor, existing)
            return existing
        dish = self._roll_dish(ctx, actor)
        _set_committed_dish(actor, dish)
        return dish

    def describe_avatar_badge(self, spirit: BattleSpirit):
        return ("火力", f"{_huoli_stacks(spirit)}")

    # --- 火力 ---

    def _add_huoli(self, ctx: BattleContext, spirit: BattleSpirit, amount: int) -> None:
        if amount <= 0 or not spirit.is_alive:
            return
        before = _huoli_stacks(spirit)
        after = before + amount
        _set_huoli(spirit, after)
        slots: List[ExtraActionSlot] = []
        pending = _pending_free(spirit)
        for thr, dish in HUOLI_THRESHOLDS:
            if before < thr <= after:
                pending.append(dish)
                slots.append(
                    ExtraActionSlot(
                        actor_id=spirit.unique_id,
                        policy_id=FREE_POLICY_ID,
                        source=f"tengjiao_free:{dish}",
                    )
                )
                ctx.add_log(
                    BattleLogType.passive_triggered,
                    f"{spirit.name} 的热火朝天触发额外出锅（{thr}层）！",
                    {"targetId": spirit.unique_id, "threshold": thr, "dish": dish},
                )
        _set_pending_free(spirit, pending)
        if slots:
            ctx.queue_extra_actions(slots)

    def _consume_all_huoli(self, spirit: BattleSpirit) -> int:
        amount = _huoli_stacks(spirit)
        _set_huoli(spirit, 0)
        return amount

    # --- skills ---

    def _skill_oil(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del player_id, action
        self._add_huoli(ctx, actor, OIL_HUOLI)
        existing = next(
            (
                e
                for e in actor.effects
                if e.type == EffectType.buff_stat_percent_boost
                and e.display_name == "浇油"
                and e.stat_type == StatType.atk
            ),
            None,
        )
        if existing:
            existing.duration_turns = OIL_DURATION
            existing.value = OIL_ATK_BONUS
        else:
            actor.effects.append(
                make_effect(
                    EffectType.buff_stat_percent_boost,
                    actor.unique_id,
                    stat_type=StatType.atk,
                    value=OIL_ATK_BONUS,
                    duration_turns=OIL_DURATION,
                    display_name="浇油",
                )
            )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 浇油！物攻提升20%（3回合）！",
            {"targetId": actor.unique_id},
        )

    def _skill_wok(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        del action
        extended = 0
        opp = ctx.get_opponent_id(player_id)
        field = list(ctx.get_all_spirits(player_id)) + list(ctx.get_active_spirits(opp))
        for spirit in field:
            for effect in spirit.effects:
                cap = _dish_cap(effect)
                if cap is None or effect.duration_turns is None:
                    continue
                if effect.duration_turns >= cap:
                    continue
                effect.duration_turns = min(cap, effect.duration_turns + 1)
                extended += 1
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 炝锅！延长了 {extended} 个菜品效果！",
            {"actorId": actor.unique_id, "extended": extended},
        )

    def _skill_serve(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        dish = self._pick_dish(ctx, actor)
        pending = _pending_free(actor)
        slot = ctx.current_extra_slot()
        if (
            pending
            and slot
            and slot.policy_id == FREE_POLICY_ID
            and slot.source.startswith("tengjiao_free:")
        ):
            pending.pop(0)
            _set_pending_free(actor, pending)

        if dish == DISH_LAZIJI:
            self._serve_laziji(ctx, player_id, actor, action)
        elif dish == DISH_SHUIZHUYU:
            self._serve_shuizhuyu(ctx, actor)
        else:
            self._serve_maoxuewang(ctx, player_id, actor)

    def _pick_dish(self, ctx: BattleContext, actor: BattleSpirit) -> str:
        committed = _committed_dish(actor)
        if committed:
            _set_committed_dish(actor, None)
            return committed
        slot = ctx.current_extra_slot()
        if slot and slot.source.startswith("tengjiao_free:"):
            return slot.source.split(":", 1)[1]
        return self._roll_dish(ctx, actor)

    def _roll_dish(self, ctx: BattleContext, actor: BattleSpirit) -> str:
        weights = {
            DISH_LAZIJI: 1,
            DISH_SHUIZHUYU: 1,
            DISH_MAOXUEWANG: 1,
        }
        if not any(e.type == EffectType.buff_shuizhuyu for e in actor.effects):
            weights[DISH_SHUIZHUYU] *= 2
        if _huoli_stacks(actor) >= 20:
            weights[DISH_MAOXUEWANG] *= 2
        dishes = list(weights.keys())
        w = [weights[d] for d in dishes]
        return ctx.next_rng("tengjiao_dish", actor.unique_id).choices(dishes, weights=w, k=1)[0]

    def _serve_laziji(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> None:
        target = target_ally(ctx, player_id, action.get("targetId"))
        if not target:
            return
        _refresh_or_apply(
            target,
            eff_type=EffectType.buff_laziji,
            source_id=actor.unique_id,
            duration=LAZIJI_DURATION,
            value=LAZIJI_RATIO,
            display_name="辣子鸡",
            effect_tag=f"{DISH_TAG_PREFIX}{LAZIJI_DURATION}",
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 端出辣子鸡，{target.name} 双攻提升！",
            {"targetId": target.unique_id, "sourceId": actor.unique_id},
        )

    def _serve_shuizhuyu(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        _refresh_or_apply(
            actor,
            eff_type=EffectType.buff_shuizhuyu,
            source_id=actor.unique_id,
            duration=SHUIZHUYU_DURATION,
            value=SHUIZHUYU_RATIO,
            display_name="水煮鱼",
            effect_tag=f"{DISH_TAG_PREFIX}{SHUIZHUYU_DURATION}",
        )
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 端出水煮鱼，全体己方双攻提升！",
            {"targetId": actor.unique_id},
        )

    def _serve_maoxuewang(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
    ) -> None:
        spent = self._consume_all_huoli(actor)
        burns = spent // HUOLI_PER_BURN
        enemies = ctx.get_active_spirits(ctx.get_opponent_id(player_id))
        for enemy in enemies:
            if burns > 0:
                apply_burn_stacks(enemy, actor.unique_id, burns)
            _refresh_maoxuewang(enemy, actor.unique_id)
        ctx.add_log(
            BattleLogType.effect_applied,
            f"{actor.name} 端出毛血旺，消耗{spent}层火力"
            + (f"，全体敌方获得{burns}层灼烧" if burns > 0 else "")
            + "，受到的持续伤害提高15%！",
            {
                "actorId": actor.unique_id,
                "huoliSpent": spent,
                "burnStacks": burns,
            },
        )


tengjiao_logic = TengjiaoLogic()
