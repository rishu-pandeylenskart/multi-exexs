"""Smoke test of the UI code paths using a fake ``tkinter``.

This does NOT prove the UI looks right - it only proves every page/handler runs
without NameError/AttributeError/logic errors.  Visual checks need a real
display (see README -> Testing).
"""
import itertools
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class FakeFont:
    def __init__(self, *a, **k): pass
    def measure(self, text): return 7 * len(text)


class W:
    _ids = itertools.count(1)
    pending_after = []

    def __init__(self, parent=None, *a, **k):
        self._opts = dict(k)
        self._kids = []
        self._parent = parent if isinstance(parent, W) else None
        if self._parent:
            self._parent._kids.append(self)

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name.startswith("create_"):
            return lambda *a, **k: next(W._ids)
        return lambda *a, **k: None

    def __getitem__(self, key): return self._opts.get(key, 100)
    def winfo_width(self): return 900
    def winfo_height(self): return 600
    def winfo_reqwidth(self): return 120
    def winfo_reqheight(self): return 40
    def winfo_rootx(self): return 0
    def winfo_rooty(self): return 0
    def winfo_screenwidth(self): return 1920
    def winfo_screenheight(self): return 1080
    def winfo_fpixels(self, s): return 96.0
    def winfo_containing(self, x, y): return None
    def winfo_toplevel(self): return self
    def winfo_geometry(self): return "1000x700+10+10"
    def winfo_children(self): return list(self._kids)
    def state(self): return "normal"
    def bbox(self, *a): return (0, 0, 10, 10)
    def get(self): return self._opts.get("_text", "")
    def after(self, ms, fn=None, *a):
        W.pending_after.append(fn)
        return len(W.pending_after)
    def destroy(self):
        for k in list(self._kids): k.destroy()
        if self._parent and self in self._parent._kids: self._parent._kids.remove(self)
    def wait_window(self, w): pass
    def mainloop(self): pass


class FakeVar:
    def __init__(self, *a, **k): self.v = ""
    def get(self): return self.v
    def set(self, v): self.v = v


def install_fake_tk():
    tk = types.ModuleType("tkinter")
    for n in ("Tk", "Frame", "Canvas", "Label", "Entry", "Text", "Toplevel", "Menu"):
        setattr(tk, n, type(n, (W,), {}))
    tk.StringVar = FakeVar
    tk.TclError = type("TclError", (Exception,), {})
    tk.TkVersion = 8.6
    font = types.ModuleType("tkinter.font")
    font.Font = FakeFont
    font.families = lambda root=None: ["Segoe UI", "Consolas"]
    tk.font = font
    sys.modules["tkinter"], sys.modules["tkinter.font"] = tk, font


class Ev:
    def __init__(self, x=0, y=0, keysym="a"):
        self.x, self.y, self.x_root, self.y_root, self.keysym, self.delta, self.num, self.width = x, y, x, y, keysym, 0, 0, 900


class UiSmoke(unittest.TestCase):
    def setUp(self):
        self.saved = {k: sys.modules.get(k) for k in ("tkinter", "tkinter.font")}
        install_fake_tk()
        for m in [m for m in sys.modules if m.startswith("hub.") and m not in (
                "hub.config", "hub.paths", "hub.preferences", "hub.process_manager", "hub.timeutil", "hub.icons", "hub.build_info")]:
            del sys.modules[m]
        import hub.app as app
        import hub.preferences as prefs
        self.app_mod = app
        tmp = Path(tempfile.mkdtemp())
        orig = prefs.Preferences.__init__
        prefs.default_path = lambda: tmp / "p.json"
        # fake EXEs so statuses are READY except one
        assets = tmp / "dist_assets"; assets.mkdir()
        import json
        for a in json.loads((ROOT / "apps.json").read_text(encoding="utf-8")):
            if "thailand" not in a["filename"]: (assets / a["filename"]).write_bytes(b"")
        app.get_assets_dir = lambda: assets
        self.calls = []
        import hub.process_manager as pmod
        class P:
            def poll(s): return None
        self.orig_popen = pmod.subprocess.Popen
        pmod.subprocess.Popen = lambda args, cwd=None: (self.calls.append((args, cwd)) or P())
        app.ask = lambda *a, **k: "Start another"
        W.pending_after.clear()

    def tearDown(self):
        import hub.process_manager as pmod
        pmod.subprocess.Popen = self.orig_popen
        for k, v in self.saved.items():
            if v is None: sys.modules.pop(k, None)
            else: sys.modules[k] = v
        for m in [m for m in sys.modules if m.startswith("hub.") and m in ("hub.app", "hub.widgets", "hub.cards", "hub.theme")]:
            del sys.modules[m]

    def test_all_pages_and_actions(self):
        hub = self.app_mod.HubApp()
        hub.pm._popen = lambda args, cwd=None: (self.calls.append((args, cwd)) or type("P", (), {"poll": lambda s: None})())
        for page in ("dashboard", "automations", "favorites", "recent", "settings", "about", "dashboard"):
            hub.show_page(page)
        self.assertEqual(len(hub.apps), 7)
        statuses = {a.name: hub.pm.status(a).value for a in hub.apps}
        self.assertEqual(statuses["THAILAND BULK BOOKING"], "missing")
        self.assertEqual(statuses["FEDEX AUTOMATION"], "ready")
        hub.show_page("dashboard")
        # search
        hub.on_search("fedex"); self.assertEqual([a.name for a in hub._visible_apps()][0], "FEDEX AUTOMATION")
        hub.on_search("zzz"); self.assertEqual(hub._visible_apps(), [])
        hub.on_search("")
        # category
        hub.set_category("Booking"); self.assertEqual(len(hub._visible_apps()), 2); hub.set_category(None)
        # favourites first
        fx = next(a for a in hub.apps if a.name == "FEDEX AUTOMATION")
        hub.toggle_favorite(fx); self.assertEqual(hub._visible_apps()[0].name, "FEDEX AUTOMATION")
        hub.show_page("favorites"); self.assertEqual([a.name for a in hub._visible_apps()], ["FEDEX AUTOMATION"])
        hub.show_page("dashboard")
        # launch -> exact original mechanics
        hub.launch(fx)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][0], [str(hub.pm.exe_path(fx))]); self.assertEqual(self.calls[0][1], str(hub.pm.assets_dir))
        self.assertEqual(hub.pm.status(fx).value, "launching")
        for fn in list(W.pending_after):
            if fn: fn()
        self.assertEqual(hub.pm.status(fx).value, "running")
        self.assertEqual(hub.prefs.recent_ids(), [fx.id])
        hub.launch(fx)  # running -> confirm (patched to "Start another")
        self.assertEqual(len(self.calls), 2)
        # missing app -> friendly failure, no launch
        th = next(a for a in hub.apps if "THAILAND" in a.name)
        hub.launch(th); self.assertEqual(len(self.calls), 2)
        # quick actions, card events, menu, theme, sidebar
        hub.refresh_status(); hub.launch_most_recent(); hub.launch_favorites(); hub.show_version(); hub.show_details(fx)
        card = hub.cards.get(fx.id) or next(iter(hub.cards.values()))
        card._motion(Ev(5, 5)); card._click(Ev(5, 5)); card._set_focus(True)
        hub.show_more_menu(fx, 10, 10)
        hub.set_theme("dark"); self.assertEqual(hub.prefs.get("theme"), "dark"); hub.set_theme("light")
        hub.toggle_sidebar()
        for fn in list(W.pending_after):
            if fn: fn()
        hub.on_close()

    def test_bad_config_and_empty(self):
        import hub.app as app, hub.config as cfg
        orig = cfg.load_apps_config
        app.load_apps_config = lambda: cfg.LoadResult(error="ValueError: bad", warnings=["x"], apps=[])
        hub = app.HubApp()
        for p in ("dashboard", "automations", "favorites"): hub.show_page(p)
        app.load_apps_config = orig


if __name__ == "__main__":
    unittest.main()
