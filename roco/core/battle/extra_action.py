"""Unified extra-action queue + per-slot policy registry.

设计要点（见 docs/mechanics.md）：

- 每个 ``ExtraActionSlot`` 描述一次插入的额外行动：actor + policy_id + source。
- 行动策略以「带名注册的 predicate」形式存在：
  - slot 里只存 ``policy_id``（字符串），便于序列化。
  - registry 把字符串映射到 ``(spirit, action) -> bool`` 的函数。
- 默认 policy ``"unrestricted"``：什么行动都允许。
- ``"cuiding_dance"``：共舞额外行动（与默认相同，保留 policy_id 便于日志/UI 区分）。
- 新精灵若要不同限制，注册一个新的 policy_id 即可。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from .actions import ActionDict
from .types import BattleSpirit

ExtraActionPredicate = Callable[[BattleSpirit, ActionDict], bool]


@dataclass(frozen=True)
class ExtraActionUI:
    """How an action panel should present one extra-action policy.

    Kept next to the policy predicate so a new spirit declares its UI rules in
    the same place as its action rules, instead of the panel growing another
    ``policy_id == "..."`` branch.
    """

    hint: str = ""
    allow_normal_attack: bool = True
    allow_gather: bool = True
    allow_skip: bool = False
    # Which half of the skill list to show: normal skills or ``special`` ones.
    special_skills: bool = False
    # When set, only these skill ids appear (overrides the special_skills split).
    allowed_skill_ids: Optional[Tuple[str, ...]] = None


DEFAULT_EXTRA_ACTION_UI = ExtraActionUI()


@dataclass
class ExtraActionSlot:
    actor_id: str
    policy_id: str = "unrestricted"
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actorId": self.actor_id,
            "policyId": self.policy_id,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExtraActionSlot":
        return cls(
            actor_id=d.get("actorId") or d.get("actor_id", ""),
            policy_id=d.get("policyId") or d.get("policy_id") or "unrestricted",
            source=d.get("source", ""),
        )


_REGISTRY: Dict[str, ExtraActionPredicate] = {}
_UI_REGISTRY: Dict[str, ExtraActionUI] = {}


def register_policy(
    policy_id: str,
    predicate: ExtraActionPredicate,
    ui: Optional[ExtraActionUI] = None,
) -> None:
    _REGISTRY[policy_id] = predicate
    if ui is not None:
        _UI_REGISTRY[policy_id] = ui


def policy_ui(policy_id: str) -> ExtraActionUI:
    """Presentation rules for ``policy_id`` (defaults to a normal action panel)."""
    return _UI_REGISTRY.get(policy_id, DEFAULT_EXTRA_ACTION_UI)


def policy_allows(slot: ExtraActionSlot, actor: BattleSpirit, action: ActionDict) -> bool:
    fn = _REGISTRY.get(slot.policy_id) or _REGISTRY["unrestricted"]
    return fn(actor, action)


def _unrestricted(_actor: BattleSpirit, _action: ActionDict) -> bool:
    return True


register_policy("unrestricted", _unrestricted)
