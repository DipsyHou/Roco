"""Small desktop UI helper functions."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from roco.core.battle.effects import get_freeze_stacks
from roco.core.battle.engine import BattleEngine
from roco.core.battle.types import BattleSpirit
from roco.core.spirits import get_spirit_logic, get_spirit_template

def _templates_from_ids(ids: List[str]):
    out = []
    for sid in ids:
        tpl = get_spirit_template(sid)
        if tpl:
            out.append(tpl)
    return out


def pick_targets(engine, actor: BattleSpirit, mode: str) -> List[BattleSpirit]:
    """Ordered candidate targets for ``mode`` ("enemy" / "ally" / any-on-field).

    Works for both the local and the remote engine via their public surface;
    UIs must not read engine-private player-id lists.
    """
    pid = actor.owner_id
    if mode == "enemy":
        opp = engine.get_opponent_id(pid)
        return sorted(engine.get_active_spirits(opp), key=lambda s: s.slot)
    if mode == "ally":
        return sorted(engine.get_active_spirits(pid), key=lambda s: s.slot)
    ids = engine.player_ids
    p1, p2 = ids[0], ids[1]
    return sorted(
        engine.get_active_spirits(p1) + engine.get_active_spirits(p2),
        key=lambda s: (s.owner_id != p1, s.slot),
    )


def center_on_parent(window, parent) -> None:
    """Center a Toplevel ``window`` over ``parent`` (call after ``update_idletasks``)."""
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    ww = window.winfo_width()
    wh = window.winfo_height()
    x = px + max(0, (pw - ww) // 2)
    y = py + max(0, (ph - wh) // 2)
    window.geometry(f"+{x}+{y}")


def _runtime_root() -> Path:
    """Return runtime root for source run or PyInstaller bundle."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[3]


def _skill_available(eng: BattleEngine, actor: BattleSpirit, sk) -> tuple[bool, str]:
    """Whether ``actor`` can currently pay for ``sk``, plus a reason if not."""
    logic = get_spirit_logic(actor.template_id)
    if logic is not None:
        personal = logic.check_skill_resource(actor, sk)
        if personal is not None:
            return personal
    cost = eng.effective_skill_energy_cost(actor, sk)
    pd = eng.state.players[actor.owner_id]
    if pd.team_energy < cost:
        return False, f"需要{cost}能量"
    return True, ""


def _skill_cost_label(actor: BattleSpirit, sk, eng: BattleEngine | None = None) -> str:
    """Cost text shown on a skill button."""
    logic = get_spirit_logic(actor.template_id)
    if logic is not None:
        label = logic.describe_skill_cost(actor, sk)
        if label is not None:
            return label
    if eng is not None:
        return f"能量 {eng.effective_skill_energy_cost(actor, sk)}"
    return f"能量 {sk.energy_cost or 0}"
