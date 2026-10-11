"""Detail panel: stats, effects, and per-spirit extra sections."""

from __future__ import annotations

import copy
import tkinter as tk
from typing import List, Tuple

from roco.core.battle.effect_display import format_spirit_effects
from roco.core.battle.shield import max_shield
from roco.core.battle.timeline import action_value
from roco.core.battle.types import BattleSpirit, DamageType, StatType
from roco.core.battle.utils import get_effective_stat
from roco.core.spirits import get_spirit_logic

from .theme import hp_text_tag, parse_effect_line

_SEP = "─" * 32
_SECTION_TITLES = (
    ("buff", "正面效果"),
    ("debuff", "负面效果"),
    ("state", "状态效果"),
)
_DAMAGE_TYPE_NAMES = {
    DamageType.fire: "火",
    DamageType.water: "水",
    DamageType.grass: "草",
    DamageType.ground: "地",
    DamageType.wind: "风",
    DamageType.physical: "物理",
    DamageType.ice: "冰",
    DamageType.electric: "电",
    DamageType.poison: "毒",
    DamageType.light: "光",
    DamageType.dark: "暗",
    DamageType.dragon: "龙",
}


class StatusPanelMixin:
    """Shows the selected spirit; extra sections come from its SpiritLogic."""

    def _display_stats(self, spirit: BattleSpirit) -> List[Tuple[str, int, float]]:
        """Four abilities: base value and realtime effective value."""
        eng = self.eng
        assert eng
        return [
            ("生命", spirit.base_stats.hp, spirit.max_hp),
            ("攻击", spirit.base_stats.attack, get_effective_stat(spirit, StatType.attack)),
            ("防御", spirit.base_stats.defense, get_effective_stat(spirit, StatType.defense)),
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

        presented = getattr(self, "_presented_status_snapshots", {}).get(sid)
        if getattr(self, "_fx_busy", False) and presented is not None:
            shown = copy.copy(spirit)
            (
                current_hp,
                max_hp,
                effects,
                charge,
            ) = presented
            if current_hp is not None:
                shown.current_hp = int(current_hp)
            if max_hp is not None:
                shown.max_hp = int(max_hp)
            shown.effects = list(effects)
            if charge is not None:
                shown.charge = float(charge)
            spirit = shown

        source_names = {
            s.unique_id: s.name
            for pid in (self.p1, self.p2)
            for s in eng.state.players[pid].spirits
        }
        owner = "Player 1" if spirit.owner_id == self.p1 else "Player 2"
        if spirit.unique_id == eng.state.active_actor_id:
            av = 0.0
        else:
            av = action_value(spirit.charge, max(1, eng.get_effective_speed(spirit)))
        hp_ratio = (spirit.current_hp / spirit.max_hp) if spirit.max_hp > 0 else 0.0

        # Header
        ins(spirit.name, "title")
        nl()
        ins(f"{owner}  ·  槽位 [{spirit.slot}]", "muted")
        nl()
        ins("生命  ", "label")
        ins(str(spirit.current_hp), hp_text_tag(hp_ratio))
        ins(f" / {spirit.max_hp}", "muted")
        bar_filled = max(0, min(10, int(round(hp_ratio * 10))))
        ins(f"  [{'█' * bar_filled}{'░' * (10 - bar_filled)}]", "muted")
        nl()
        ins("护盾  ", "label")
        ins(str(max_shield(spirit)), "value")
        nl()
        ins("行动值  ", "label")
        ins(f"{av:.1f}", "accent")
        nl()
        ins(_SEP, "sep")
        nl()

        # Attributes
        ins("能力值", "section")
        nl()
        for name, base, real in self._display_stats(spirit):
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

        ins("固有属性", "section")
        nl()
        ins("  " + "、".join(_DAMAGE_TYPE_NAMES[e] for e in spirit.elements), "value")
        nl()
        ins("抗性", "section")
        nl()
        resistances = [
            (damage_type, spirit.resistance_to(damage_type))
            for damage_type in _DAMAGE_TYPE_NAMES
            if spirit.resistance_to(damage_type) != 0
        ]
        if not resistances:
            ins("  无非零抗性", "muted")
            nl()
        for damage_type, resistance in resistances:
            ins(f"  {_DAMAGE_TYPE_NAMES[damage_type]}  ", "label")
            pct = int(round(resistance * 100))
            ins(f"{pct:+d}%", "stat_up" if pct > 0 else "stat_down")
            nl()

        # Effects by category (including shields under 状态效果).
        buckets: dict[str, list[tuple[str, str]]] = {
            "buff": [],
            "debuff": [],
            "state": [],
        }
        for line in format_spirit_effects(spirit.effects, source_names, spirit):
            tag, body = parse_effect_line(line)
            if tag not in buckets:
                tag = "state"
            buckets[tag].append((tag, body))

        for key, title in _SECTION_TITLES:
            ins(title, "section")
            nl()
            for tag, body in buckets[key]:
                ins("  • ", "muted")
                ins(body, tag)
                nl()

        logic = get_spirit_logic(spirit.template_id)
        for title, rows in (logic.describe_detail_sections(spirit) if logic else []):
            nl()
            ins(_SEP, "sep")
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
