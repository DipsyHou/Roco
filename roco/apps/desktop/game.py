"""Desktop battle app entrypoint and compatibility exports."""

from __future__ import annotations

from .app import DesktopGameApp, main
from .constants import UI_FONT
from .helpers import _skill_available, _skill_cost_label
from .windows import IndexChoiceWindow, MultiPickWindow, TargetWindow, TeamSelectWindow

__all__ = [
    "DesktopGameApp",
    "IndexChoiceWindow",
    "MultiPickWindow",
    "TargetWindow",
    "TeamSelectWindow",
    "UI_FONT",
    "_skill_available",
    "_skill_cost_label",
    "main",
]

if __name__ == "__main__":
    main()
