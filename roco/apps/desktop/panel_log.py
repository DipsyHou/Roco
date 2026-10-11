"""Battle log panel with incremental append."""

from __future__ import annotations

import tkinter as tk

from .theme import log_tag_for_entry, log_tag_for_message


class LogPanelMixin:
    """Reveal battle logs one presentation event at a time."""

    def _append_log_line(self, index: int, message: str, log_type=None) -> None:
        line = f"{index:02d}. {message}\n"
        tag = log_tag_for_entry(log_type) if log_type is not None else log_tag_for_message(message)
        self.log_text.insert(tk.END, line, tag)

    def _render_logs(self) -> None:
        eng = self.eng
        assert eng
        logs = eng.state.battle_log
        if self._rendered_log_count > len(logs):
            self._rendered_log_count = 0
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", tk.END)
            self.log_text.configure(state="disabled")
        self.log_text.see(tk.END)

    def _reveal_log(self, log_index: int) -> None:
        eng = self.eng
        if not eng:
            return
        logs = eng.state.battle_log
        end = min(len(logs), max(self._rendered_log_count, log_index + 1))
        if end <= self._rendered_log_count:
            return
        self.log_text.configure(state="normal")
        for index in range(self._rendered_log_count, end):
            entry = logs[index]
            self._append_log_line(index + 1, entry.message, entry.type)
        self.log_text.configure(state="disabled")
        self._rendered_log_count = end
        self.log_text.see(tk.END)
