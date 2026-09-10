"""Avatar image loading and caching for the desktop panels."""

from __future__ import annotations

import tkinter as tk
from typing import Dict, Optional

from PIL import Image, ImageEnhance, ImageOps, ImageTk

from .constants import AVATAR_BY_TEMPLATE_ID
from .helpers import _runtime_root


class AvatarMixin:
    """Loads spirit portraits from ``assets/spirits`` and marks from ``assets/marks``."""

    _pil_cache: Dict[str, Image.Image]

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

    def _avatar_cache_key(
        self,
        spirit_name: str,
        *,
        mirror: bool,
        template_id: str,
        max_size: int,
    ) -> str:
        basename = AVATAR_BY_TEMPLATE_ID.get(template_id, spirit_name)
        return f"avatar:{basename}:{'m' if mirror else 'n'}:{max_size}"

    def _load_avatar_pil(
        self,
        spirit_name: str,
        *,
        mirror: bool = False,
        template_id: str = "",
        max_size: int = 72,
    ) -> Optional[Image.Image]:
        """RGBA portrait used for tint/brightness filters (same footprint as PhotoImage)."""
        if not hasattr(self, "_pil_cache"):
            self._pil_cache = {}
        cache_key = self._avatar_cache_key(
            spirit_name, mirror=mirror, template_id=template_id, max_size=max_size
        )
        cached = self._pil_cache.get(cache_key)
        if cached is not None:
            return cached
        basename = AVATAR_BY_TEMPLATE_ID.get(template_id, spirit_name)
        img_path = self.asset_dir / f"{basename}.png"
        if not img_path.exists():
            return None
        try:
            source = Image.open(img_path).convert("RGBA")
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
            self._pil_cache[cache_key] = canvas
            return canvas
        except Exception:
            return None

    def _load_avatar(
        self,
        spirit_name: str,
        *,
        mirror: bool = False,
        template_id: str = "",
        max_size: int = 72,
    ) -> Optional[tk.PhotoImage]:
        cache_key = self._avatar_cache_key(
            spirit_name, mirror=mirror, template_id=template_id, max_size=max_size
        )
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
        pil = self._load_avatar_pil(
            spirit_name,
            mirror=mirror,
            template_id=template_id,
            max_size=max_size,
        )
        if pil is None:
            return None
        try:
            img = ImageTk.PhotoImage(pil, master=self)
            self._image_cache[cache_key] = img
            return img
        except Exception:
            return None

    def _avatar_with_overlay_photo(
        self,
        pil: Image.Image,
        overlay: Image.Image,
        *,
        overlay_brightness: float = 1.0,
    ) -> tk.PhotoImage:
        """Portrait at full brightness with a centered overlay (brightness optional)."""
        out = pil.convert("RGBA")
        if abs(overlay_brightness - 1.0) < 1e-3:
            tinted = overlay
        else:
            rgb = overlay.convert("RGB")
            enhanced = ImageEnhance.Brightness(rgb).enhance(overlay_brightness)
            tinted = enhanced.convert("RGBA")
            tinted.putalpha(overlay.getchannel("A"))
        layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
        x = (out.width - tinted.width) // 2
        y = (out.height - tinted.height) // 2
        layer.alpha_composite(tinted, (max(0, x), max(0, y)))
        out = Image.alpha_composite(out, layer)
        return ImageTk.PhotoImage(out, master=self)

    def _load_ui_pil(self, basename: str, *, max_size: int = 96) -> Optional[Image.Image]:
        """Load an RGBA UI icon from ``assets/ui/{basename}.png``."""
        if not hasattr(self, "_pil_cache"):
            self._pil_cache = {}
        cache_key = f"ui-pil:{basename}:{max_size}"
        cached = self._pil_cache.get(cache_key)
        if cached is not None:
            return cached
        ui_dir = getattr(self, "ui_dir", None)
        if ui_dir is None:
            ui_dir = _runtime_root() / "assets" / "ui"
        img_path = ui_dir / f"{basename}.png"
        if not img_path.exists():
            return None
        try:
            source = Image.open(img_path).convert("RGBA")
            source.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            self._pil_cache[cache_key] = source
            return source
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
