"""Reusable, theme-aware widgets drawn on tk.Canvas (rounded, flat, modern)."""
from __future__ import annotations

import tkinter as tk

from .icons import draw_icon
from .theme import px


# ---------------------------------------------------------------- drawing helpers
def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y1 + r,
           x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


def truncate(text: str, font, max_width: int) -> str:
    if font.measure(text) <= max_width:
        return text
    while text and font.measure(text + "\u2026") > max_width:
        text = text[:-1]
    return text.rstrip() + "\u2026"


def wrap_text(text: str, font, max_width: int, max_lines: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if font.measure(trial) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
        if len(lines) == max_lines:
            break
    if len(lines) < max_lines and current:
        lines.append(current)
    consumed = " ".join(lines).split()
    if len(consumed) < len(words) and lines:
        lines[-1] = truncate(lines[-1] + " \u2026", font, max_width)
    return lines[:max_lines]


_BUTTON_COLORS = {
    # kind: (bg, bg_hover, bg_press, fg, outline)
    "primary": ("accent", "accent_hover", "accent_press", "on_accent", None),
    "secondary": ("surface", "surface_alt", "surface_press", "text", "border_strong"),
    "soft": ("accent_soft", "accent_soft_hover", "accent_soft_hover", "accent_text", None),
    "ghost": (None, "surface_alt", "surface_press", "text_muted", None),
}


def paint_button(canvas, theme, rect, text, kind="primary", state="normal", icon=None,
                 icon_right=False, focused=False, tags=(), font_key="body_bold", parent_bg=None):
    """Draw a rounded button inside ``rect`` = (x1, y1, x2, y2)."""
    c = theme.c
    x1, y1, x2, y2 = rect
    bg_k, hover_k, press_k, fg_k, outline_k = _BUTTON_COLORS[kind]
    disabled = state == "disabled"
    if disabled:
        bg, fg, outline = c["surface_alt"], c["text_faint"], None
    else:
        key = {"hover": hover_k, "pressed": press_k}.get(state, bg_k)
        bg = c[key] if key else (parent_bg or c["bg"])
        fg = c[fg_k]
        outline = c[outline_k] if outline_k else None
        if kind == "ghost" and state in ("hover", "pressed"):
            fg = c["text"]
    round_rect(canvas, x1, y1, x2, y2, px(8), fill=bg, outline=outline or bg, width=1, tags=tags)
    font = theme.font(font_key)
    isz = px(16)
    gap = px(6)
    tw = font.measure(text) if text else 0
    total = tw + (isz + (gap if text else 0) if icon else 0)
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    x = cx - total / 2
    if icon and not icon_right:
        draw_icon(canvas, icon, x, cy - isz / 2, isz, fg, tags=tags)
        x += isz + (gap if text else 0)
    if text:
        canvas.create_text(x, cy, text=text, anchor="w", fill=fg, font=font, tags=tags)
        x += tw
    if icon and icon_right:
        draw_icon(canvas, icon, x + gap, cy - isz / 2, isz, fg, tags=tags)
    if focused and not disabled:
        round_rect(canvas, x1 - 1, y1 - 1, x2 + 1, y2 + 1, px(9), fill="", outline=c["accent"], width=2, tags=tags)


def paint_badge(canvas, theme, x, y, text, tone="neutral", tags=()):
    """Status pill: coloured dot + text (never colour alone). Returns its width."""
    c = theme.c
    font = theme.font("small_bold")
    h = px(22)
    w = font.measure(text) + px(30)
    round_rect(canvas, x, y, x + w, y + h, h / 2, fill=c[f"{tone}_soft"], outline=c[f"{tone}_soft"], tags=tags)
    r = px(3)
    canvas.create_oval(x + px(10) - r, y + h / 2 - r, x + px(10) + r, y + h / 2 + r, fill=c[tone], outline=c[tone], tags=tags)
    canvas.create_text(x + px(19), y + h / 2, text=text, anchor="w", font=font, fill=c[tone], tags=tags)
    return w


# ---------------------------------------------------------------- buttons
class CanvasButton(tk.Canvas):
    def __init__(self, parent, theme, text="", command=None, kind="primary", icon=None, icon_right=False,
                 height=36, min_width=0, bg=None, tooltip=None, font_key="body_bold"):
        self.theme, self.text, self.command, self.kind = theme, text, command, kind
        self.icon, self.icon_right, self.font_key = icon, icon_right, font_key
        self.state, self._hover, self._focus = "normal", False, False
        self._bg = bg or theme.c["bg"]
        font = theme.font(font_key)
        content = font.measure(text) if text else 0
        if icon:
            content += px(16) + (px(6) if text else 0)
        width = max(px(min_width), content + px(28 if text else 20))
        super().__init__(parent, width=width, height=px(height), bg=self._bg, highlightthickness=0, bd=0,
                         cursor="hand2", takefocus=1)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Return>", lambda e: self._invoke())
        self.bind("<space>", lambda e: self._invoke())
        self.bind("<FocusIn>", lambda e: self._set_focus(True))
        self.bind("<FocusOut>", lambda e: self._set_focus(False))
        if tooltip:
            Tooltip(self, theme, tooltip)
        self._draw()

    def configure_button(self, text=None, state=None, kind=None):
        if text is not None:
            self.text = text
        if kind is not None:
            self.kind = kind
        if state is not None:
            self.state = state
            self.config(cursor="arrow" if state == "disabled" else "hand2")
        self._draw()

    def _set_hover(self, value):
        self._hover = value
        if self.state == "normal" or self.state == "hover":
            self._draw()

    def _set_focus(self, value):
        self._focus = value
        self._draw()

    def _press(self, _e):
        if self.state != "disabled":
            self._pressed = True
            self._draw(pressed=True)

    def _release(self, e):
        was = getattr(self, "_pressed", False)
        self._pressed = False
        self._draw()
        if was and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self._invoke()

    def _invoke(self):
        if self.state != "disabled" and self.command:
            self.command()

    def _draw(self, pressed=False):
        self.delete("all")
        state = "disabled" if self.state == "disabled" else ("pressed" if pressed else ("hover" if self._hover else "normal"))
        w, h = int(self["width"]), int(self["height"])
        paint_button(self, self.theme, (1, 1, w - 1, h - 1), self.text, self.kind, state, self.icon,
                     self.icon_right, self._focus, font_key=self.font_key, parent_bg=self._bg)


class Toggle(tk.Canvas):
    """On/off switch with keyboard support."""

    def __init__(self, parent, theme, value=False, command=None, bg=None):
        self.theme, self.value, self.command = theme, bool(value), command
        self._focus = False
        super().__init__(parent, width=px(44), height=px(24), bg=bg or theme.c["surface"], highlightthickness=0,
                         bd=0, cursor="hand2", takefocus=1)
        self.bind("<Button-1>", lambda e: self.flip())
        self.bind("<Return>", lambda e: self.flip())
        self.bind("<space>", lambda e: self.flip())
        self.bind("<FocusIn>", lambda e: self._f(True))
        self.bind("<FocusOut>", lambda e: self._f(False))
        self._draw()

    def _f(self, v):
        self._focus = v
        self._draw()

    def flip(self):
        self.value = not self.value
        self._draw()
        if self.command:
            self.command(self.value)

    def _draw(self):
        c = self.theme.c
        self.delete("all")
        w, h = px(44), px(24)
        round_rect(self, 2, 2, w - 2, h - 2, (h - 4) / 2, fill=c["accent"] if self.value else c["border_strong"],
                   outline=c["accent"] if self.value else c["border_strong"])
        r = (h - 4 - px(6)) / 2
        cx = w - 2 - px(3) - r if self.value else 2 + px(3) + r
        self.create_oval(cx - r, h / 2 - r, cx + r, h / 2 + r, fill="#FFFFFF", outline="#FFFFFF")
        if self._focus:
            round_rect(self, 0, 0, w, h, h / 2, fill="", outline=c["accent_text"], width=2)


class Segmented(tk.Frame):
    """Two or more mutually exclusive buttons (used for Light / Dark)."""

    def __init__(self, parent, theme, options, value, command, bg=None):
        super().__init__(parent, bg=bg or theme.c["surface"])
        self.theme, self.command, self.value, self.buttons = theme, command, value, {}
        for key, label in options:
            btn = CanvasButton(self, theme, label, command=lambda k=key: self.select(k),
                               kind="primary" if key == value else "secondary", height=32, min_width=84,
                               bg=bg or theme.c["surface"])
            btn.pack(side="left", padx=(0, px(6)))
            self.buttons[key] = btn

    def select(self, key):
        if key == self.value:
            return
        self.value = key
        for k, b in self.buttons.items():
            b.configure_button(kind="primary" if k == key else "secondary")
        self.command(key)


# ---------------------------------------------------------------- tooltip / toast
class Tooltip:
    def __init__(self, widget, theme, text):
        self.widget, self.theme, self.text, self.tip, self._job = widget, theme, text, None, None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _e):
        self._job = self.widget.after(450, self._show)

    def _show(self):
        if self.tip:
            return
        c = self.theme.c
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + px(6)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, bg=c["toast_bg"], fg=c["toast_text"], font=self.theme.font("small"),
                 padx=px(8), pady=px(4)).pack()

    def _hide(self, _e=None):
        if self._job:
            try:
                self.widget.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        if self.tip:
            self.tip.destroy()
            self.tip = None


class Toast:
    def __init__(self, root, theme):
        self.root, self.theme, self.frame, self._job = root, theme, None, None

    def show(self, message: str, tone: str = "neutral", ms: int = 2600):
        self.dismiss()
        c = self.theme.c
        self.frame = tk.Frame(self.root, bg=c["toast_bg"], padx=px(16), pady=px(10))
        tk.Label(self.frame, text=message, bg=c["toast_bg"], fg=c["toast_text"], font=self.theme.font("body")).pack()
        self.frame.place(relx=1.0, rely=1.0, anchor="se", x=-px(24), y=-px(24))
        self.frame.lift()
        self._job = self.root.after(ms, self.dismiss)

    def dismiss(self):
        if self._job:
            try:
                self.root.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        if self.frame is not None:
            self.frame.destroy()
            self.frame = None


# ---------------------------------------------------------------- scrolling
class SlimScrollbar(tk.Canvas):
    def __init__(self, parent, theme, command):
        super().__init__(parent, width=px(10), bg=theme.c["bg"], highlightthickness=0, bd=0)
        self.theme, self.command, self.first, self.last = theme, command, 0.0, 1.0
        self._drag = None
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._motion)

    def set(self, first, last):
        self.first, self.last = float(first), float(last)
        self._draw()

    def _draw(self):
        self.delete("all")
        if self.last - self.first >= 0.999:
            return
        h = self.winfo_height()
        y1, y2 = self.first * h, self.last * h
        round_rect(self, 2, y1 + 1, px(10) - 2, max(y2 - 1, y1 + px(24)), px(4), fill=self.theme.c["border_strong"],
                   outline=self.theme.c["border_strong"])

    def _press(self, e):
        self._drag = e.y

    def _motion(self, e):
        h = max(1, self.winfo_height())
        delta = (e.y - self._drag) / h
        self._drag = e.y
        self.command("moveto", max(0.0, min(1.0 - (self.last - self.first), self.first + delta)))


class ScrollFrame(tk.Frame):
    """Vertically scrolling container; put content into ``.inner``."""

    def __init__(self, parent, theme):
        bg = theme.c["bg"]
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = SlimScrollbar(self, theme, self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas)
        self.on_width = None
        self._last_w = 0
        self.canvas.bind_all("<MouseWheel>", self._wheel, add="+")
        self.canvas.bind_all("<Button-4>", self._wheel, add="+")
        self.canvas.bind_all("<Button-5>", self._wheel, add="+")

    def _on_canvas(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)
        if self.on_width and abs(e.width - self._last_w) > 1:
            self._last_w = e.width
            self.on_width(e.width)

    def _wheel(self, e):
        try:
            under = self.winfo_containing(e.x_root, e.y_root)
        except Exception:
            return
        if under is None or not str(under).startswith(str(self)):
            return
        if self.bar.last - self.bar.first >= 0.999:
            return
        if e.num == 4:
            step = -1
        elif e.num == 5:
            step = 1
        else:
            step = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(step * 3, "units")

    def scroll_top(self):
        self.canvas.yview_moveto(0)

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()


# ---------------------------------------------------------------- search box
class SearchBox(tk.Frame):
    PLACEHOLDER = "Search automations\u2026  (Ctrl+K)"

    def __init__(self, parent, theme, on_change, on_enter, width=300):
        c = theme.c
        super().__init__(parent, bg=c["surface"], highlightthickness=1, highlightbackground=c["border_strong"],
                         highlightcolor=c["accent"])
        self.theme, self.on_change, self.on_enter = theme, on_change, on_enter
        self._placeholder = True
        icon = tk.Canvas(self, width=px(30), height=px(34), bg=c["surface"], highlightthickness=0, bd=0)
        icon.pack(side="left")
        draw_icon(icon, "search", px(9), px(9), px(16), c["text_faint"])
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, relief="flat", bd=0, bg=c["surface"],
                              fg=c["text_faint"], insertbackground=c["text"], font=theme.font("body"),
                              width=max(10, int(width / 8)))
        self.entry.pack(side="left", fill="x", expand=True, ipady=px(6), padx=(0, px(10)))
        self._show_placeholder()
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<KeyRelease>", self._changed)
        self.entry.bind("<Return>", lambda e: self.on_enter())
        self.entry.bind("<Escape>", lambda e: self.clear())

    def _show_placeholder(self):
        self._placeholder = True
        self.entry.delete(0, "end")
        self.entry.insert(0, self.PLACEHOLDER)
        self.entry.config(fg=self.theme.c["text_faint"])

    def _focus_in(self, _e):
        if self._placeholder:
            self.entry.delete(0, "end")
            self.entry.config(fg=self.theme.c["text"])
            self._placeholder = False

    def _focus_out(self, _e):
        if not self.entry.get().strip():
            self._show_placeholder()

    def _changed(self, e):
        if e.keysym in ("Return", "Escape", "Tab"):
            return
        self.on_change(self.query())

    def query(self) -> str:
        return "" if self._placeholder else self.entry.get().strip()

    def set_query(self, text: str):
        if text:
            self._placeholder = False
            self.entry.config(fg=self.theme.c["text"])
            self.entry.delete(0, "end")
            self.entry.insert(0, text)
        else:
            self._show_placeholder()

    def clear(self):
        self._show_placeholder()
        self.on_change("")

    def focus_search(self):
        self.entry.focus_set()
        self.entry.select_range(0, "end") if not self._placeholder else None


# ---------------------------------------------------------------- dialogs
def _center(win, parent, w, h):
    parent.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - h) // 3
    win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")


class Dialog(tk.Toplevel):
    """Themed modal dialog with an optional expandable technical-details area."""

    def __init__(self, parent, theme, title, message, tone="error", icon="alert", details="",
                 buttons=(("Close", "primary"),), width=480):
        super().__init__(parent)
        c = theme.c
        self.theme, self.result, self._details_open = theme, None, False
        self.withdraw()
        self.title(title)
        self.configure(bg=c["surface"])
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        body = tk.Frame(self, bg=c["surface"], padx=px(24), pady=px(22))
        body.pack(fill="both", expand=True)
        head = tk.Frame(body, bg=c["surface"])
        head.pack(fill="x")
        tile = tk.Canvas(head, width=px(44), height=px(44), bg=c["surface"], highlightthickness=0, bd=0)
        tile.pack(side="left", anchor="n")
        round_rect(tile, 0, 0, px(44), px(44), px(12), fill=c[f"{tone}_soft"], outline=c[f"{tone}_soft"])
        draw_icon(tile, icon, px(11), px(11), px(22), c[tone])
        text = tk.Frame(head, bg=c["surface"])
        text.pack(side="left", fill="x", expand=True, padx=(px(14), 0))
        tk.Label(text, text=title, bg=c["surface"], fg=c["text"], font=theme.font("section"), anchor="w").pack(fill="x")
        tk.Label(text, text=message, bg=c["surface"], fg=c["text_muted"], font=theme.font("body"), anchor="w",
                 justify="left", wraplength=px(width - 130)).pack(fill="x", pady=(px(4), 0))
        if details:
            self.toggle_btn = CanvasButton(body, theme, "Show technical details", command=self._toggle, kind="ghost",
                                           height=30, bg=c["surface"], font_key="small_bold")
            self.toggle_btn.pack(anchor="w", pady=(px(12), 0))
        self.details_host = tk.Frame(body, bg=c["surface"])
        self.details_host.pack(fill="x")
        if details:
            self.box = tk.Text(self.details_host, height=6, wrap="word", font=theme.font("mono"), bg=c["surface_alt"],
                               fg=c["text"], relief="flat", bd=0, padx=px(10), pady=px(8), highlightthickness=1,
                               highlightbackground=c["border"])
            self.box.insert("1.0", details)
            self.box.config(state="disabled")
            self._details = details
        row = tk.Frame(body, bg=c["surface"])
        row.pack(fill="x", pady=(px(18), 0))
        for label, kind in reversed(buttons):
            CanvasButton(row, theme, label, command=lambda l=label: self._close(l), kind=kind, height=34,
                         min_width=88, bg=c["surface"]).pack(side="right", padx=(px(8), 0))
        if details:
            CanvasButton(row, theme, "Copy details", command=self._copy, kind="secondary", height=34,
                         bg=c["surface"]).pack(side="left")
        self._width_px = px(width)
        self.bind("<Escape>", lambda e: self._close(buttons[0][0]))
        self.protocol("WM_DELETE_WINDOW", lambda: self._close(buttons[0][0]))
        self.update_idletasks()
        _center(self, parent.winfo_toplevel(), self._width_px, self.winfo_reqheight())
        self.deiconify()
        self.grab_set()
        self.focus_set()

    def _toggle(self):
        self._details_open = not self._details_open
        if self._details_open:
            self.box.pack(fill="x", pady=(px(10), 0))
            self.toggle_btn.configure_button(text="Hide technical details")
        else:
            self.box.pack_forget()
            self.toggle_btn.configure_button(text="Show technical details")
        self.update_idletasks()
        self.geometry(f"{self._width_px}x{self.winfo_reqheight()}")

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self._details)

    def _close(self, label):
        self.result = label
        self.grab_release()
        self.destroy()


def ask(parent, theme, title, message, tone="info", icon="info", details="", buttons=(("Close", "primary"),), width=480):
    dlg = Dialog(parent, theme, title, message, tone, icon, details, buttons, width)
    parent.wait_window(dlg)
    return dlg.result


class Panel(tk.Canvas):
    """Rounded surface that auto-sizes to the widgets placed in ``.inner``."""

    def __init__(self, parent, theme, pad=16, bg=None):
        self.theme, self._pad = theme, px(pad)
        super().__init__(parent, bg=bg or theme.c["bg"], highlightthickness=0, bd=0, height=px(40))
        self.inner = tk.Frame(self, bg=theme.c["surface"])
        self._win = self.create_window(self._pad, self._pad, window=self.inner, anchor="nw")
        self.bind("<Configure>", self._on_conf)
        self.inner.bind("<Configure>", self._on_inner)

    def _on_conf(self, e):
        self.itemconfigure(self._win, width=max(1, e.width - 2 * self._pad))
        self.delete("panel_bg")
        c = self.theme.c
        round_rect(self, 1, 1, e.width - 1, e.height - 1, px(12), fill=c["surface"], outline=c["border"], tags="panel_bg")
        self.tag_lower("panel_bg")

    def _on_inner(self, _e):
        height = self.inner.winfo_reqheight() + 2 * self._pad
        if abs(height - int(float(self["height"]))) > 1:
            self.config(height=height)
