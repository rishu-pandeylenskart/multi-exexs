"""Design tokens: colours, fonts and DPI scaling shared by every screen."""
from __future__ import annotations

import tkinter.font as tkfont

LIGHT = {
    "bg": "#F4F6FA", "surface": "#FFFFFF", "surface_alt": "#EEF1F7", "surface_press": "#E1E6F0",
    "border": "#E1E6EF", "border_strong": "#C9D1E0",
    "text": "#111827", "text_muted": "#4B5568", "text_faint": "#667085",
    "accent": "#3B4CCA", "accent_hover": "#2F3DAE", "accent_press": "#27338F",
    "accent_text": "#3B4CCA", "accent_soft": "#E8EBFB", "accent_soft_hover": "#D9DEF8", "on_accent": "#FFFFFF",
    "success": "#0B6B42", "success_soft": "#DDF3E8",
    "warning": "#8A5700", "warning_soft": "#FCEFD2",
    "error": "#B42318", "error_soft": "#FDE7E4",
    "info": "#1A56C4", "info_soft": "#E1ECFD",
    "neutral": "#4B5568", "neutral_soft": "#E9ECF2",
    "shadow1": "#E8ECF4", "shadow2": "#D3DAE8",
    "toast_bg": "#18202F", "toast_text": "#FFFFFF",
}
DARK = {
    "bg": "#0E131D", "surface": "#171D2B", "surface_alt": "#1F2738", "surface_press": "#2A3449",
    "border": "#2A3347", "border_strong": "#3C4863",
    "text": "#EDF0F7", "text_muted": "#A9B2C6", "text_faint": "#8E98AF",
    "accent": "#5967E8", "accent_hover": "#6B78EE", "accent_press": "#4A57D1",
    "accent_text": "#A9B3FF", "accent_soft": "#252E5C", "accent_soft_hover": "#2F3A72", "on_accent": "#FFFFFF",
    "success": "#4ADE9A", "success_soft": "#12332A",
    "warning": "#F5B94A", "warning_soft": "#3A2D12",
    "error": "#FF8A80", "error_soft": "#3F1B1A",
    "info": "#7FB0FF", "info_soft": "#16294A",
    "neutral": "#A9B2C6", "neutral_soft": "#252D3F",
    "shadow1": "#121826", "shadow2": "#080B12",
    "toast_bg": "#EDF0F7", "toast_text": "#111827",
}

_scale = 1.0


def set_scale(value: float) -> None:
    global _scale
    _scale = max(1.0, min(3.0, float(value)))


def px(n: float) -> int:
    """Scale a design pixel value for the current display DPI."""
    return int(round(n * _scale))


class Theme:
    def __init__(self, name: str, root):
        self.name = name
        self.c = dict(DARK if name == "dark" else LIGHT)
        families = set(tkfont.families(root))
        self.family = next((f for f in ("Segoe UI Variable Text", "Segoe UI", "Helvetica Neue", "Helvetica", "DejaVu Sans") if f in families), "TkDefaultFont")
        self.mono = "Consolas" if "Consolas" in families else "Courier"
        fam = self.family
        self.fonts = {
            "body": tkfont.Font(root=root, family=fam, size=10),
            "body_bold": tkfont.Font(root=root, family=fam, size=10, weight="bold"),
            "small": tkfont.Font(root=root, family=fam, size=9),
            "small_bold": tkfont.Font(root=root, family=fam, size=9, weight="bold"),
            "caption": tkfont.Font(root=root, family=fam, size=8),
            "card_title": tkfont.Font(root=root, family=fam, size=11, weight="bold"),
            "section": tkfont.Font(root=root, family=fam, size=12, weight="bold"),
            "title": tkfont.Font(root=root, family=fam, size=20, weight="bold"),
            "brand": tkfont.Font(root=root, family=fam, size=12, weight="bold"),
            "mono": tkfont.Font(root=root, family=self.mono, size=9),
        }

    def font(self, key: str):
        return self.fonts[key]
