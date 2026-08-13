"""Shared visual theme for the desktop battle client."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, Union

from roco.core.battle.types import BattleLogType, BattleSpirit

from roco.core.battle.effects import get_freeze_stacks

from .constants import UI_FONT, UI_FONT_TITLE, UI_MONO_FONT

WindowLike = Union[tk.Tk, tk.Toplevel]


class Colors:
    BG = "#0f1419"
    PANEL = "#1a2332"
    PANEL_ALT = "#242f42"
    BORDER = "#2d3a4f"
    BORDER_ACTIVE = "#3b82f6"
    BORDER_SELECTED = "#f59e0b"
    TEXT = "#e8edf4"
    TEXT_MUTED = "#8b9cb3"
    ACCENT = "#3b82f6"
    ENERGY = "#3b82f6"
    HP_HIGH = "#22c55e"
    HP_MID = "#eab308"
    HP_LOW = "#ef4444"
    FREEZE = "#7dd3fc"
    TIMELINE_ACTIVE = "#1e3a5f"
    TIMELINE_ALLY = "#17263a"
    LOG_DAMAGE = "#f87171"
    LOG_HEAL = "#4ade80"
    LOG_PASSIVE = "#a78bfa"
    LOG_EFFECT = "#60a5fa"
    LOG_DEFEAT = "#fb7185"
    LOG_DEFAULT = "#cbd5e1"
    INPUT_BG = "#111827"
    TROUGH = "#111827"
    TIMELINE_ENEMY = "#3a2026"
    TIMELINE_ENEMY_ACTIVE = "#512731"
    TIMELINE_EXTRA = "#f59e0b"


def apply_theme(root: WindowLike) -> ttk.Style:
    """Apply dark battle theme to a Tk root or Toplevel."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    c = Colors
    root.configure(bg=c.BG)

    style.configure(".", background=c.BG, foreground=c.TEXT, font=UI_FONT)
    style.configure("TFrame", background=c.BG)
    style.configure("Card.TFrame", background=c.PANEL)
    style.configure("TLabel", background=c.BG, foreground=c.TEXT, font=UI_FONT)
    style.configure("Card.TLabel", background=c.PANEL, foreground=c.TEXT, font=UI_FONT)
    style.configure("Muted.TLabel", background=c.BG, foreground=c.TEXT_MUTED, font=UI_FONT)
    style.configure("Section.TLabel", background=c.BG, foreground=c.TEXT, font=UI_FONT_TITLE)
    style.configure("TButton", padding=(10, 6))
    style.map(
        "TButton",
        background=[("active", c.PANEL_ALT), ("disabled", c.PANEL)],
        foreground=[("disabled", c.TEXT_MUTED)],
    )
    style.configure("Primary.TButton", background=c.ACCENT, foreground="#ffffff")
    style.map("Primary.TButton", background=[("active", "#2563eb")])
    style.configure("TLabelframe", background=c.BG, foreground=c.TEXT_MUTED)
    style.configure("TLabelframe.Label", background=c.BG, foreground=c.TEXT_MUTED, font=UI_FONT)
    style.configure("Card.TLabelframe", background=c.PANEL, foreground=c.TEXT_MUTED)
    style.configure(
        "Card.TLabelframe.Label",
        background=c.PANEL,
        foreground=c.TEXT,
        font=UI_FONT_TITLE,
    )
    style.configure(
        "Energy.Horizontal.TProgressbar",
        troughcolor=c.TROUGH,
        background=c.ENERGY,
        bordercolor=c.BORDER,
        lightcolor=c.ENERGY,
        darkcolor=c.ENERGY,
    )
    for name, color in (
        ("HP.High.Horizontal.TProgressbar", c.HP_HIGH),
        ("HP.Mid.Horizontal.TProgressbar", c.HP_MID),
        ("HP.Low.Horizontal.TProgressbar", c.HP_LOW),
    ):
        style.configure(
            name,
            troughcolor=c.TROUGH,
            background=color,
            bordercolor=c.BORDER,
            lightcolor=color,
            darkcolor=color,
        )
    style.configure(
        "TProgressbar",
        troughcolor=c.TROUGH,
        background=c.HP_HIGH,
        bordercolor=c.BORDER,
    )
    return style


def configure_text_widget(widget: tk.Text, *, mono: bool = False) -> None:
    widget.configure(
        bg=Colors.PANEL,
        fg=Colors.TEXT,
        insertbackground=Colors.TEXT,
        relief="flat",
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
        highlightcolor=Colors.BORDER_ACTIVE,
        font=UI_MONO_FONT if mono else UI_FONT,
        padx=10,
        pady=8,
        selectbackground=Colors.BORDER_ACTIVE,
        selectforeground=Colors.TEXT,
    )


def configure_status_widget(widget: tk.Text) -> None:
    """Rich tags for the spirit detail panel."""
    configure_text_widget(widget)
    c = Colors
    widget.tag_configure("title", font=UI_FONT_TITLE, foreground=c.ACCENT)
    widget.tag_configure("muted", foreground=c.TEXT_MUTED)
    widget.tag_configure("section", font=(UI_FONT[0], UI_FONT[1], "bold"), foreground=c.TEXT)
    widget.tag_configure("label", foreground=c.TEXT_MUTED)
    widget.tag_configure("value", foreground=c.TEXT)
    widget.tag_configure("hp_high", foreground=c.HP_HIGH, font=(UI_FONT[0], UI_FONT[1], "bold"))
    widget.tag_configure("hp_mid", foreground=c.HP_MID, font=(UI_FONT[0], UI_FONT[1], "bold"))
    widget.tag_configure("hp_low", foreground=c.HP_LOW, font=(UI_FONT[0], UI_FONT[1], "bold"))
    widget.tag_configure("stat_up", foreground=c.HP_HIGH)
    widget.tag_configure("stat_down", foreground=c.LOG_DAMAGE)
    widget.tag_configure("stat_flat", foreground=c.TEXT_MUTED)
    widget.tag_configure("buff", foreground=c.LOG_HEAL)
    widget.tag_configure("debuff", foreground=c.LOG_DAMAGE)
    widget.tag_configure("state", foreground=c.LOG_PASSIVE)
    widget.tag_configure("accent", foreground=c.ACCENT)
    widget.tag_configure("sep", foreground=c.BORDER)
    widget.tag_configure("empty", foreground=c.TEXT_MUTED)
    widget.tag_configure("card", foreground=c.LOG_EFFECT)


def hp_text_tag(ratio: float) -> str:
    if ratio <= 0.25:
        return "hp_low"
    if ratio <= 0.5:
        return "hp_mid"
    return "hp_high"


def parse_effect_line(line: str) -> tuple[str, str]:
    """Map effect_display line prefix to a Text tag."""
    if line.startswith("[buff]"):
        return "buff", line[6:]
    if line.startswith("[debuff]"):
        return "debuff", line[8:]
    if line.startswith("[state]"):
        return "state", line[7:]
    return "value", line


def log_tag_for_entry(log_type: Optional[BattleLogType]) -> str:
    if log_type is None:
        return "default"
    mapping = {
        BattleLogType.damage_dealt: "damage",
        BattleLogType.heal_applied: "heal",
        BattleLogType.passive_triggered: "passive",
        BattleLogType.effect_applied: "effect",
        BattleLogType.effect_removed: "effect",
        BattleLogType.spirit_defeated: "defeat",
        BattleLogType.action_executed: "default",
        BattleLogType.turn_start: "default",
        BattleLogType.battle_end: "defeat",
        BattleLogType.stunned: "effect",
    }
    return mapping.get(log_type, "default")


def configure_log_widget(widget: tk.Text) -> None:
    configure_text_widget(widget, mono=True)
    widget.tag_configure("damage", foreground=Colors.LOG_DAMAGE)
    widget.tag_configure("heal", foreground=Colors.LOG_HEAL)
    widget.tag_configure("passive", foreground=Colors.LOG_PASSIVE)
    widget.tag_configure("effect", foreground=Colors.LOG_EFFECT)
    widget.tag_configure("defeat", foreground=Colors.LOG_DEFEAT, font=(UI_MONO_FONT[0], UI_MONO_FONT[1], "bold"))
    widget.tag_configure("default", foreground=Colors.LOG_DEFAULT)


def log_tag_for_message(message: str) -> str:
    """Fallback when log entry type is unavailable."""
    if "击败" in message:
        return "defeat"
    if any(token in message for token in ("回复", "治疗", "回血")):
        return "heal"
    if any(token in message for token in ("被动", "触发", "共振")):
        return "passive"
    if any(token in message for token in ("伤害", "造成", "固伤")):
        return "damage"
    if any(token in message for token in ("获得", "层", "效果", "浸润", "分流", "升温", "灼烧")):
        return "effect"
    return "default"


def configure_listbox(widget: tk.Listbox) -> None:
    widget.configure(
        bg=Colors.PANEL,
        fg=Colors.TEXT,
        selectbackground=Colors.BORDER_ACTIVE,
        selectforeground=Colors.TEXT,
        highlightthickness=1,
        highlightbackground=Colors.BORDER,
        relief="flat",
        borderwidth=0,
    )


def hp_progress_style(ratio: float) -> str:
    if ratio <= 0.25:
        return "HP.Low.Horizontal.TProgressbar"
    if ratio <= 0.5:
        return "HP.Mid.Horizontal.TProgressbar"
    return "HP.High.Horizontal.TProgressbar"


HP_BAR_WIDTH = 118
HP_BAR_HEIGHT = 12


def hp_bar_fill_color(ratio: float) -> str:
    if ratio <= 0.25:
        return Colors.HP_LOW
    if ratio <= 0.5:
        return Colors.HP_MID
    return Colors.HP_HIGH


def draw_spirit_hp_bar(
    canvas: tk.Canvas,
    spirit: BattleSpirit,
    *,
    width: int = HP_BAR_WIDTH,
    height: int = HP_BAR_HEIGHT,
) -> None:
    """Draw HP fill; freeze execute zone (at or below 1%×max×stacks) is blue."""
    canvas.delete("all")
    max_hp = max(1, spirit.max_hp)
    hp = max(0, min(spirit.current_hp, max_hp))
    hp_ratio = hp / max_hp
    hp_width = int(width * hp_ratio)

    canvas.create_rectangle(0, 0, width, height, fill=Colors.BORDER, outline=Colors.BORDER)

    if hp_width <= 0:
        return

    stacks = get_freeze_stacks(spirit)
    if stacks > 0:
        thresh_width = max(1, int(width * min(1.0, 0.01 * stacks)))
        blue_end = min(hp_width, thresh_width)
        if blue_end > 0:
            canvas.create_rectangle(0, 0, blue_end, height, fill=Colors.FREEZE, outline="")
        if hp_width > thresh_width:
            fill = hp_bar_fill_color(hp_ratio)
            canvas.create_rectangle(thresh_width, 0, hp_width, height, fill=fill, outline="")
    else:
        fill = hp_bar_fill_color(hp_ratio)
        canvas.create_rectangle(0, 0, hp_width, height, fill=fill, outline="")


def draw_vertical_spirit_hp_bar(
    canvas: tk.Canvas,
    spirit: BattleSpirit,
    *,
    width: int,
    height: int,
) -> None:
    """Draw a bottom-up HP bar, including the freeze execute zone."""
    canvas.delete("all")
    max_hp = max(1, spirit.max_hp)
    hp = max(0, min(spirit.current_hp, max_hp))
    hp_ratio = hp / max_hp
    hp_height = int(height * hp_ratio)
    canvas.create_rectangle(0, 0, width, height, fill=Colors.BORDER, outline="")
    if hp_height <= 0:
        return

    fill_top = height - hp_height
    stacks = get_freeze_stacks(spirit)
    if stacks > 0:
        threshold_height = max(1, int(height * min(1.0, 0.01 * stacks)))
        freeze_top = max(fill_top, height - threshold_height)
        if freeze_top > fill_top:
            canvas.create_rectangle(
                0,
                fill_top,
                width,
                freeze_top,
                fill=hp_bar_fill_color(hp_ratio),
                outline="",
            )
        canvas.create_rectangle(
            0,
            freeze_top,
            width,
            height,
            fill=Colors.FREEZE,
            outline="",
        )
    else:
        canvas.create_rectangle(
            0,
            fill_top,
            width,
            height,
            fill=hp_bar_fill_color(hp_ratio),
            outline="",
        )
