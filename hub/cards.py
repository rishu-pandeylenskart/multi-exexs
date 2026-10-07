"""Application card and sidebar navigation item (both canvas-drawn)."""
from __future__ import annotations

import tkinter as tk

from .icons import draw_icon
from .process_manager import Status
from .theme import px
from .timeutil import relative_time
from .widgets import paint_badge, paint_button, round_rect, truncate, wrap_text

STATUS_VIEW = {
    Status.READY: ("Ready", "success"),
    Status.MISSING: ("Not installed", "warning"),
    Status.LAUNCHING: ("Launching\u2026", "info"),
    Status.RUNNING: ("Running", "info"),
    Status.ERROR: ("Error", "error"),
}

CARD_HEIGHT = 200
MARGIN = 4
PAD = 18


class AppCard(tk.Canvas):
    def __init__(self, parent, hub, entry, width):
        self.hub, self.entry, self.theme = hub, entry, hub.theme
        self.W = width
        self.hover = None          # None | "card" | "launch" | "star" | "more"
        self.focused = False
        self.hits: dict[str, tuple] = {}
        super().__init__(parent, width=width, height=px(CARD_HEIGHT), bg=self.theme.c["bg"], highlightthickness=0,
                         bd=0, takefocus=1)
        self.bind("<Motion>", self._motion)
        self.bind("<Enter>", self._motion)
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.bind("<Button-1>", self._click)
        self.bind("<Return>", lambda e: hub.launch(entry))
        self.bind("<space>", lambda e: hub.launch(entry))
        self.bind("<Menu>", lambda e: hub.show_more_menu(entry, self.winfo_rootx() + px(40), self.winfo_rooty() + px(40)))
        self.bind("<FocusIn>", lambda e: self._set_focus(True))
        self.bind("<FocusOut>", lambda e: self._set_focus(False))
        self.render()

    # ---- interaction ---------------------------------------------------
    def set_width(self, width):
        if width != self.W:
            self.W = width
            self.config(width=width)
            self.render()

    def _region(self, x, y):
        for name in ("launch", "star", "more"):
            x1, y1, x2, y2 = self.hits.get(name, (0, 0, -1, -1))
            if x1 <= x <= x2 and y1 <= y <= y2:
                return name
        return "card"

    def _motion(self, e):
        self._set_hover(self._region(e.x, e.y))

    def _set_hover(self, value):
        if value != self.hover:
            self.hover = value
            self.config(cursor="hand2" if value in ("launch", "star", "more") else "arrow")
            self.render()

    def _set_focus(self, value):
        self.focused = value
        self.render()

    def _click(self, e):
        self.focus_set()
        region = self._region(e.x, e.y)
        if region == "launch":
            self.hub.launch(self.entry, from_card=True)
        elif region == "star":
            self.hub.toggle_favorite(self.entry)
        elif region == "more":
            self.hub.show_more_menu(self.entry, e.x_root, e.y_root)

    # ---- drawing ---------------------------------------------------------
    def render(self):
        hub, entry, theme = self.hub, self.entry, self.theme
        c, W, H, m, pad = theme.c, self.W, px(CARD_HEIGHT), px(MARGIN), px(PAD)
        status = hub.pm.status(entry)
        view, tone = STATUS_VIEW[status]
        lifted = self.hover is not None
        self.delete("all")
        self.hits = {}
        bottom = H - m - px(3)
        # shadow + surface
        if lifted:
            round_rect(self, m + 1, m + 3, W - m - 1, bottom + 3, px(14), fill=c["shadow2"], outline=c["shadow2"])
        else:
            round_rect(self, m, m + 1, W - m, bottom + 1, px(14), fill=c["shadow1"], outline=c["shadow1"])
        border = c["accent"] if self.focused else (c["border_strong"] if lifted else c["border"])
        round_rect(self, m, m, W - m, bottom, px(14), fill=c["surface"], outline=border, width=2 if self.focused else 1)

        left, right = m + pad, W - m - pad
        top = m + pad
        # icon tile
        tile = px(44)
        tile_bg = c["accent_soft"] if status != Status.MISSING else c["neutral_soft"]
        tile_fg = c["accent_text"] if status != Status.MISSING else c["text_faint"]
        round_rect(self, left, top, left + tile, top + tile, px(11), fill=tile_bg, outline=tile_bg)
        draw_icon(self, entry.icon, left + px(11), top + px(11), px(22), tile_fg)

        # star + more
        btn = px(28)
        more_x1 = right - btn
        star_x1 = more_x1 - btn - px(2)
        fav = hub.prefs.is_favorite(entry.id)
        for name, x1, icon in (("star", star_x1, "star_filled" if fav else "star"), ("more", more_x1, "dots")):
            self.hits[name] = (x1, top - px(2), x1 + btn, top - px(2) + btn)
            if self.hover == name:
                round_rect(self, x1, top - px(2), x1 + btn, top - px(2) + btn, px(8), fill=c["surface_alt"], outline=c["surface_alt"])
            color = c["warning"] if fav and name == "star" else (c["text"] if self.hover == name else c["text_faint"])
            draw_icon(self, icon, x1 + px(6), top - px(2) + px(6), px(16), color)

        # name + category
        text_x = left + tile + px(12)
        name_w = star_x1 - px(6) - text_x
        self.create_text(text_x, top + px(1), text=truncate(entry.name, theme.font("card_title"), name_w), anchor="nw",
                         font=theme.font("card_title"), fill=c["text"])
        self.create_text(text_x, top + px(24), text=truncate(entry.category, theme.font("small"), name_w), anchor="nw",
                         font=theme.font("small"), fill=c["text_faint"])

        # description
        desc = entry.description or entry.filename
        font = theme.font("small") if entry.description else theme.font("mono")
        lines = wrap_text(desc, font, right - left, 2)
        y = top + tile + px(12)
        for line in lines:
            self.create_text(left, y, text=line, anchor="nw", font=font, fill=c["text_muted"])
            y += px(18)

        # last used / error line
        info_y = top + tile + px(12) + px(18) * 2 + px(6)
        err = hub.pm.error_for(entry) if status == Status.ERROR else None
        if err:
            msg, color = truncate(err.friendly, theme.font("caption"), right - left), c["error"]
        else:
            last = hub.prefs.last_used(entry.id)
            msg = f"Last used: {relative_time(last)}" if last else "Not launched yet"
            color = c["text_faint"]
        self.create_text(left, info_y, text=msg, anchor="nw", font=theme.font("caption"), fill=color)

        # bottom row: badge + launch
        row_h = px(34)
        row_y2 = bottom - px(14)
        row_y1 = row_y2 - row_h
        paint_badge(self, theme, left, row_y1 + (row_h - px(22)) / 2, view, tone)
        label, kind, icon, enabled = {
            Status.MISSING: ("Details", "secondary", None, True),
            Status.LAUNCHING: ("Launching\u2026", "secondary", None, False),
            Status.ERROR: ("Try again", "secondary", "refresh", True),
        }.get(status, ("Launch", "primary", "arrow_right", True))
        bw = max(px(104), theme.font("body_bold").measure(label) + px(52))
        rect = (right - bw, row_y1, right, row_y2)
        self.hits["launch"] = rect
        state = "normal" if enabled else "disabled"
        if enabled and self.hover == "launch":
            state = "hover"
        paint_button(self, theme, rect, label, kind, state, icon, icon_right=True,
                     focused=False)


class NavItem(tk.Canvas):
    def __init__(self, parent, hub, key, label, icon, command):
        self.hub, self.key, self.label, self.icon, self.command = hub, key, label, icon, command
        self.hover = self.has_focus = False
        c = hub.theme.c
        super().__init__(parent, height=px(40), bg=c["surface"], highlightthickness=0, bd=0, cursor="hand2",
                         takefocus=1)
        self.bind("<Configure>", lambda e: self.render())
        self.bind("<Enter>", lambda e: self._set("hover", True))
        self.bind("<Leave>", lambda e: self._set("hover", False))
        self.bind("<FocusIn>", lambda e: self._set("has_focus", True))
        self.bind("<FocusOut>", lambda e: self._set("has_focus", False))
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Return>", lambda e: self.command())
        self.bind("<space>", lambda e: self.command())
        if hub.sidebar_collapsed:
            from .widgets import Tooltip
            Tooltip(self, hub.theme, label)

    def _set(self, name, value):
        setattr(self, name, value)
        self.render()

    def render(self):
        hub = self.hub
        c = hub.theme.c
        w, h = self.winfo_width(), px(40)
        if w < 10:
            return
        self.delete("all")
        selected = hub.page == self.key and self.key is not None
        bg = c["accent_soft"] if selected else (c["surface_alt"] if self.hover else None)
        if bg:
            round_rect(self, px(10), px(2), w - px(10), h - px(2), px(9), fill=bg, outline=bg)
        if selected:
            round_rect(self, px(2), px(11), px(5), h - px(11), px(2), fill=c["accent"], outline=c["accent"])
        if self.has_focus:
            round_rect(self, px(10), px(2), w - px(10), h - px(2), px(9), fill="", outline=c["accent"], width=2)
        color = c["accent_text"] if selected else (c["text"] if self.hover else c["text_muted"])
        isz = px(20)
        draw_icon(self, self.icon, (px(68) - isz) / 2, (h - isz) / 2, isz, color)
        if w > px(120):
            font = hub.theme.font("body_bold" if selected else "body")
            self.create_text(px(62), h / 2, text=self.label, anchor="w", font=font, fill=color)
