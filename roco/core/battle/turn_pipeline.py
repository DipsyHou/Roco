"""Single entry for turn begin / act / end.

Hook timings are documented on ``SpiritLogic`` in ``roco/core/spirits/base.py``;
the turn / extra-action distinction is specified in ``docs/mechanics.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from .actions import ActionDict
from . import messages as msg
from .types import BattleLogType, BattleSpirit
from .dot import process_system_effects_on_action_end
from .effects import is_action_blocked, tick_effects
from ..spirits import get_spirit_logic

if TYPE_CHECKING:
    from .engine import BattleEngine


class TurnPipeline:
    def __init__(self, engine: "BattleEngine") -> None:
        self._eng = engine

    def begin_turn(self, actor: BattleSpirit) -> bool:
        """Turn start for ``actor``. Returns True if stunned (skip act)."""
        ctx = self._eng
        if not actor.is_alive:
            return False

        stunned = is_action_blocked(actor)
        logic = get_spirit_logic(actor.template_id)
        if logic:
            logic.on_turn_start(ctx, actor)

        player_id = actor.owner_id
        pd = ctx.state.players.get(player_id)
        if pd:
            for spirit in pd.spirits:
                if not spirit.is_alive:
                    continue
                ally_logic = get_spirit_logic(spirit.template_id)
                if ally_logic:
                    ally_logic.on_ally_turn_start(ctx, player_id, spirit, actor)

        return stunned

    def resolve_turn(
        self,
        actor: BattleSpirit,
        action: ActionDict,
        *,
        stunned: bool,
        defer_end_turn: bool = False,
    ) -> None:
        ctx = self._eng
        player_id = actor.owner_id

        if stunned:
            ctx.add_log(
                BattleLogType.stunned,
                msg.stunned_normal(actor.name),
                {"actorId": actor.unique_id},
            )
        else:
            ctx.execute_action(player_id, action)

        logic = get_spirit_logic(actor.template_id)
        if logic and actor.is_alive:
            logic.on_action_end(
                ctx,
                player_id,
                actor,
                action,
                stunned=stunned,
            )

        if not defer_end_turn:
            self.end_turn(actor, action, player_id=player_id, stunned=stunned)

    def resolve_inserted_extra_action(
        self,
        actor: BattleSpirit,
        action: ActionDict,
    ) -> None:
        """额外行动：仅执行一次出手，不触发回合开始/结束结算，也不改动时间轴。

        执行期间 ``execute_skill`` 等可继续往 ``state.extra_action_queue`` 追加
        / 插队，从而触发牌技连锁、共舞链等。
        """
        ctx = self._eng
        if is_action_blocked(actor):
            ctx.add_log(
                BattleLogType.stunned,
                msg.stunned_extra(actor.name),
                {"actorId": actor.unique_id},
            )
            return
        ctx.execute_action(actor.owner_id, action)

    def end_turn(
        self,
        actor: BattleSpirit,
        action: ActionDict,
        *,
        player_id: str,
        stunned: bool,
    ) -> None:
        ctx = self._eng
        opponent_id = ctx.get_opponent_id(player_id)

        logic = get_spirit_logic(actor.template_id)
        if logic and actor.is_alive:
            logic.on_turn_end(ctx, player_id, actor, action, stunned=stunned)

        pd = ctx.state.players.get(player_id)
        if pd:
            for spirit in pd.spirits:
                if not spirit.is_alive:
                    continue
                ally_logic = get_spirit_logic(spirit.template_id)
                if ally_logic:
                    ally_logic.on_ally_turn_end(ctx, player_id, spirit, actor)

        for eff in tick_effects(actor):
            ctx.log_effect_expired(actor, eff)
        process_system_effects_on_action_end(ctx, actor)
        ctx.after_actor_acts(actor)
        self._passive_check(player_id)
        self._passive_check(opponent_id)

    def _passive_check(self, player_id: str) -> None:
        pd = self._eng.state.players.get(player_id)
        if not pd:
            return
        seen: set[str] = set()
        for s in pd.spirits:
            if s.template_id in seen or not s.is_alive:
                continue
            seen.add(s.template_id)
            logic = get_spirit_logic(s.template_id)
            if logic:
                logic.on_passive_check(self._eng, player_id)
