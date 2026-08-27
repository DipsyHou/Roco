"""Detail panel: stats, effects, and per-spirit extra sections."""

from __future__ import annotations

import tkinter as tk
from typing import List

from roco.core.battle.effect_display import format_spirit_effects
from roco.core.battle.shield import max_shield
from roco.core.battle.timeline import action_value
from roco.core.battle.types import BattleSpirit, StatType
from roco.core.battle.utils import get_effective_stat
from roco.core.spirits import get_spirit_logic

from .theme import hp_text_tag, parse_effect_line


class StatusPanelMixin:
    """Shows the selected spirit; extra sections come from its SpiritLogic."""

    def _display_stats(self, spirit: BattleSpirit) -> List[tuple[str, int, float]]:
        """Unified six-attribute display values (base, realtime effective)."""
        eng = self.eng
        assert eng
        base_hp = spirit.max_hp
        now_hp = spirit.current_hp
        return [
            ("HP", base_hp, now_hp),
            ("物攻", spirit.base_stats.atk, get_effective_stat(spirit, StatType.atk)),
            ("魔攻", spirit.base_stats.mag_atk, get_effective_stat(spirit, StatType.mag_atk)),
            ("物防", spirit.base_stats.def_, get_effective_stat(spirit, StatType.def_)),
            ("魔防", spirit.base_stats.mag_def, get_effective_stat(spirit, StatType.mag_def)),
            # 速度走 BattleEngine 实时速度管线（含邻接、状态等）。
            ("速度", spirit.base_stats.speed, eng.get_effective_speed(spirit)),
        ]

    def _render_status_panel(self) -> None:
        eng = self.eng
        assert eng
        sid = self.selected_spirit_id
        w = self.status_text
        w.configure(state="normal")
        w.delete("1.0", tk.END)

        def ins(text: str, tag: str = "value") -> None:
            w.insert(tk.END, text, tag)

        def nl() -> None:
            w.insert(tk.END, "\n")

        if not sid:
            ins("点击精灵查看详情", "empty")
            w.configure(state="disabled")
            return
        spirit = eng.find_spirit_anywhere(sid)
        if not spirit:
            ins("未找到该宠物", "empty")
            w.configure(state="disabled")
            return

        source_names = {
            s.unique_id: s.name
            for pid in (self.p1, self.p2)
            for s in eng.state.players[pid].spirits
        }
        owner = "Player 1" if spirit.owner_id == self.p1 else "Player 2"
        av = action_value(spirit.charge, max(1, eng.get_effective_speed(spirit)))
        hp_ratio = (spirit.current_hp / spirit.max_hp) if spirit.max_hp > 0 else 0.0

        ins(spirit.name, "title")
        nl()
        ins(f"{owner}  ·  槽位 [{spirit.slot}]", "muted")
        nl()
        ins("HP  ", "label")
        ins(str(spirit.current_hp), hp_text_tag(hp_ratio))
        ins(f" / {spirit.max_hp}", "muted")
        bar_filled = max(0, min(10, int(round(hp_ratio * 10))))
        ins(f"  [{'█' * bar_filled}{'░' * (10 - bar_filled)}]", "muted")
        nl()
        ins(f"AV  {av:.1f}", "accent")
        nl()
        ins("─" * 32, "sep")
        nl()
        ins("属性", "section")
        nl()

        for name, base, real in self._display_stats(spirit):
            if name == "HP":
                continue
            real_disp = int(round(real))
            delta = real_disp - base
            ins(f"  {name}  ", "label")
            ins(str(base), "value")
            if delta > 0:
                ins(f"  (+{delta})", "stat_up")
            elif delta < 0:
                ins(f"  ({delta})", "stat_down")
            else:
                ins("  (—)", "stat_flat")
            nl()

        nl()
        ins("  护盾  ", "label")
        ins(str(max_shield(spirit)), "value")

        nl()
        ins("状态效果", "section")
        nl()
        fx = format_spirit_effects(spirit.effects, source_names, spirit)
        if not fx:
            ins("  （无）", "empty")
            nl()
        else:
            for line in fx:
                tag, body = parse_effect_line(line)
                ins("  • ", "muted")
                ins(body, tag)
                nl()

        logic = get_spirit_logic(spirit.template_id)
        for title, rows in (logic.describe_detail_sections(spirit) if logic else []):
            nl()
            ins("─" * 32, "sep")
            nl()
            ins(title, "section")
            nl()
            for label, value in rows:
                if value is None:
                    ins(label, "empty")
                else:
                    ins(label, "label")
                    ins(value, "card")
                nl()

        w.configure(state="disabled")
