"""藤椒小巴 — 热火朝天 / 浇油 / 炝锅 / 出锅！"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from ..battle import messages as msg
from ..battle.extra_action import ExtraActionSlot, ExtraActionUI, register_policy
from ..battle.types import (
    ActionType,
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
from .tengjiao_state import (
    COMMITTED_DISH_KEY,
    PENDING_FREE_KEY,
    DISH_LAZIJI,
    DISH_MAOXUEWANG,
    DISH_SHUIZHUYU,
    HUOLI_THRESHOLDS,
    committed_dish,
    consume_all_huoli,
    huoli_stacks,
    pending_free,
    set_committed_dish,
    set_huoli,
    set_pending_free,
)
from .tengjiao_dishes import (
    DISH_TAG_PREFIX,
    HUOLI_PER_BURN,
    LAZIJI_DURATION,
    LAZIJI_RATIO,
    MAOXUEWANG_DURATION,
    OIL_ATK_BONUS,
    OIL_DURATION,
    OIL_HUOLI,
    SHUIZHUYU_DURATION,
    SHUIZHUYU_RATIO,
    dish_cap,
    refresh_maoxuewang,
    refresh_or_apply,
)


# Back-compat aliases for older tests/UI code that imported module-private helpers.
_pending_free = pending_free
_set_pending_free = set_pending_free
_huoli_stacks = huoli_stacks
_set_huoli = set_huoli

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
            lambda a: msg.physical_hit(actor.name, target.name, a),
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
        if skill.id == "tengjiao_skill3" and pending_free(spirit):
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
        committed = committed_dish(actor)
        if committed:
            return committed
        free_slot = self._free_serve_slot(ctx, actor)
        if free_slot is not None:
            return free_slot.source.split(":", 1)[1]
        return None

    def prepare_serve_dish(self, ctx: BattleContext, actor: BattleSpirit) -> str:
        """Commit the dish for the upcoming 出锅 (roll if not yet known)."""
        existing = self.peek_serve_dish(ctx, actor)
        if existing:
            set_committed_dish(actor, existing)
            return existing
        dish = self._roll_dish(ctx, actor)
        set_committed_dish(actor, dish)
        return dish

    def preview_action(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
        action: Dict[str, Any],
    ) -> Optional[bool]:
        """Commit 出锅's dish without spending the turn.

        The UI submits this preview first, then renders the final target picker
        based on the committed dish stored in ``sync_attrs``.
        """
        del player_id
        if not action.get("previewDish"):
            return None
        if action.get("type") != ActionType.use_skill.value:
            return False
        if action.get("skillId") != "tengjiao_skill3":
            return False
        if actor.template_id != TEMPLATE_ID:
            return False
        if action.get("actorId") != actor.unique_id:
            return False
        self.prepare_serve_dish(ctx, actor)
        return True

    def describe_avatar_badge(self, spirit: BattleSpirit):
        return ("火力", f"{huoli_stacks(spirit)}")

    # --- 火力 ---

    def _add_huoli(self, ctx: BattleContext, spirit: BattleSpirit, amount: int) -> None:
        if amount <= 0 or not spirit.is_alive:
            return
        before = huoli_stacks(spirit)
        after = before + amount
        set_huoli(spirit, after)
        slots: List[ExtraActionSlot] = []
        pending = pending_free(spirit)
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
                    msg.passive(spirit.name, "热火朝天"),
                    {"targetId": spirit.unique_id, "threshold": thr, "dish": dish},
                )
        set_pending_free(spirit, pending)
        if slots:
            ctx.queue_extra_actions(slots)

    def _free_serve_slot(self, ctx: BattleContext, actor: BattleSpirit):
        """免费出锅槽：仅在「额外行动期」结算时有效。

        正常行动中途（付费出锅先扣能）也可能已经把免费槽推进队列；
        此时 ``current_extra_slot()`` 非空，但不能当成正在打免费出锅。
        引擎在切入额外行动时会设置 ``_suspended_turn_actor_id``，用它区分。
        """
        slot = ctx.current_extra_slot()
        if (
            slot is None
            or slot.policy_id != FREE_POLICY_ID
            or not slot.source.startswith("tengjiao_free:")
            or slot.actor_id != actor.unique_id
        ):
            return None
        if not getattr(ctx, "_suspended_turn_actor_id", None):
            return None
        return slot

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
            msg.effect_gained(actor.name, "浇油"),
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
                cap = dish_cap(effect)
                if cap is None or effect.duration_turns is None:
                    continue
                if effect.duration_turns >= cap:
                    continue
                effect.duration_turns = min(cap, effect.duration_turns + 1)
                extended += 1
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.passive(actor.name, "炝锅"),
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
        free_slot = self._free_serve_slot(ctx, actor)
        if free_slot is not None:
            pending = pending_free(actor)
            if pending:
                pending.pop(0)
                set_pending_free(actor, pending)

        if dish == DISH_LAZIJI:
            self._serve_laziji(ctx, player_id, actor, action)
        elif dish == DISH_SHUIZHUYU:
            self._serve_shuizhuyu(ctx, actor)
        else:
            self._serve_maoxuewang(ctx, player_id, actor)

    def _pick_dish(self, ctx: BattleContext, actor: BattleSpirit) -> str:
        committed = committed_dish(actor)
        if committed:
            set_committed_dish(actor, None)
            return committed
        free_slot = self._free_serve_slot(ctx, actor)
        if free_slot is not None:
            return free_slot.source.split(":", 1)[1]
        return self._roll_dish(ctx, actor)

    def _roll_dish(self, ctx: BattleContext, actor: BattleSpirit) -> str:
        weights = {
            DISH_LAZIJI: 1,
            DISH_SHUIZHUYU: 1,
            DISH_MAOXUEWANG: 1,
        }
        if not any(e.type == EffectType.buff_shuizhuyu for e in actor.effects):
            weights[DISH_SHUIZHUYU] *= 2
        if huoli_stacks(actor) >= 20:
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
        refresh_or_apply(
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
            msg.effect_gained_from(actor.name, target.name, "辣子鸡"),
            {"targetId": target.unique_id, "sourceId": actor.unique_id},
        )

    def _serve_shuizhuyu(self, ctx: BattleContext, actor: BattleSpirit) -> None:
        refresh_or_apply(
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
            msg.effect_gained(actor.name, "水煮鱼"),
            {"targetId": actor.unique_id},
        )

    def _serve_maoxuewang(
        self,
        ctx: BattleContext,
        player_id: str,
        actor: BattleSpirit,
    ) -> None:
        spent = consume_all_huoli(actor)
        burns = spent // HUOLI_PER_BURN
        enemies = ctx.get_active_spirits(ctx.get_opponent_id(player_id))
        for enemy in enemies:
            if burns > 0:
                apply_burn_stacks(enemy, actor.unique_id, burns)
            refresh_maoxuewang(enemy, actor.unique_id)
        ctx.add_log(
            BattleLogType.effect_applied,
            msg.effect_gained(actor.name, "毛血旺"),
            {
                "actorId": actor.unique_id,
                "huoliSpent": spent,
                "burnStacks": burns,
            },
        )


tengjiao_logic = TengjiaoLogic()
