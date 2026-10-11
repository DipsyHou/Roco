"""Structured combat presentation, paced independently from battle logs."""

from __future__ import annotations

import tkinter as tk
import time
from tkinter import ttk
from dataclasses import dataclass
from typing import List, Optional, Sequence

from roco.core.battle.types import (
    BattleLogEntry,
    BattleLogType,
    BattlePhase,
    BattlePresentationEvent,
    PresentationStage,
)

from .constants import UI_FX_FRAME_MS, UI_FX_FPS
from .theme import Colors

# Pacing knobs — adjust here without touching call sites.
FX_STAGGER_MS = 360
FX_LOG_STAGGER_MS = 190
FX_FLOAT_LIFE_MS = 760
FX_FLOAT_STEPS = max(1, FX_FLOAT_LIFE_MS * UI_FX_FPS // 1000)
FX_HOLD_AFTER_MS = 180
FX_EMPTY_HOLD_MS = 120
FX_STAGE_MIN_MS = {
    PresentationStage.turn_start: 100,
    PresentationStage.normal_action: 100,
    PresentationStage.action_resolution: 100,
    PresentationStage.extra_resolution: 100,
    PresentationStage.turn_end: 100,
}

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


def presentation_stage_text(stage: Optional[PresentationStage]) -> str:
    """Return the quiet status-line copy for the current presentation stage."""
    return {
        PresentationStage.turn_start: "回合开始",
        PresentationStage.turn_end: "回合结束",
    }.get(stage, "结算中…")


class CombatFxMixin:
    """Queues floating numbers after an action, then finishes with a full refresh."""

    _fx_busy: bool
    _fx_jobs: List[str]
    _fx_overlays: List[tk.Toplevel]
    _fx_highlight_actor_id: Optional[str]
    _fx_on_complete: Optional[object]
    _rendered_event_count: int
    _fx_stage_token: Optional[int]
    _completed_presentation_token: Optional[int]

    def _init_combat_fx(self) -> None:
        self._fx_busy = False
        self._fx_jobs = []
        self._fx_overlays = []
        self._fx_highlight_actor_id = None
        self._fx_on_complete = None
        self._rendered_event_count = 0
        self._fx_stage_token = None
        self._completed_presentation_token = None
        self._presented_status_snapshots = {}

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
        self._fx_stage_token = None
        self._presented_status_snapshots.clear()

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
        """Play structured events and reveal their log entries in lockstep."""
        eng = self.eng
        if not eng:
            return

        self._cancel_ai_job()
        self._cancel_combat_fx()

        events = list(getattr(eng.state, "presentation_events", None) or [])
        if self._rendered_event_count > len(events):
            self._rendered_event_count = 0
        steps = events[self._rendered_event_count :]
        if not events and log_start < len(eng.state.battle_log):
            steps = self._legacy_presentation_events(log_start)

        self._fx_busy = True
        self._fx_highlight_actor_id = highlight_actor_id
        self._fx_on_complete = on_complete
        self._fx_stage_token = (
            eng.state.presentation_token
            if eng.state.phase == BattlePhase.presentation
            else None
        )
        started_at = time.monotonic()

        update_highlights = getattr(self, "_update_pet_selection_highlights", None)
        if callable(update_highlights):
            update_highlights()

        self._clear_action_row()
        stage = eng.state.presentation_stage
        ttk.Label(
            self.action_row,
            text=presentation_stage_text(stage),
            style="Muted.TLabel",
        ).pack(side=tk.LEFT)

        if not steps:
            self._schedule_fx(
                max(FX_EMPTY_HOLD_MS, self._remaining_stage_hold(started_at)),
                self._finish_action_fx,
            )
            return

        def _spawn_at(index: int) -> None:
            if not self._fx_busy:
                return
            if index >= len(steps):
                self._schedule_fx(
                    max(FX_HOLD_AFTER_MS, self._remaining_stage_hold(started_at)),
                    self._finish_action_fx,
                )
                return
            step = steps[index]
            self._present_event(step)
            if events:
                self._rendered_event_count = max(
                    self._rendered_event_count, step.sequence + 1
                )
            delay = self._event_delay(step)
            self._schedule_fx(delay, lambda i=index + 1: _spawn_at(i))

        _spawn_at(0)

    def _legacy_presentation_events(self, log_start: int) -> List[BattlePresentationEvent]:
        eng = self.eng
        if not eng:
            return []
        out: List[BattlePresentationEvent] = []
        for index, entry in enumerate(eng.state.battle_log[log_start:], start=log_start):
            data = entry.data or {}
            kind = "log"
            amount = 0
            if entry.type == BattleLogType.damage_dealt:
                kind = "damage"
                amount = int(data.get("damage") or 0)
            elif entry.type == BattleLogType.heal_applied:
                kind = "heal"
                amount = int(data.get("heal") or 0)
            elif entry.type == BattleLogType.effect_applied:
                kind = "effect_applied"
            out.append(
                BattlePresentationEvent(
                    sequence=index,
                    log_index=index,
                    kind=kind,
                    target_id=data.get("targetId"),
                    amount=amount,
                )
            )
        return out

    def _remaining_stage_hold(self, started_at: float) -> int:
        eng = self.eng
        if not eng or eng.state.phase != BattlePhase.presentation:
            return 0
        minimum = FX_STAGE_MIN_MS.get(eng.state.presentation_stage, 0)
        elapsed = int((time.monotonic() - started_at) * 1000)
        return max(0, minimum - elapsed)

    def _event_delay(self, event: BattlePresentationEvent) -> int:
        if event.kind in ("damage", "heal", "effect_applied", "defeat"):
            return FX_STAGGER_MS
        return FX_LOG_STAGGER_MS

    def _present_event(self, event: BattlePresentationEvent) -> None:
        reveal = getattr(self, "_reveal_log", None)
        if callable(reveal):
            reveal(event.log_index)
        if not event.target_id:
            return
        if event.current_hp is not None:
            show_hp = getattr(self, "_show_presented_hp", None)
            if callable(show_hp):
                show_hp(event.target_id, event.current_hp, event.max_hp)
        if event.target_id:
            self._presented_status_snapshots[event.target_id] = (
                event.current_hp,
                event.max_hp,
                event.effects,
                event.charge,
            )
            if event.target_id == getattr(self, "selected_spirit_id", None):
                render_status = getattr(self, "_render_status_panel", None)
                if callable(render_status):
                    render_status()
        if event.kind == "damage" and event.amount > 0:
            self._show_float_number(
                event.target_id, f"-{event.amount}", Colors.LOG_DAMAGE
            )
        elif event.kind == "heal" and event.amount > 0:
            self._show_float_number(
                event.target_id, f"+{event.amount}", Colors.LOG_HEAL
            )
        elif event.kind == "effect_applied":
            labels = {
                "buff": ("增益", Colors.BUFF_FX),
                "debuff": ("减益", Colors.DEBUFF_FX),
                "state": ("状态", Colors.STATE_FX),
            }
            label, color = labels.get(
                event.effect_kind or "state", labels["state"]
            )
            self._show_float_number(event.target_id, label, color)

    def _finish_action_fx(self) -> None:
        on_complete = self._fx_on_complete
        self._fx_busy = False
        self._fx_highlight_actor_id = None
        self._fx_on_complete = None
        stage_token = self._fx_stage_token
        self._fx_stage_token = None
        self._fx_jobs.clear()
        self._advance_presentation_after_fx(stage_token)
        self._presented_status_snapshots.clear()
        # Leave any still-animating overlays alone; they self-destroy.
        self._refresh()
        if callable(on_complete):
            on_complete()

    def _advance_presentation_after_fx(self, token: Optional[int]) -> None:
        eng = self.eng
        if not eng or token is None:
            return
        if (
            eng.state.phase != BattlePhase.presentation
            or eng.state.presentation_token != token
        ):
            return
        self._completed_presentation_token = token
        owner_id = eng.state.presentation_owner_id
        if not self._engine_is_authoritative() and owner_id != self._ally_player_id():
            return
        advance = getattr(eng, "advance_presentation", None)
        if callable(advance):
            advance(token)

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

        step_ms = UI_FX_FRAME_MS
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
