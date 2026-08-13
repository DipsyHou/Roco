"""Battlefield: two vertical columns of large spirit cards."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional, Tuple

from roco.core.battle.types import BattleSpirit
from roco.core.spirits import get_spirit_logic

from .constants import UI_FONT, UI_FONT_BADGE, UI_FONT_TITLE
from .theme import Colors, draw_vertical_spirit_hp_bar

# Larger portraits / bars for the main battlefield layout.
AVATAR_SIZE = 150
MARK_SIZE = 24
VERTICAL_HP_WIDTH = 14


class PetStripMixin:
    """Builds the battlefield once, then updates widgets in place on each refresh."""

    def _render_team_energy_bar(self, parent: ttk.Frame) -> Dict[str, object]:
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(row, text="能量", font=UI_FONT, width=4).pack(side=tk.LEFT)
        pb = ttk.Progressbar(
            row,
            orient="horizontal",
            mode="determinate",
            length=160,
            style="Energy.Horizontal.TProgressbar",
        )
        pb.pack(side=tk.LEFT, padx=(0, 6), fill=tk.X, expand=True)
        value_label = ttk.Label(row, text="", font=UI_FONT)
        value_label.pack(side=tk.LEFT)
        return {"pb": pb, "label": value_label}

    def _update_team_energy_bar(self, widgets: Dict[str, object], current: int, maximum: int) -> None:
        pb = widgets["pb"]
        assert isinstance(pb, ttk.Progressbar)
        cap = max(1, maximum)
        pb["maximum"] = cap
        pb["value"] = max(0, min(cap, current))
        label = widgets["label"]
        assert isinstance(label, ttk.Label)
        label.configure(text=f"{current}/{maximum}")

    def _pet_card_bg(self, spirit_id: str) -> str:
        eng = self.eng
        if eng and spirit_id == eng.state.active_actor_id:
            return Colors.TIMELINE_ACTIVE
        return Colors.BG

    def _apply_pet_card_bg(self, widgets: Dict[str, object], spirit_id: str) -> None:
        bg = self._pet_card_bg(spirit_id)
        for key in (
            "frame",
            "combat_row",
            "hp_side",
            "avatar_wrap",
            "avatar_label",
            "hp_canvas",
            "hp_label",
        ):
            widget = widgets.get(key)
            if isinstance(widget, (tk.Frame, tk.Label, tk.Canvas)) and widget.winfo_exists():
                widget.configure(bg=bg)

    def _avatar_badge_info(self, spirit: BattleSpirit) -> Optional[Tuple[str, str]]:
        logic = get_spirit_logic(spirit.template_id)
        if not logic:
            return None
        info = logic.describe_avatar_badge(spirit)
        if not info:
            return None
        mark_key, caption = info
        return str(mark_key), str(caption)

    def _mount_avatar_badge(
        self,
        avatar_wrap: tk.Frame,
        spirit: BattleSpirit,
    ) -> Dict[str, object]:
        """Corner mark + caption on the avatar (bottom-left). Empty dict if none."""
        info = self._avatar_badge_info(spirit)
        if not info:
            return {}
        mark_key, caption = info
        mark_img = self._load_mark(mark_key, max_size=MARK_SIZE)
        badge = tk.Frame(avatar_wrap, bg=Colors.PANEL_ALT, padx=1, pady=0)
        badge.place(relx=0.0, rely=1.0, anchor="sw", x=1, y=-1)
        mark_label = None
        if mark_img is not None:
            mark_label = tk.Label(
                badge,
                image=mark_img,
                bg=Colors.PANEL_ALT,
                borderwidth=0,
            )
            mark_label.pack(side=tk.LEFT)
            mark_label.image = mark_img  # keep ref
        caption_label = tk.Label(
            badge,
            text=caption,
            bg=Colors.PANEL_ALT,
            fg=Colors.TEXT,
            font=UI_FONT_BADGE,
            borderwidth=0,
            padx=2,
        )
        caption_label.pack(side=tk.LEFT)
        return {
            "badge": badge,
            "mark_label": mark_label,
            "caption_label": caption_label,
            "mark_key": mark_key,
        }

    def _update_avatar_badge(self, widgets: Dict[str, object], spirit: BattleSpirit) -> None:
        caption_label = widgets.get("badge_caption")
        avatar_wrap = widgets.get("avatar_wrap")
        if not isinstance(avatar_wrap, tk.Frame) or not avatar_wrap.winfo_exists():
            return
        info = self._avatar_badge_info(spirit)
        if info is None:
            badge = widgets.get("badge")
            if isinstance(badge, tk.Frame) and badge.winfo_exists():
                badge.place_forget()
            return
        _mark_key, caption = info
        if isinstance(caption_label, tk.Label) and caption_label.winfo_exists():
            caption_label.configure(text=caption)
            badge = widgets.get("badge")
            if isinstance(badge, tk.Frame) and badge.winfo_exists():
                badge.place(relx=0.0, rely=1.0, anchor="sw", x=1, y=-1)
            return
        badge_widgets = self._mount_avatar_badge(avatar_wrap, spirit)
        widgets["badge"] = badge_widgets.get("badge")
        widgets["badge_caption"] = badge_widgets.get("caption_label")

    def _bind_spirit_click(self, widget: tk.Misc, spirit_id: str) -> None:
        widget.bind("<Button-1>", lambda _e, sid=spirit_id: self._select_spirit(sid))

    def _update_pet_selection_highlights(self) -> None:
        for spirit_id, widgets in self._pet_card_widgets.items():
            self._apply_pet_card_bg(widgets, spirit_id)

    def _reset_pet_strip(self) -> None:
        self._pet_card_widgets.clear()
        self._team_strip_widgets.clear()
        for child in self.pet_strip.winfo_children():
            child.destroy()

    def _pet_strip_ready(self) -> bool:
        eng = self.eng
        if not eng or not self._pet_card_widgets:
            return False
        expected = {
            s.unique_id
            for pid in (self.p1, self.p2)
            for s in eng.state.players[pid].spirits
        }
        return expected == set(self._pet_card_widgets.keys())

    def _sync_pet_strip(self) -> None:
        if self._pet_strip_ready():
            self._update_pet_strip()
        else:
            self._build_pet_strip()

    def _build_pet_strip(self) -> None:
        eng = self.eng
        assert eng
        self._reset_pet_strip()
        ally_id = self._ally_player_id()
        titles = ((ally_id, "我方精灵"), (self._enemy_player_id(), "敌方精灵"))
        for pid, title in titles:
            pd = eng.state.players[pid]
            mirror_avatars = pid == ally_id
            box = tk.Frame(self.pet_strip, bg=Colors.BG, padx=12)
            box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tk.Label(
                box,
                text=title,
                bg=Colors.BG,
                fg=Colors.TEXT,
                font=UI_FONT_TITLE,
                anchor="w",
            ).pack(fill=tk.X, pady=(0, 6))
            energy_widgets = self._render_team_energy_bar(box)
            self._team_strip_widgets[pid] = energy_widgets
            self._update_team_energy_bar(energy_widgets, pd.team_energy, pd.max_team_energy)
            column = self._make_scroll_column(box)
            for s in sorted(pd.spirits, key=lambda x: x.slot):
                self._build_spirit_card(column, s, mirror_avatars=mirror_avatars)

    def _make_scroll_column(self, parent: tk.Frame) -> tk.Frame:
        """Vertical scroll area so five large cards still fit short windows."""
        outer = tk.Frame(parent, bg=Colors.BG)
        outer.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(outer, bg=Colors.BG, highlightthickness=0, borderwidth=0)
        column = tk.Frame(canvas, bg=Colors.BG)
        window_id = canvas.create_window((0, 0), window=column, anchor="nw")

        def _sync_scroll(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(window_id, width=canvas.winfo_width())

        column.bind("<Configure>", _sync_scroll)
        canvas.bind("<Configure>", _sync_scroll)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_mousewheel(event: tk.Event) -> None:
            delta = int(-event.delta / 120) if event.delta else 0
            if delta:
                canvas.yview_scroll(delta, "units")

        # Cards bind this too so the wheel works while hovering portraits.
        column._on_mousewheel = _on_mousewheel  # type: ignore[attr-defined]
        for w in (canvas, column, outer):
            w.bind("<MouseWheel>", _on_mousewheel)
        return column

    def _build_spirit_card(
        self,
        parent: tk.Frame,
        spirit: BattleSpirit,
        *,
        mirror_avatars: bool,
    ) -> None:
        eng = self.eng
        assert eng
        card_bg = self._pet_card_bg(spirit.unique_id)
        col = tk.Frame(
            parent,
            bg=card_bg,
            highlightthickness=0,
            padx=8,
            pady=6,
        )
        col.pack(side=tk.TOP, fill=tk.X, pady=5)
        self._bind_spirit_click(col, spirit.unique_id)

        img = self._load_avatar(
            spirit.name,
            mirror=mirror_avatars,
            template_id=spirit.template_id,
            max_size=AVATAR_SIZE,
        )
        has_image = img is not None
        portrait_height = img.height() if img is not None else AVATAR_SIZE
        bar_height = max(24, portrait_height // 2)

        combat_row = tk.Frame(col, bg=card_bg)
        combat_row.pack()
        avatar_wrap = tk.Frame(combat_row, bg=card_bg)
        if has_image:
            avatar_label = tk.Label(
                avatar_wrap,
                image=img,
                bg=card_bg,
                borderwidth=0,
            )
            avatar_label.pack()
            avatar_label.image = img
        else:
            avatar_label = tk.Label(
                avatar_wrap,
                text="[无图]",
                bg=card_bg,
                fg=Colors.TEXT_MUTED,
                font=UI_FONT_TITLE,
                borderwidth=0,
            )
            avatar_label.pack()

        badge_widgets = self._mount_avatar_badge(avatar_wrap, spirit)
        hp_side = tk.Frame(combat_row, bg=card_bg)
        hp_canvas = tk.Canvas(
            hp_side,
            width=VERTICAL_HP_WIDTH,
            height=bar_height,
            bg=card_bg,
            highlightthickness=0,
            borderwidth=0,
        )
        hp_canvas.pack()
        draw_vertical_spirit_hp_bar(
            hp_canvas,
            spirit,
            width=VERTICAL_HP_WIDTH,
            height=bar_height,
        )
        hp_label = tk.Label(
            hp_side,
            text=str(spirit.current_hp),
            bg=card_bg,
            fg=Colors.TEXT_MUTED,
            font=UI_FONT,
            borderwidth=0,
        )
        hp_label.pack(pady=(3, 0))
        if spirit.owner_id == self._ally_player_id():
            hp_side.pack(side=tk.LEFT, padx=(0, 10))
            avatar_wrap.pack(side=tk.LEFT)
        else:
            avatar_wrap.pack(side=tk.LEFT)
            hp_side.pack(side=tk.LEFT, padx=(10, 0))

        wheel = getattr(parent, "_on_mousewheel", None)
        for w in (
            col,
            combat_row,
            hp_side,
            avatar_wrap,
            avatar_label,
            hp_canvas,
            hp_label,
            badge_widgets.get("badge"),
            badge_widgets.get("mark_label"),
            badge_widgets.get("caption_label"),
        ):
            if isinstance(w, (tk.Frame, tk.Label, tk.Canvas)):
                self._bind_spirit_click(w, spirit.unique_id)
                if callable(wheel):
                    w.bind("<MouseWheel>", wheel)

        self._pet_card_widgets[spirit.unique_id] = {
            "frame": col,
            "combat_row": combat_row,
            "hp_side": hp_side,
            "avatar_wrap": avatar_wrap,
            "avatar_label": avatar_label,
            "badge": badge_widgets.get("badge"),
            "badge_caption": badge_widgets.get("caption_label"),
            "hp_canvas": hp_canvas,
            "hp_label": hp_label,
            "hp_height": bar_height,
            "has_image": has_image,
        }

    def _update_pet_strip(self) -> None:
        eng = self.eng
        assert eng
        for pid in (self.p1, self.p2):
            pd = eng.state.players[pid]
            team_widgets = self._team_strip_widgets.get(pid)
            if team_widgets:
                self._update_team_energy_bar(team_widgets, pd.team_energy, pd.max_team_energy)
        for pid in (self.p1, self.p2):
            for s in eng.state.players[pid].spirits:
                widgets = self._pet_card_widgets.get(s.unique_id)
                if not widgets:
                    continue
                frame = widgets["frame"]
                hp_canvas = widgets["hp_canvas"]
                hp_label = widgets["hp_label"]
                if not (
                    isinstance(frame, tk.Frame)
                    and isinstance(hp_canvas, tk.Canvas)
                    and isinstance(hp_label, tk.Label)
                ):
                    continue
                self._apply_pet_card_bg(widgets, s.unique_id)
                self._update_avatar_badge(widgets, s)
                hp_height = int(widgets.get("hp_height", max(24, AVATAR_SIZE // 2)))
                draw_vertical_spirit_hp_bar(
                    hp_canvas,
                    s,
                    width=VERTICAL_HP_WIDTH,
                    height=hp_height,
                )
                hp_label.configure(text=str(s.current_hp))

    def _select_spirit(self, spirit_id: str) -> None:
        self.selected_spirit_id = spirit_id
        self._update_pet_selection_highlights()
        show = getattr(self, "_show_spirit_detail", None)
        if callable(show):
            show()
        else:
            self._render_status_panel()
