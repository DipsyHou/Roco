"""Multi-step skill interactions that need extra dialogs before submitting.

Most skills submit directly, optionally after one target pick. A few need a
richer flow — 诡法师 must choose a hand card, then possibly a target, then
possibly a set of cards to consume. Keeping those flows here (registered by
skill id) means ``app.py`` never names a specific spirit: it just asks whether
a skill has a custom flow and delegates.

To add a flow for a new spirit, write a function taking ``(panel, actor)`` and
register it with :func:`register_skill_flow`.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol

from tkinter import messagebox

from roco.core.battle.types import ActionType, BattleSpirit
from roco.core.spirits.guifashi_cards import (
    ALLY_TARGET_CARDS,
    ENEMY_TARGET_CARDS,
    FATE_CARDS,
    CardState,
    card_label,
)

from .windows import IndexChoiceWindow, MultiPickWindow


class SkillFlowPanel(Protocol):
    """The slice of the action panel a flow may drive."""

    eng: Any

    def _submit_action(self, action: Dict[str, Any]) -> None: ...

    def _pick_target(
        self,
        mode: str,
        callback: Callable[[BattleSpirit], None],
        *,
        cancellable: bool = True,
    ) -> None: ...


SkillFlow = Callable[[SkillFlowPanel, BattleSpirit], None]

_FLOWS: Dict[str, SkillFlow] = {}


def register_skill_flow(skill_id: str, flow: SkillFlow) -> None:
    _FLOWS[skill_id] = flow


def get_skill_flow(skill_id: str) -> Optional[SkillFlow]:
    """Custom interaction for ``skill_id``, or ``None`` for the default path."""
    return _FLOWS.get(skill_id)


def resume_pending_tengjiao_serve(panel: SkillFlowPanel) -> None:
    """Continue 出锅 UI after previewDish is reflected in engine state."""
    actor_id = getattr(panel, "_pending_tengjiao_serve", None)
    if not actor_id:
        return
    eng = getattr(panel, "eng", None)
    if eng is None:
        return
    from roco.core.spirits.tengjiao import tengjiao_logic

    actor = eng.find_spirit_anywhere(actor_id)
    if not actor:
        return
    dish = tengjiao_logic.peek_serve_dish(eng, actor)
    if not dish:
        return
    panel._pending_tengjiao_serve = None  # type: ignore[attr-defined]
    _tengjiao_after_dish(panel, actor, dish)


def _base_action(actor: BattleSpirit, skill_id: str) -> Dict[str, Any]:
    return {
        "type": ActionType.use_skill.value,
        "playerId": actor.owner_id,
        "actorId": actor.unique_id,
        "skillId": skill_id,
    }


def _hand_labels(hand: List[str]) -> List[str]:
    return [f"[{i}] {card_label(cid)}" for i, cid in enumerate(hand)]


# --- 诡法师 -----------------------------------------------------------------


def _draw(panel: SkillFlowPanel, actor: BattleSpirit) -> None:
    panel._submit_action(_base_action(actor, "guifashi_draw"))


def _consume_for_demon(
    panel: SkillFlowPanel,
    actor: BattleSpirit,
    action: Dict[str, Any],
    shown_idx: int,
) -> None:
    """恶魔：额外消耗若干张手牌（不含刚揭晓的那张）。"""
    cs = CardState.from_dict(actor.card_state)
    eligible = [i for i in range(len(cs.hand)) if i != shown_idx]
    labels = [f"[{i}] {card_label(cs.hand[i])}" for i in eligible]
    if not labels:
        messagebox.showinfo("提示", "没有可消耗的手牌。")
        return

    def _picked(positions: List[int]) -> None:
        action["consumeHandIndices"] = [eligible[p] for p in positions]
        panel._submit_action(action)

    MultiPickWindow(
        panel,
        "恶魔",
        "选择要消耗的手牌（可多选，消耗后进消耗堆，再抽取等量牌）",
        labels,
        _picked,
        min_pick=1,
    )


def _show(panel: SkillFlowPanel, actor: BattleSpirit) -> None:
    cs = CardState.from_dict(actor.card_state)
    if not cs.hand:
        messagebox.showinfo("提示", "手牌为空，无法揭晓。")
        return

    def _picked(hand_idx: int) -> None:
        card_id = cs.hand[hand_idx]
        action = _base_action(actor, "guifashi_show")
        action["cardHandIndex"] = hand_idx

        def _after_target(target: BattleSpirit) -> None:
            action["targetId"] = target.unique_id
            if card_id == "demon":
                _consume_for_demon(panel, actor, action, hand_idx)
                return
            panel._submit_action(action)

        if card_id in ALLY_TARGET_CARDS:
            panel._pick_target("ally", _after_target)
            return
        if card_id in ENEMY_TARGET_CARDS:
            panel._pick_target("enemy", _after_target)
            return
        if card_id == "demon":
            _consume_for_demon(panel, actor, action, hand_idx)
            return
        panel._submit_action(action)

    IndexChoiceWindow(panel, "揭晓", "选择要打出的手牌", _hand_labels(cs.hand), _picked)


def _cheat(panel: SkillFlowPanel, actor: BattleSpirit) -> None:
    cs = CardState.from_dict(actor.card_state)
    if not cs.hand:
        messagebox.showinfo("提示", "手牌为空，无法逆位。")
        return

    def _picked_hand(hand_idx: int) -> None:
        current = cs.hand[hand_idx]
        options = [c for c in FATE_CARDS if c != current]
        type_labels = [f"{card_label(c)} ({c})" for c in options]

        def _picked_type(type_idx: int) -> None:
            action = _base_action(actor, "guifashi_cheat")
            action["cardHandIndex"] = hand_idx
            action["newCardId"] = options[type_idx]
            panel._submit_action(action)

        IndexChoiceWindow(
            panel, "逆位", f"将 {card_label(current)} 变化为：", type_labels, _picked_type
        )

    IndexChoiceWindow(panel, "逆位", "选择要变化的手牌", _hand_labels(cs.hand), _picked_hand)


def _tengjiao_after_dish(
    panel: SkillFlowPanel, actor: BattleSpirit, dish: str
) -> None:
    from roco.core.spirits.tengjiao import DISH_LAZIJI

    base = _base_action(actor, "tengjiao_skill3")
    if dish == DISH_LAZIJI:
        panel._pick_target(
            "ally",
            lambda t: panel._submit_action({**base, "targetId": t.unique_id}),
            cancellable=False,
        )
        return
    panel._submit_action(base)


def _tengjiao_serve(panel: SkillFlowPanel, actor: BattleSpirit) -> None:
    """出锅：权威引擎先定菜（previewDish），再按菜选目标（不可取消）。"""
    eng = getattr(panel, "eng", None)
    base = _base_action(actor, "tengjiao_skill3")
    if eng is None:
        panel._submit_action(base)
        return
    from roco.core.spirits.tengjiao import tengjiao_logic

    dish = tengjiao_logic.peek_serve_dish(eng, actor)
    if dish is None:
        panel._pending_tengjiao_serve = actor.unique_id  # type: ignore[attr-defined]
        panel._submit_action({**base, "previewDish": True})
        return
    if hasattr(eng, "next_rng"):
        tengjiao_logic.prepare_serve_dish(eng, actor)
    _tengjiao_after_dish(panel, actor, dish)


register_skill_flow("guifashi_draw", _draw)
register_skill_flow("guifashi_show", _show)
register_skill_flow("guifashi_cheat", _cheat)
register_skill_flow("tengjiao_skill3", _tengjiao_serve)
