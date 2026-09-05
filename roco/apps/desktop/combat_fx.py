"""Combat presentation: floating damage/heal numbers and post-action pacing."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import List, Optional, Sequence

from roco.core.battle.types import BattleLogEntry, BattleLogType

from .theme import Colors

# Pacing knobs — adjust here without touching call sites.
FX_STAGGER_MS = 500
FX_FLOAT_LIFE_MS = 1000
FX_FLOAT_STEPS = 30
FX_HOLD_AFTER_MS = 0
FX_EMPTY_HOLD_MS = 0

# Big bold floats; magenta is the chromakey for a transparent label backdrop.
FX_FONT = ("Microsoft YaHei UI", 20, "bold")
FX_TRANSPARENT_KEY = "#ff00ff"
FX_OUTLINE = "#ffffff"
FX_OUTLINE_OFFSETS = (
    (-2, 0),
    (2, 0),
    (0, -2),
    (0, 2),
    (-2, -2),
    (-2, 2),
    (2, -2),
    (2, 2),
)


@dataclass(frozen=True)
class FloatStep:
    spirit_id: str
    kind: str  # "damage" | "heal"
    amount: int


def float_steps_from_logs(logs: Sequence[BattleLogEntry]) -> List[FloatStep]:
    """Extract ordered float-number steps from a battle_log delta."""
    steps: List[FloatStep] = []
    for entry in logs:
        data = entry.data or {}
        target_id = data.get("targetId")
        if not target_id:
            continue
        if entry.type == BattleLogType.damage_dealt:
            amount = int(data.get("damage") or 0)
            if amount > 0:
                steps.append(FloatStep(str(target_id), "damage", amount))
            continue
        # heal_applied, or passives that heal inline (e.g. 紧急支援).
        if entry.type == BattleLogType.heal_applied or "heal" in data:
            amount = int(data.get("heal") or 0)
            if amount > 0:
                steps.append(FloatStep(str(target_id), "heal", amount))
    return steps


class CombatFxMixin:
    """Queues floating numbers after an action, then finishes with a full refresh."""

    _fx_busy: bool
    _fx_jobs: List[str]
    _fx_overlays: List[tk.Toplevel]
    _fx_highlight_actor_id: Optional[str]
    _fx_on_complete: Optional[object]

    def _init_combat_fx(self) -> None:
        self._fx_busy = False
        self._fx_jobs = []
        self._fx_overlays = []
        self._fx_highlight_actor_id = None
        self._fx_on_complete = None

    def _cancel_combat_fx(self, *, destroy_labels: bool = True) -> None:
        for job in self._fx_jobs:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._fx_jobs.clear()
        if destroy_labels:
            for overlay in self._fx_overlays:
                try:
                    if overlay.winfo_exists():
                        overlay.destroy()
                except Exception:
                    pass
            self._fx_overlays.clear()
        self._fx_busy = False
        self._fx_highlight_actor_id = None
        self._fx_on_complete = None

    def _schedule_fx(self, delay_ms: int, callback) -> None:
        job = self.after(delay_ms, callback)
        self._fx_jobs.append(job)

    def _play_action_fx(
        self,
        log_start: int,
        *,
        highlight_actor_id: Optional[str] = None,
        on_complete=None,
    ) -> None:
        """Present log delta from ``log_start``, then refresh the full UI."""
        eng = self.eng
        if not eng:
            return

        self._cancel_ai_job()
        self._cancel_combat_fx()

        logs = eng.state.battle_log
        if log_start < 0:
            log_start = 0
        if log_start > len(logs):
            log_start = len(logs)
        delta = logs[log_start:]
        steps = float_steps_from_logs(delta)

        self._fx_busy = True
        self._fx_highlight_actor_id = highlight_actor_id
        self._fx_on_complete = on_complete

        self._clear_action_row()
        self.action_hint.set("结算中…")

        # HP / energy / log catch up immediately; turn highlight stays frozen.
        self._update_pet_strip()
        self._render_logs()

        if not steps:
            self._schedule_fx(FX_EMPTY_HOLD_MS, self._finish_action_fx)
            return

        def _spawn_at(index: int) -> None:
            if not self._fx_busy:
                return
            if index >= len(steps):
                self._schedule_fx(FX_HOLD_AFTER_MS, self._finish_action_fx)
                return
            step = steps[index]
            if step.kind == "damage":
                self._show_float_number(step.spirit_id, f"-{step.amount}", Colors.LOG_DAMAGE)
            else:
                self._show_float_number(step.spirit_id, f"+{step.amount}", Colors.LOG_HEAL)
            delay = FX_STAGGER_MS if index + 1 < len(steps) else FX_FLOAT_LIFE_MS
            self._schedule_fx(delay, lambda i=index + 1: _spawn_at(i))

        _spawn_at(0)

    def _finish_action_fx(self) -> None:
        on_complete = self._fx_on_complete
        self._fx_busy = False
        self._fx_highlight_actor_id = None
        self._fx_on_complete = None
        self._fx_jobs.clear()
        # Leave any still-animating overlays alone; they self-destroy.
        self._refresh()
        if callable(on_complete):
            on_complete()

    def _show_float_number(self, spirit_id: str, text: str, color: str) -> None:
        widgets = self._pet_card_widgets.get(spirit_id)
        if not widgets:
            return
        wrap = widgets.get("avatar_wrap")
        if not isinstance(wrap, tk.Frame) or not wrap.winfo_exists():
            return

        wrap.update_idletasks()
        overlay = tk.Toplevel(self)
        overlay.overrideredirect(True)
        overlay.wm_attributes("-topmost", True)
        bg = FX_TRANSPARENT_KEY
        try:
            overlay.wm_attributes("-transparentcolor", FX_TRANSPARENT_KEY)
        except tk.TclError:
            # Platforms without chromakey: fall back to the card color.
            bg = wrap.cget("bg")

        # Measure text, then paint white offsets + colored fill on a chromakey canvas.
        probe = tk.Label(overlay, text=text, font=FX_FONT)
        probe.update_idletasks()
        pad = 4
        width = probe.winfo_reqwidth() + pad * 2
        height = probe.winfo_reqheight() + pad * 2
        probe.destroy()

        canvas = tk.Canvas(
            overlay,
            width=width,
            height=height,
            bg=bg,
            highlightthickness=0,
            borderwidth=0,
        )
        canvas.pack()
        cx, cy = width // 2, height // 2
        for ox, oy in FX_OUTLINE_OFFSETS:
            canvas.create_text(
                cx + ox,
                cy + oy,
                text=text,
                fill=FX_OUTLINE,
                font=FX_FONT,
                anchor="center",
            )
        canvas.create_text(cx, cy, text=text, fill=color, font=FX_FONT, anchor="center")
        overlay.update_idletasks()

        base_x = wrap.winfo_rootx() + wrap.winfo_width() // 2 - overlay.winfo_width() // 2
        base_y = wrap.winfo_rooty() + int(wrap.winfo_height() * 0.28) - overlay.winfo_height() // 2
        overlay.geometry(f"+{base_x}+{base_y}")
        self._fx_overlays.append(overlay)

        step_ms = max(1, FX_FLOAT_LIFE_MS // FX_FLOAT_STEPS)
        dy = 28 / FX_FLOAT_STEPS

        def _tick(frame: int, y_off: float) -> None:
            if not overlay.winfo_exists():
                return
            if frame >= FX_FLOAT_STEPS:
                try:
                    overlay.destroy()
                except Exception:
                    pass
                if overlay in self._fx_overlays:
                    self._fx_overlays.remove(overlay)
                return
            y_off -= dy
            try:
                overlay.geometry(f"+{base_x}+{base_y + int(y_off)}")
            except Exception:
                return
            job = self.after(step_ms, lambda: _tick(frame + 1, y_off))
            self._fx_jobs.append(job)

        _tick(0, 0.0)
