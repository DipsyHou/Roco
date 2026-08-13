"""Battle log panel with incremental append."""

from __future__ import annotations

import tkinter as tk

from .theme import log_tag_for_entry, log_tag_for_message


class LogPanelMixin:
    """Appends only new entries, so long battles stay responsive."""

    def _append_log_line(self, index: int, message: str, log_type=None) -> None:
        line = f"{index:02d}. {message}\n"
        tag = log_tag_for_entry(log_type) if log_type is not None else log_tag_for_message(message)
        self.log_text.insert(tk.END, line, tag)

    def _render_logs(self) -> None:
        eng = self.eng
        assert eng
        logs = eng.state.battle_log
        # New battle or reset: rebuild from scratch.
        if self._rendered_log_count > len(logs):
            self._rendered_log_count = 0
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", tk.END)
            self.log_text.configure(state="disabled")

        if self._rendered_log_count == 0 and logs:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", tk.END)
            for i, entry in enumerate(logs, start=1):
                self._append_log_line(i, entry.message, entry.type)
            self.log_text.configure(state="disabled")
            self._rendered_log_count = len(logs)
            self.log_text.see(tk.END)
            return

        if self._rendered_log_count < len(logs):
            new_logs = logs[self._rendered_log_count :]
            self.log_text.configure(state="normal")
            for i, entry in enumerate(new_logs, start=self._rendered_log_count + 1):
                self._append_log_line(i, entry.message, entry.type)
            self.log_text.configure(state="disabled")
            self._rendered_log_count = len(logs)

        self.log_text.see(tk.END)
