"""Avatar image loading and caching for the desktop panels."""

from __future__ import annotations

import tkinter as tk
from typing import Optional

from PIL import Image, ImageOps, ImageTk

from .constants import AVATAR_BY_TEMPLATE_ID
from .helpers import _runtime_root


class AvatarMixin:
    """Loads spirit portraits from ``assets/spirits`` and marks from ``assets/marks``."""

    @staticmethod
    def _mirror_photo(img: tk.PhotoImage) -> tk.PhotoImage:
        width = img.width()
        height = img.height()
        flipped = tk.PhotoImage(width=width, height=height)
        for x in range(width):
            flipped.tk.call(
                str(flipped),
                "copy",
                str(img),
                "-from",
                x,
                0,
                x + 1,
                height,
                "-to",
                width - 1 - x,
                0,
            )
        return flipped

    def _load_avatar(
        self,
        spirit_name: str,
        *,
        mirror: bool = False,
        template_id: str = "",
        max_size: int = 72,
    ) -> Optional[tk.PhotoImage]:
        basename = AVATAR_BY_TEMPLATE_ID.get(template_id, spirit_name)
        cache_key = f"avatar:{basename}:{'m' if mirror else 'n'}:{max_size}"
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        img_path = self.asset_dir / f"{basename}.png"
        if not img_path.exists():
            return None
        try:
            source = Image.open(img_path).convert("RGBA")
            # Source portraits have very different transparent margins. Crop
            # by alpha first, then fit the visible sprite into one square
            # canvas so every spirit uses the same visual scale and footprint.
            bbox = source.getchannel("A").getbbox()
            if bbox:
                source = source.crop(bbox)
            if mirror:
                source = ImageOps.mirror(source)
            source.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (max_size, max_size), (0, 0, 0, 0))
            x = (max_size - source.width) // 2
            y = max_size - source.height
            canvas.alpha_composite(source, (x, y))
            img = ImageTk.PhotoImage(canvas, master=self)
            self._image_cache[cache_key] = img
            return img
        except Exception:
            return None

    def _load_mark(self, basename: str, *, max_size: int = 22) -> Optional[tk.PhotoImage]:
        """Load a corner-mark icon from ``assets/marks/{basename}.png``."""
        cache_key = f"mark:{basename}:{max_size}"
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        marks_dir = getattr(self, "marks_dir", None)
        if marks_dir is None:
            marks_dir = _runtime_root() / "assets" / "marks"
        img_path = marks_dir / f"{basename}.png"
        if not img_path.exists():
            # Fall back to MARK_BY_TEMPLATE_ID reverse is unnecessary; try as-is.
            return None
        try:
            img = tk.PhotoImage(file=str(img_path))
            # Prefer zoom for tiny sprites; subsample only when larger than target.
            if img.width() > max_size or img.height() > max_size:
                img = img.subsample(
                    max(1, img.width() // max_size),
                    max(1, img.height() // max_size),
                )
            self._image_cache[cache_key] = img
            return img
        except Exception:
            return None
