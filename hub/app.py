"""Main window: sidebar, header, pages and launch orchestration."""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tkinter as tk
import webbrowser
from datetime import datetime

from . import APP_BRAND, APP_TAGLINE, APP_TITLE, REPO_SLUG, REPO_URL
from .build_info import load_build_info
from .cards import AppCard, NavItem
from .config import categories_in_order, load_apps_config, search_apps
from .icons import draw_icon
from .paths import get_assets_dir, get_resource_base
from .preferences import Preferences
from .process_manager import LaunchFailure, ProcessManager, Status
from .theme import Theme, px, set_scale
from .timeutil import greeting, relative_time
from .widgets import (CanvasButton, Panel, ScrollFrame, SearchBox, Segmented, Toast, Toggle, ask, round_rect)

LAUNCH_SETTLE_MS = 1500
POLL_MS = 2000
SIDEBAR_WIDE, SIDEBAR_NARROW = 232, 68
CONTENT_PAD = 28
CARD_MIN_W, CARD_GAP = 300, 16

NAV_MAIN = [("dashboard", "Dashboard", "home"), ("automations", "Automations", "grid"),
            ("favorites", "Favorites", "star"), ("recent", "Recent", "clock")]
NAV_BOTTOM = [("settings", "Settings", "sliders"), ("about", "About", "info")]


def enable_dpi_awareness():
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def open_path(path, select: bool = False) -> bool:
    """Open a folder (or reveal a file) in the OS file manager."""
    try:
        if os.name == "nt":
            if select and path.is_file():
                subprocess.Popen(["explorer", f"/select,{path}"])
            else:
                os.startfile(str(path.parent if path.is_file() else path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path.parent if path.is_file() else path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent if path.is_file() else path)])
        return True
    except Exception:
        return False


class HubApp:
    def __init__(self):
        enable_dpi_awareness()
        self.root = tk.Tk()
        set_scale(self.root.winfo_fpixels("1i") / 96.0)
        self.prefs = Preferences()
        self.cfg = load_apps_config()
        self.apps = self.cfg.apps
        self.pm = ProcessManager(get_assets_dir())
        self.build = load_build_info()
        self.page = "dashboard"
        self.query = ""
        self.category = None
        self.sidebar_collapsed = bool(self.prefs.get("sidebar_collapsed"))
        self.cards: dict[str, AppCard] = {}
        self._poll_job = None
        self._resize_job = None
        self._flows: list = []
        self._favorites_only = False
        self.recent_host = self.grid_host = self.chips_host = self.count_lbl = None
        self._cols = self._card_w = 0

        self.root.title(APP_TITLE)
        icon = get_resource_base() / "assets" / "app.ico"
        try:
            if icon.exists():
                self.root.iconbitmap(str(icon))
        except Exception:
            pass
        self.min_w, self.min_h = px(820), px(560)
        self.root.minsize(self.min_w, self.min_h)
        geometry = self.prefs.saved_geometry(self.root.winfo_screenwidth(), self.root.winfo_screenheight(),
                                             self.min_w, self.min_h)
        if not geometry:
            w, h = px(1120), px(740)
            w, h = min(w, self.root.winfo_screenwidth() - 80), min(h, self.root.winfo_screenheight() - 120)
            geometry = f"{w}x{h}+{(self.root.winfo_screenwidth() - w) // 2}+{max(0, (self.root.winfo_screenheight() - h) // 3)}"
        self.root.geometry(geometry)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind_all("<Control-k>", lambda e: self.focus_search())
        self.root.bind_all("<Control-K>", lambda e: self.focus_search())
        self.root.bind_all("<F5>", lambda e: self.refresh_status())
        self._build_ui()
        if self.prefs.get("start_minimized"):
            self.root.iconify()

    def run(self):
        self.root.mainloop()

    # ------------------------------------------------------------------ shell
    def _build_ui(self):
        for child in self.root.winfo_children():
            child.destroy()
        self.theme = Theme(self.prefs.get("theme"), self.root)
        c = self.theme.c
        self.root.configure(bg=c["bg"])
        self.toast = Toast(self.root, self.theme)
        self.cards, self._flows = {}, []

        self.side = tk.Frame(self.root, bg=c["surface"], width=px(SIDEBAR_NARROW if self.sidebar_collapsed else SIDEBAR_WIDE))
        self.side.pack(side="left", fill="y")
        self.side.pack_propagate(False)
        tk.Frame(self.root, bg=c["border"], width=1).pack(side="left", fill="y")
        self._build_sidebar()

        main = tk.Frame(self.root, bg=c["bg"])
        main.pack(side="left", fill="both", expand=True)
        self._build_header(main)
        self.scroll = ScrollFrame(main, self.theme)
        self.scroll.pack(fill="both", expand=True)
        self.scroll.on_width = self._on_content_width
        self.show_page(self.page)

    def _build_sidebar(self):
        c, theme = self.theme.c, self.theme
        brand = tk.Canvas(self.side, height=px(68), bg=c["surface"], highlightthickness=0, bd=0)
        brand.pack(fill="x")
        round_rect(brand, (px(SIDEBAR_NARROW) - px(38)) / 2, px(15), (px(SIDEBAR_NARROW) + px(38)) / 2, px(53), px(11),
                   fill=c["accent"], outline=c["accent"])
        draw_icon(brand, "hub", (px(SIDEBAR_NARROW) - px(22)) / 2, px(23), px(22), c["on_accent"])
        if not self.sidebar_collapsed:
            brand.create_text(px(62), px(34), text=APP_BRAND, anchor="w", font=theme.font("brand"), fill=c["text"])
        self.nav_items = []
        for key, label, icon in NAV_MAIN:
            item = NavItem(self.side, self, key, label, icon, lambda k=key: self.show_page(k))
            item.pack(fill="x", pady=1)
            self.nav_items.append(item)
        tk.Frame(self.side, bg=c["surface"]).pack(fill="both", expand=True)
        for key, label, icon in NAV_BOTTOM:
            item = NavItem(self.side, self, key, label, icon, lambda k=key: self.show_page(k))
            item.pack(fill="x", pady=1)
            self.nav_items.append(item)
        collapse = NavItem(self.side, self, None, "Collapse sidebar" if not self.sidebar_collapsed else "Expand sidebar",
                           "chevron_left" if not self.sidebar_collapsed else "chevron_right", self.toggle_sidebar)
        collapse.pack(fill="x", pady=(1, px(4)))
        self.collapse_item = collapse
        foot = tk.Label(self.side, text="" if self.sidebar_collapsed else self.build.short(), bg=c["surface"],
                        fg=c["text_faint"], font=theme.font("caption"), anchor="w")
        foot.pack(fill="x", padx=px(22), pady=(0, px(12)))

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        self.prefs.set("sidebar_collapsed", self.sidebar_collapsed)
        start = self.side.winfo_width()
        end = px(SIDEBAR_NARROW if self.sidebar_collapsed else SIDEBAR_WIDE)
        steps = 8

        def step(i):
            self.side.config(width=int(start + (end - start) * i / steps))
            if i < steps:
                self.root.after(14, lambda: step(i + 1))
            else:
                self._rebuild_keep_page()

        step(1)

    def _rebuild_keep_page(self):
        query = self.search.query() if hasattr(self, "search") else ""
        self._build_ui()
        if query:
            self.search.set_query(query)

    def _build_header(self, parent):
        c, theme = self.theme.c, self.theme
        bar = tk.Frame(parent, bg=c["bg"], padx=px(CONTENT_PAD), pady=px(20))
        bar.pack(fill="x")
        right = tk.Frame(bar, bg=c["bg"])
        right.pack(side="right", anchor="n")
        self.search = SearchBox(right, theme, self.on_search, self.on_search_enter, width=280)
        self.search.pack(side="left", padx=(0, px(8)))
        for icon, tip, cmd in (("refresh", "Refresh application status (F5)", self.refresh_status),
                               ("sliders", "Settings", lambda: self.show_page("settings"))):
            CanvasButton(right, theme, "", command=cmd, kind="ghost", icon=icon, height=36, bg=c["bg"],
                         tooltip=tip).pack(side="left")
        left = tk.Frame(bar, bg=c["bg"])
        left.pack(side="left", fill="x", expand=True, anchor="n")
        self.h_eyebrow = tk.Label(left, bg=c["bg"], fg=c["text_muted"], font=theme.font("body"), anchor="w")
        self.h_title = tk.Label(left, bg=c["bg"], fg=c["text"], font=theme.font("title"), anchor="w")
        self.h_sub = tk.Label(left, bg=c["bg"], fg=c["text_muted"], font=theme.font("body"), anchor="w")
        for w in (self.h_eyebrow, self.h_title, self.h_sub):
            w.pack(fill="x")
        if self.query:
            self.search.set_query(self.query)

    def _update_header(self):
        n = len(self.apps)
        ready = sum(1 for a in self.apps if self.pm.status(a) in (Status.READY, Status.RUNNING, Status.LAUNCHING))
        plural = "tool" if n == 1 else "tools"
        if self.page == "dashboard":
            eyebrow, title = greeting(datetime.now().hour), APP_TITLE
            sub = f"{n} automation {plural} available \u00b7 {ready} ready"
        else:
            eyebrow, title = APP_TITLE, {"automations": "Automations", "favorites": "Favorites", "recent": "Recently used",
                                         "settings": "Settings", "about": "About"}[self.page]
            sub = {"automations": f"{n} automation {plural}", "favorites": "Starred tools appear first everywhere",
                   "recent": "Your latest launches on this PC", "settings": "Preferences are stored locally on this PC",
                   "about": APP_TAGLINE}[self.page]
        self.h_eyebrow.config(text=eyebrow)
        self.h_title.config(text=title)
        self.h_sub.config(text=sub)

    # ------------------------------------------------------------------ pages
    def show_page(self, key: str):
        self.page = key
        self.scroll.clear()
        self._flows, self.cards = [], {}
        self.recent_host = self.grid_host = self.chips_host = self.count_lbl = None
        self._cols = self._card_w = 0
        c = self.theme.c
        self.body = tk.Frame(self.scroll.inner, bg=c["bg"], padx=px(CONTENT_PAD), pady=px(4))
        self.body.pack(fill="x")
        {"dashboard": self._page_dashboard, "automations": self._page_automations, "favorites": self._page_favorites,
         "recent": self._page_recent, "settings": self._page_settings, "about": self._page_about}[key]()
        self._update_header()
        for item in self.nav_items:
            item.render()
        self.scroll.scroll_top()
        self.root.after(30, self._layout_all)

    def _section(self, text, right_widget_factory=None):
        c = self.theme.c
        row = tk.Frame(self.body, bg=c["bg"])
        row.pack(fill="x", pady=(px(18), px(10)))
        tk.Label(row, text=text, bg=c["bg"], fg=c["text"], font=self.theme.font("section")).pack(side="left")
        holder = None
        if right_widget_factory:
            holder = tk.Frame(row, bg=c["bg"])
            holder.pack(side="right")
            right_widget_factory(holder)
        return row

    def _banner(self):
        if not (self.cfg.error or self.cfg.warnings):
            return
        c = self.theme.c
        panel = Panel(self.body, self.theme, pad=12, bg=c["bg"])
        panel.pack(fill="x", pady=(0, px(6)))
        row = tk.Frame(panel.inner, bg=c["surface"])
        row.pack(fill="x")
        msg = ("The application list (apps.json) could not be read, so bundled EXEs are shown instead."
               if self.cfg.error else "Some entries in apps.json were skipped.")
        tk.Label(row, text=msg, bg=c["surface"], fg=c["warning"], font=self.theme.font("body_bold"), anchor="w",
                 wraplength=px(560), justify="left").pack(side="left", fill="x", expand=True)
        detail = "\n".join(([self.cfg.error] if self.cfg.error else []) + self.cfg.warnings)
        CanvasButton(row, self.theme, "Details", kind="secondary", height=30, bg=c["surface"],
                     command=lambda: ask(self.root, self.theme, "Configuration problem", msg, "warning", "alert", detail)
                     ).pack(side="right")

    # -- dashboard / automations / favorites -----------------------------------
    def _page_dashboard(self):
        self._banner()
        self._section("Quick actions")
        qa = tk.Frame(self.body, bg=self.theme.c["bg"])
        qa.pack(fill="x")
        recent = self._most_recent_launchable()
        favs = self._ready_favorites()
        actions = [("Launch most recent", "clock", self.launch_most_recent, recent is not None),
                   ("Launch favorites", "star", self.launch_favorites, bool(favs)),
                   ("Refresh status", "refresh", self.refresh_status, True),
                   ("Open app folder", "folder", self.open_app_folder, True),
                   ("Version info", "info", self.show_version, True)]
        widgets = []
        for text, icon, cmd, enabled in actions:
            b = CanvasButton(qa, self.theme, text, command=cmd, kind="secondary", icon=icon, height=36, bg=self.theme.c["bg"])
            if not enabled:
                b.configure_button(state="disabled")
            widgets.append(b)
        self._register_flow(qa, widgets)
        if self.prefs.recent_entries():
            self._section("Recently used", lambda h: CanvasButton(
                h, self.theme, "View all", kind="ghost", height=30, bg=self.theme.c["bg"], font_key="small_bold",
                command=lambda: self.show_page("recent")).pack())
            self.recent_host = tk.Frame(self.body, bg=self.theme.c["bg"])
            self.recent_host.pack(fill="x")
            self._render_recent(limit=3)
        self._grid_section("All automations", with_chips=True)

    def _page_automations(self):
        self._banner()
        self._grid_section("All automations", with_chips=True)

    def _page_favorites(self):
        self._grid_section("Favorites", with_chips=False, favorites_only=True)

    def _grid_section(self, title, with_chips, favorites_only=False):
        c = self.theme.c
        self._favorites_only = favorites_only
        self._section(title, lambda h: setattr(self, "count_lbl", tk.Label(
            h, bg=c["bg"], fg=c["text_faint"], font=self.theme.font("small"))) or self.count_lbl.pack())
        if with_chips:
            self.chips_host = tk.Frame(self.body, bg=c["bg"])
            self.chips_host.pack(fill="x", pady=(0, px(12)))
            self._render_chips()
        self.grid_host = tk.Frame(self.body, bg=c["bg"])
        self.grid_host.pack(fill="x")
        self._render_grid()

    def _visible_apps(self):
        apps = search_apps(self.apps, self.query)
        if self.category and self.page in ("dashboard", "automations"):
            apps = [a for a in apps if a.category == self.category]
        if self._favorites_only:
            apps = [a for a in apps if self.prefs.is_favorite(a.id)]
        return sorted(apps, key=lambda a: 0 if self.prefs.is_favorite(a.id) else 1)  # stable: favourites first

    def _render_chips(self):
        if not self.chips_host:
            return
        for child in self.chips_host.winfo_children():
            child.destroy()
        c = self.theme.c
        widgets = []
        cats = categories_in_order(self.apps)
        if len(cats) > 1:
            for label, value, count in [("All", None, len(self.apps))] + [
                    (cat, cat, sum(1 for a in self.apps if a.category == cat)) for cat in cats]:
                selected = self.category == value
                b = CanvasButton(self.chips_host, self.theme, f"{label}  {count}", kind="soft" if selected else "secondary",
                                 height=32, bg=c["bg"], font_key="small_bold" if selected else "small",
                                 command=lambda v=value: self.set_category(v))
                widgets.append(b)
        self._flows = [f for f in self._flows if f[0] is not self.chips_host]
        self._register_flow(self.chips_host, widgets, gap=px(8))

    def set_category(self, value):
        self.category = value
        self._render_chips()
        self._render_grid()
        self._layout_all()

    def _render_grid(self):
        if not self.grid_host:
            return
        for child in self.grid_host.winfo_children():
            child.destroy()
        self.cards = {}
        self._cols = self._card_w = 0
        c = self.theme.c
        apps = self._visible_apps()
        if self.count_lbl:
            self.count_lbl.config(text=f"{len(apps)} shown" if (self.query or self.category) else f"{len(apps)} total")
        if not apps:
            self._empty_state()
            return
        for entry in apps:
            self.cards[entry.id] = AppCard(self.grid_host, self, entry, px(CARD_MIN_W))
        self._layout_cards()

    def _empty_state(self):
        c, theme = self.theme.c, self.theme
        box = tk.Frame(self.grid_host, bg=c["bg"], pady=px(40))
        box.pack(fill="x")
        if self.query:
            title, text = "No matching automations", f"Nothing matches \u201c{self.query}\u201d. Try a name, courier or category."
        elif self._favorites_only:
            title, text = "No favorites yet", "Click the star on any automation card to pin it here and at the top of your lists."
        elif not self.apps:
            title, text = "No automations found", "apps.json is empty and no bundled EXEs were found. Add apps to apps.json and rebuild."
        else:
            title, text = "Nothing in this category", "Choose another category above."
        tk.Label(box, text=title, bg=c["bg"], fg=c["text"], font=theme.font("section")).pack()
        tk.Label(box, text=text, bg=c["bg"], fg=c["text_muted"], font=theme.font("body"), wraplength=px(480)).pack(pady=(px(6), px(12)))
        if self.query:
            CanvasButton(box, theme, "Clear search", kind="secondary", height=34, bg=c["bg"], command=self.search.clear).pack()
        elif self._favorites_only:
            CanvasButton(box, theme, "Browse automations", kind="primary", height=34, bg=c["bg"],
                         command=lambda: self.show_page("automations")).pack()

    # -- responsive layout -----------------------------------------------------
    def _register_flow(self, host, widgets, gap=None):
        self._flows.append((host, widgets, gap if gap is not None else px(10)))

    def _avail_width(self):
        return max(px(300), self.scroll.canvas.winfo_width() - 2 * px(CONTENT_PAD))

    def _flow_layout(self, host, widgets, gap):
        avail, x, row, col = self._avail_width(), 0, 0, 0
        for w in widgets:
            w.grid_forget()
        for w in widgets:
            need = w.winfo_reqwidth()
            if x and x + need > avail:
                row, col, x = row + 1, 0, 0
            w.grid(row=row, column=col, padx=(0, gap), pady=(0, gap // 2), sticky="w")
            x += need + gap
            col += 1

    def _layout_cards(self):
        if not self.cards:
            return
        avail, gap = self._avail_width(), px(CARD_GAP)
        cols = max(1, min(4, (avail + gap) // (px(CARD_MIN_W) + gap)))
        card_w = (avail - gap * (cols - 1)) // cols
        if cols == self._cols and card_w == self._card_w:
            return
        self._cols, self._card_w = cols, card_w
        for i, card in enumerate(self.cards.values()):
            card.set_width(card_w)
            card.grid(row=i // cols, column=i % cols, padx=(0, gap if (i % cols) != cols - 1 else 0),
                      pady=(0, gap // 2), sticky="nw")

    def _layout_all(self):
        for host, widgets, gap in self._flows:
            self._flow_layout(host, widgets, gap)
        self._layout_cards()

    def _on_content_width(self, _w):
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(60, self._layout_all)

    # -- recent -----------------------------------------------------------------
    def _page_recent(self):
        c = self.theme.c
        if self.prefs.recent_entries():
            self._section("Latest launches", lambda h: CanvasButton(
                h, self.theme, "Clear history", kind="secondary", height=30, bg=c["bg"], font_key="small_bold",
                command=self._clear_recent).pack())
        self.recent_host = tk.Frame(self.body, bg=c["bg"])
        self.recent_host.pack(fill="x", pady=(px(8), 0))
        self._render_recent(limit=20)

    def _clear_recent(self):
        if ask(self.root, self.theme, "Clear recent history?", "This only removes the list shown here and the \u201cLast used\u201d labels. "
               "Your automations are not affected.", "info", "info", "", (("Cancel", "secondary"), ("Clear", "primary"))) == "Clear":
            self.prefs.clear_recent()
            self.show_page(self.page)

    def _render_recent(self, limit):
        host = self.recent_host
        if host is None:
            return
        for child in host.winfo_children():
            child.destroy()
        c, theme = self.theme.c, self.theme
        by_id = {a.id: a for a in self.apps}
        rows = [(by_id[i], ts) for i, ts in self.prefs.recent_entries() if i in by_id][:limit]
        if not rows:
            tk.Label(host, text="Nothing launched yet. Apps you launch from here will appear in this list.", bg=c["bg"],
                     fg=c["text_muted"], font=theme.font("body")).pack(anchor="w", pady=px(12))
            return
        panel = Panel(host, theme, pad=6, bg=c["bg"])
        panel.pack(fill="x")
        for n, (entry, ts) in enumerate(rows):
            if n:
                tk.Frame(panel.inner, bg=c["border"], height=1).pack(fill="x", padx=px(10))
            row = tk.Frame(panel.inner, bg=c["surface"], padx=px(10), pady=px(8))
            row.pack(fill="x")
            tile = tk.Canvas(row, width=px(36), height=px(36), bg=c["surface"], highlightthickness=0, bd=0)
            tile.pack(side="left")
            round_rect(tile, 0, 0, px(36), px(36), px(9), fill=c["accent_soft"], outline=c["accent_soft"])
            draw_icon(tile, entry.icon, px(8), px(8), px(20), c["accent_text"])
            info = tk.Frame(row, bg=c["surface"])
            info.pack(side="left", padx=px(12), fill="x", expand=True)
            tk.Label(info, text=entry.name, bg=c["surface"], fg=c["text"], font=theme.font("body_bold"), anchor="w").pack(fill="x")
            tk.Label(info, text=f"{entry.category} \u00b7 {relative_time(ts)}", bg=c["surface"], fg=c["text_faint"],
                     font=theme.font("small"), anchor="w").pack(fill="x")
            CanvasButton(row, theme, "Launch", kind="soft", icon="arrow_right", icon_right=True, height=32,
                         bg=c["surface"], command=lambda e=entry: self.launch(e)).pack(side="right")

    # -- settings -----------------------------------------------------------------
    def _group(self, title):
        c = self.theme.c
        tk.Label(self.body, text=title, bg=c["bg"], fg=c["text"], font=self.theme.font("section")).pack(anchor="w", pady=(px(18), px(8)))
        panel = Panel(self.body, self.theme, pad=8, bg=c["bg"])
        panel.pack(fill="x")
        panel._first = True
        return panel

    def _setting(self, panel, title, desc, control_factory):
        c = self.theme.c
        if not panel._first:
            tk.Frame(panel.inner, bg=c["border"], height=1).pack(fill="x", padx=px(12))
        panel._first = False
        row = tk.Frame(panel.inner, bg=c["surface"], padx=px(12), pady=px(12))
        row.pack(fill="x")
        text = tk.Frame(row, bg=c["surface"])
        text.pack(side="left", fill="x", expand=True)
        tk.Label(text, text=title, bg=c["surface"], fg=c["text"], font=self.theme.font("body_bold"), anchor="w").pack(fill="x")
        if desc:
            tk.Label(text, text=desc, bg=c["surface"], fg=c["text_muted"], font=self.theme.font("small"), anchor="w",
                     justify="left", wraplength=px(480)).pack(fill="x")
        holder = tk.Frame(row, bg=c["surface"])
        holder.pack(side="right", padx=(px(16), 0))
        control_factory(holder)

    def _page_settings(self):
        c, theme = self.theme.c, self.theme
        sur = c["surface"]
        g = self._group("Appearance")
        self._setting(g, "Theme", "Switch between the light and dark interface.", lambda h: Segmented(
            h, theme, [("light", "Light"), ("dark", "Dark")], self.prefs.get("theme"), self.set_theme).pack())
        g = self._group("Launcher")
        self._setting(g, "Remember window size and position", "Reopen the launcher where you left it.",
                      lambda h: Toggle(h, theme, self.prefs.get("remember_window"),
                                       lambda v: self.prefs.set("remember_window", v)).pack())
        self._setting(g, "Start minimized", "Open the launcher in the taskbar instead of on screen.",
                      lambda h: Toggle(h, theme, self.prefs.get("start_minimized"),
                                       lambda v: self.prefs.set("start_minimized", v)).pack())
        g = self._group("Applications")
        self._setting(g, "Refresh application status", "Re-check which bundled EXEs are present and clear old errors.",
                      lambda h: CanvasButton(h, theme, "Refresh", kind="secondary", icon="refresh", height=34, bg=sur,
                                             command=self.refresh_status).pack())
        self._setting(g, "Application folder", str(self.pm.assets_dir),
                      lambda h: CanvasButton(h, theme, "Open folder", kind="secondary", icon="folder", height=34, bg=sur,
                                             command=self.open_app_folder).pack())
        self._setting(g, "Recent history", "Remove the recently-used list and \u201cLast used\u201d labels.",
                      lambda h: CanvasButton(h, theme, "Clear", kind="secondary", height=34, bg=sur,
                                             command=self._clear_recent).pack())

    def set_theme(self, name):
        self.prefs.set("theme", name)
        self._rebuild_keep_page()

    # -- about -----------------------------------------------------------------------
    def _page_about(self):
        c, theme = self.theme.c, self.theme
        panel = Panel(self.body, theme, pad=22, bg=c["bg"])
        panel.pack(fill="x", pady=(px(14), 0))
        head = tk.Frame(panel.inner, bg=c["surface"])
        head.pack(fill="x")
        tile = tk.Canvas(head, width=px(56), height=px(56), bg=c["surface"], highlightthickness=0, bd=0)
        tile.pack(side="left")
        round_rect(tile, 0, 0, px(56), px(56), px(15), fill=c["accent"], outline=c["accent"])
        draw_icon(tile, "hub", px(14), px(14), px(28), c["on_accent"])
        t = tk.Frame(head, bg=c["surface"])
        t.pack(side="left", padx=px(16))
        tk.Label(t, text=APP_BRAND, bg=c["surface"], fg=c["text"], font=theme.font("title"), anchor="w").pack(fill="x")
        tk.Label(t, text=APP_TAGLINE, bg=c["surface"], fg=c["text_muted"], font=theme.font("body"), anchor="w").pack(fill="x")
        stack = "Python {} \u00b7 Tkinter {}".format(sys.version.split()[0], tk.TkVersion)
        if getattr(sys, "frozen", False):
            stack += " \u00b7 packaged with PyInstaller"
        facts = [("Version", self.build.long()), ("Connected applications", str(len(self.apps))),
                 ("Technology", stack), ("Repository", REPO_SLUG)]
        for label, value in facts:
            tk.Frame(panel.inner, bg=c["border"], height=1).pack(fill="x", pady=(px(14), 0))
            row = tk.Frame(panel.inner, bg=c["surface"], pady=px(10))
            row.pack(fill="x")
            tk.Label(row, text=label, bg=c["surface"], fg=c["text_muted"], font=theme.font("body"), width=24, anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=c["surface"], fg=c["text"], font=theme.font("body"), anchor="w").pack(side="left")
            if label == "Repository":
                CanvasButton(row, theme, "Open on GitHub", kind="secondary", height=30, bg=c["surface"], font_key="small_bold",
                             command=lambda: webbrowser.open(REPO_URL)).pack(side="right")
        self._section("Connected applications")
        panel = Panel(self.body, theme, pad=6, bg=c["bg"])
        panel.pack(fill="x", pady=(0, px(24)))
        for n, a in enumerate(self.apps):
            if n:
                tk.Frame(panel.inner, bg=c["border"], height=1).pack(fill="x", padx=px(10))
            row = tk.Frame(panel.inner, bg=c["surface"], padx=px(10), pady=px(8))
            row.pack(fill="x")
            tk.Label(row, text=a.name, bg=c["surface"], fg=c["text"], font=theme.font("body_bold"), anchor="w", width=26).pack(side="left")
            tk.Label(row, text=a.filename, bg=c["surface"], fg=c["text_faint"], font=theme.font("mono"), anchor="w").pack(side="left")

    # ------------------------------------------------------------------ actions
    def focus_search(self):
        self.search.focus_search()

    def on_search(self, query):
        if query == self.query:
            return
        self.query = query
        if query and self.page not in ("dashboard", "automations", "favorites"):
            self.show_page("automations")
            return
        if self.grid_host is not None:
            self._render_grid()
            self._layout_all()

    def on_search_enter(self):
        apps = [a for a in self._visible_apps()] if self.grid_host is not None else search_apps(self.apps, self.query)
        if self.query and len(apps) == 1:
            self.launch(apps[0])

    def toggle_favorite(self, entry):
        state = self.prefs.toggle_favorite(entry.id)
        self.toast.show(f"{entry.name} {'added to' if state else 'removed from'} favorites")
        if self.page in ("favorites", "dashboard", "automations"):
            self._render_grid()
            self._layout_all()

    def show_more_menu(self, entry, x, y):
        c = self.theme.c
        menu = tk.Menu(self.root, tearoff=0, bg=c["surface"], fg=c["text"], activebackground=c["accent"],
                       activeforeground=c["on_accent"], bd=0, relief="flat", font=self.theme.font("body"))
        fav = self.prefs.is_favorite(entry.id)
        status = self.pm.status(entry)
        menu.add_command(label="Launch" if status != Status.MISSING else "Why is this unavailable?",
                         command=lambda: self.launch(entry))
        menu.add_command(label="Remove from favorites" if fav else "Add to favorites", command=lambda: self.toggle_favorite(entry))
        menu.add_separator()
        menu.add_command(label="Show in folder", command=lambda: self._reveal(entry))
        menu.add_command(label="Show details", command=lambda: self.show_details(entry))
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _reveal(self, entry):
        path = self.pm.exe_path(entry)
        if not open_path(path if path.exists() else self.pm.assets_dir, select=True):
            self.toast.show("Could not open the folder")

    def show_details(self, entry):
        status = self.pm.status(entry)
        lines = [f"Status: {status.value}", f"File: {self.pm.exe_path(entry)}", f"Category: {entry.category}"]
        if entry.repo:
            lines.append(f"Release source: {entry.repo} ({entry.tag})")
        err = self.pm.error_for(entry)
        if err:
            lines += ["", "Last problem:", err.technical]
        ask(self.root, self.theme, entry.name, entry.description or "Application details.", "info", "info", "\n".join(lines),
            width=520)

    def show_failure(self, failure: LaunchFailure):
        ask(self.root, self.theme, failure.title, failure.friendly, "error", "alert", failure.technical)

    def launch(self, entry, from_card=False, confirm_running=True):
        status = self.pm.status(entry)
        if status == Status.LAUNCHING:
            return
        if status == Status.MISSING:
            self.show_failure(self.pm.missing_failure(entry))
            return
        if status == Status.RUNNING and confirm_running:
            result = ask(self.root, self.theme, "Already running", f"{entry.name} is already open. Start another copy?",
                         "info", "info", "", (("Cancel", "secondary"), ("Start another", "primary")))
            if result != "Start another":
                return
        try:
            self.pm.start(entry)
        except LaunchFailure as failure:
            self._refresh_card(entry.id)
            self.show_failure(failure)
            return
        self.prefs.record_launch(entry.id)
        self._refresh_card(entry.id)
        self._refresh_recent_ui()
        self.root.after(LAUNCH_SETTLE_MS, lambda: self._settled(entry))
        self._ensure_poll()

    def _settled(self, entry):
        failure = self.pm.settle(entry)
        self._refresh_card(entry.id)
        if failure:
            self.show_failure(failure)
        else:
            self.toast.show(f"{entry.name} started")

    def _refresh_card(self, app_id):
        card = self.cards.get(app_id)
        if card is not None:
            try:
                card.render()
            except tk.TclError:
                pass

    def _refresh_recent_ui(self):
        if self.recent_host is not None:
            self._render_recent(limit=3 if self.page == "dashboard" else 20)

    def _ensure_poll(self):
        if self._poll_job is None and self.pm.any_running():
            self._poll_job = self.root.after(POLL_MS, self._tick)

    def _tick(self):
        self._poll_job = None
        for app_id in self.pm.reap():
            self._refresh_card(app_id)
        self._ensure_poll()

    def refresh_status(self):
        self.pm.clear_errors()
        self.pm.reap()
        for app_id in list(self.cards):
            self._refresh_card(app_id)
        self._update_header()
        ready = sum(1 for a in self.apps if self.pm.exists(a))
        self.toast.show(f"Status refreshed \u00b7 {ready} of {len(self.apps)} applications present")

    def _most_recent_launchable(self):
        by_id = {a.id: a for a in self.apps}
        for app_id in self.prefs.recent_ids():
            entry = by_id.get(app_id)
            if entry and self.pm.exists(entry):
                return entry
        return None

    def _ready_favorites(self):
        return [a for a in self.apps if self.prefs.is_favorite(a.id) and self.pm.exists(a)]

    def launch_most_recent(self):
        entry = self._most_recent_launchable()
        if entry:
            self.launch(entry)

    def launch_favorites(self):
        favs = self._ready_favorites()
        if not favs:
            return
        if len(favs) > 1:
            names = "\n".join(f"\u2022 {a.name}" for a in favs)
            if ask(self.root, self.theme, f"Launch {len(favs)} favorites?", names, "info", "info", "",
                   (("Cancel", "secondary"), ("Launch all", "primary"))) != "Launch all":
                return
        for entry in favs:
            if self.pm.status(entry) != Status.RUNNING:
                self.launch(entry, confirm_running=False)

    def open_app_folder(self):
        if not open_path(self.pm.assets_dir):
            self.toast.show("Could not open the application folder")

    def show_version(self):
        ask(self.root, self.theme, APP_BRAND, f"{self.build.long()}\n{len(self.apps)} connected applications", "info", "info")

    def on_close(self):
        try:
            if self.prefs.get("remember_window") and self.root.state() == "normal":
                self.prefs.data["window_geometry"] = self.root.winfo_geometry()
            self.prefs.save()
        finally:
            self.root.destroy()


def main():
    HubApp().run()
