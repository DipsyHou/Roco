"""Timeline panel: predicted turn order."""

from __future__ import annotations

import tkinter as tk
from typing import List

from roco.core.battle.timeline import action_value
from roco.core.battle.types import BattleSpirit

from .constants import UI_MONO_FONT
from .theme import Colors


class TimelineMixin:
    """Renders the upcoming actors predicted by the engine."""

    def _iter_all_spirits(self) -> List[BattleSpirit]:
        eng = self.eng
        assert eng
        spirits: List[BattleSpirit] = []
        for pid in (self.p1, self.p2):
            spirits.extend(eng.state.players[pid].spirits)
        return spirits

    def _render_timeline(self) -> None:
        eng = self.eng
        assert eng
        for child in self.timeline_frame.winfo_children():
            child.destroy()
        self._timeline_image_refs.clear()

        alive = [s for s in self._iter_all_spirits() if s.is_alive]

        def sort_key(s: BattleSpirit) -> tuple:
            speed = max(1, eng.get_effective_speed(s))
            return (action_value(s.charge, speed), s.unique_id)

        active_id = eng.state.active_actor_id
        active = [s for s in alive if s.unique_id == active_id]
        extra_queue = list(getattr(eng.state, "extra_action_queue", []))

        def slot_actor_id(slot) -> str:
            if isinstance(slot, dict):
                return str(slot.get("actorId") or slot.get("actor_id") or "")
            return str(getattr(slot, "actor_id", ""))

        current_is_extra = bool(
            active_id
            and extra_queue
            and slot_actor_id(extra_queue[0]) == active_id
        )
        pending_slots = extra_queue[1:] if current_is_extra else extra_queue

        # During an extra action, the same spirit may still have a normal AV
        # turn pending; deliberately show both entries.
        normal_candidates = alive if current_is_extra else [
            s for s in alive if s.unique_id != active_id
        ]
        waiting = sorted(normal_candidates, key=sort_key)

        rows: list[tuple[BattleSpirit, bool, bool]] = []
        rows.extend((s, current_is_extra, True) for s in active)
        for slot in pending_slots:
            spirit = eng.find_spirit_anywhere(slot_actor_id(slot))
            if spirit is not None and spirit.is_alive:
                rows.append((spirit, True, False))
        rows.extend((s, False, False) for s in waiting)

        ally_id = self._ally_player_id()
        for s, is_extra, is_current in rows:
            is_enemy = s.owner_id != ally_id
            if is_enemy:
                row_bg = (
                    Colors.TIMELINE_ENEMY_ACTIVE
                    if is_current
                    else Colors.TIMELINE_ENEMY
                )
            else:
                row_bg = (
                    Colors.TIMELINE_ACTIVE
                    if is_current
                    else Colors.TIMELINE_ALLY
                )
            row = tk.Frame(self.timeline_frame, bg=row_bg, padx=6, pady=3)
            row.pack(fill=tk.X, pady=1)
            select = getattr(self, "_select_spirit", None)
            if callable(select):
                row.bind("<Button-1>", lambda _e, sid=s.unique_id: select(sid))
                row.configure(cursor="hand2")

            extra_mark = None
            if is_extra:
                extra_mark = tk.Frame(
                    row,
                    bg=Colors.TIMELINE_EXTRA,
                    width=3,
                )
                extra_mark.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 3))

            mirror = not is_enemy
            img = self._load_avatar(
                s.name,
                mirror=mirror,
                template_id=s.template_id,
                max_size=40,
            )
            if img:
                self._timeline_image_refs.append(img)
                avatar = tk.Label(row, image=img, bg=row_bg)
                avatar.pack(side=tk.LEFT)
            else:
                avatar = tk.Label(
                    row,
                    text="?",
                    font=UI_MONO_FONT,
                    bg=row_bg,
                    fg=Colors.TEXT_MUTED,
                    width=2,
                )
                avatar.pack(side=tk.LEFT)

            if is_extra:
                av_text = "+"
                value_color = Colors.TIMELINE_EXTRA
            elif is_current:
                av_text = "0"
                value_color = (
                    Colors.LOG_DAMAGE if is_enemy else Colors.ACCENT
                )
            else:
                speed = max(1, eng.get_effective_speed(s))
                av_text = str(round(action_value(s.charge, speed)))
                value_color = Colors.TEXT_MUTED
            av_lbl = tk.Label(
                row,
                text=av_text,
                font=UI_MONO_FONT,
                bg=row_bg,
                fg=value_color,
                anchor="e",
            )
            av_lbl.pack(side=tk.RIGHT, padx=(4, 0))
            if callable(select):
                click_widgets = [avatar, av_lbl]
                if extra_mark is not None:
                    click_widgets.append(extra_mark)
                for w in click_widgets:
                    w.bind("<Button-1>", lambda _e, sid=s.unique_id: select(sid))
