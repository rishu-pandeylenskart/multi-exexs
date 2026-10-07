import json, sys, tempfile, time, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hub.config import load_apps_config, categories_in_order, search_apps
from hub.preferences import Preferences
from hub.process_manager import ProcessManager, Status
from hub.timeutil import relative_time, greeting

ROOT = Path(__file__).resolve().parent.parent


class FakeProc:
    def __init__(self, code=None): self.code = code
    def poll(self): return self.code


class ConfigTests(unittest.TestCase):
    def test_real_apps_json(self):
        r = load_apps_config(ROOT / "apps.json", Path(tempfile.mkdtemp()))
        self.assertEqual(r.error, "")
        self.assertEqual(len(r.apps), 7)
        self.assertEqual(categories_in_order(r.apps), ["Data & Processing", "Shipping Automation", "Booking"])
        self.assertTrue(any(a.matches("fedex") for a in r.apps))
        self.assertEqual(search_apps(r.apps, "fedex")[0].name, "FEDEX AUTOMATION")

    def test_original_keys_preserved(self):
        for a in json.load(open(ROOT / "apps.json")):
            for k in ("name", "filename", "repo", "asset_name", "tag", "required"):
                self.assertIn(k, a)

    def test_invalid_json_falls_back(self):
        d = Path(tempfile.mkdtemp()); (d / "x.exe").write_bytes(b"")
        bad = d / "apps.json"; bad.write_text("{nope")
        r = load_apps_config(bad, d)
        self.assertTrue(r.error); self.assertEqual([a.filename for a in r.apps], ["x.exe"])

    def test_skips_bad_entries(self):
        d = Path(tempfile.mkdtemp()); p = d / "apps.json"
        p.write_text(json.dumps([{"name": "no file"}, 5, {"filename": "a.exe"}]))
        r = load_apps_config(p, d)
        self.assertEqual(len(r.apps), 1); self.assertEqual(len(r.warnings), 2)


class PrefTests(unittest.TestCase):
    def test_roundtrip_and_corrupt(self):
        p = Path(tempfile.mkdtemp()) / "p.json"
        a = Preferences(p); a.toggle_favorite("x"); a.record_launch("x"); a.set("theme", "dark")
        b = Preferences(p)
        self.assertTrue(b.is_favorite("x")); self.assertEqual(b.recent_ids(), ["x"]); self.assertEqual(b.get("theme"), "dark")
        p.write_text("garbage"); c = Preferences(p); self.assertEqual(c.get("theme"), "light")

    def test_unwritable_is_safe(self):
        a = Preferences(Path("/proc/nope/p.json")); a.toggle_favorite("x")  # must not raise
        self.assertTrue(a.is_favorite("x"))

    def test_geometry(self):
        p = Preferences(Path(tempfile.mkdtemp()) / "p.json")
        p.data["window_geometry"] = "1000x700+50+40"
        self.assertEqual(p.saved_geometry(1920, 1080, 820, 560), "1000x700+50+40")
        p.data["window_geometry"] = "1000x700+5000+40"
        self.assertEqual(p.saved_geometry(1920, 1080, 820, 560), "1000x700")


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.r = load_apps_config(ROOT / "apps.json", self.d)
        self.app = self.r.apps[0]

    def test_missing_then_ready(self):
        pm = ProcessManager(self.d)
        self.assertEqual(pm.status(self.app), Status.MISSING)
        (self.d / self.app.filename).write_bytes(b"")
        self.assertEqual(pm.status(self.app), Status.READY)

    def test_launch_uses_original_mechanics(self):
        (self.d / self.app.filename).write_bytes(b"")
        calls = []
        def popen(args, cwd=None): calls.append((args, cwd)); return FakeProc()
        pm = ProcessManager(self.d, popen)
        pm.start(self.app)
        self.assertEqual(calls, [([str(self.d / self.app.filename)], str(self.d))])
        self.assertEqual(pm.status(self.app), Status.LAUNCHING)
        self.assertIsNone(pm.settle(self.app))
        self.assertEqual(pm.status(self.app), Status.RUNNING)

    def test_missing_launch_friendly(self):
        pm = ProcessManager(self.d)
        with self.assertRaises(Exception) as cm: pm.start(self.app)
        self.assertIn("executable was not found", cm.exception.friendly)
        self.assertEqual(pm.status(self.app), Status.ERROR)
        pm.clear_errors(); self.assertEqual(pm.status(self.app), Status.MISSING)

    def test_instant_crash_and_reap(self):
        (self.d / self.app.filename).write_bytes(b"")
        proc = FakeProc(3)
        pm = ProcessManager(self.d, lambda a, cwd=None: proc)
        pm.start(self.app)
        self.assertIsNotNone(pm.settle(self.app)); self.assertEqual(pm.status(self.app), Status.ERROR)
        proc2 = FakeProc(); pm._popen = lambda a, cwd=None: proc2
        pm.start(self.app); pm.settle(self.app); self.assertTrue(pm.any_running())
        proc2.code = 0; self.assertEqual(pm.reap(), {self.app.id}); self.assertFalse(pm.any_running())

    def test_oserror_mapping(self):
        (self.d / self.app.filename).write_bytes(b"")
        def boom(a, cwd=None): raise PermissionError("denied")
        pm = ProcessManager(self.d, boom)
        with self.assertRaises(Exception) as cm: pm.start(self.app)
        self.assertIn("did not allow", cm.exception.friendly)


class TimeTests(unittest.TestCase):
    def test_relative(self):
        now = time.time()
        self.assertEqual(relative_time(now - 5, now), "Just now")
        self.assertEqual(relative_time(now - 300, now), "5 minutes ago")
        self.assertEqual(relative_time(now - 86400 * 3, now), "3 days ago")
        self.assertEqual(greeting(9), "Good morning"); self.assertEqual(greeting(20), "Good evening")


if __name__ == "__main__":
    unittest.main()
