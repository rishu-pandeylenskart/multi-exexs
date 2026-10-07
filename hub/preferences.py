"""Local, lightweight user preferences (theme, favourites, recent launches).

Stored as one small JSON file in the user's profile.  Every operation is
failure-tolerant: if the file cannot be read or written the launcher simply
runs with defaults - apps.json and launching never depend on it.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

MAX_RECENT = 20

DEFAULTS = {
    "theme": "light",
    "favorites": [],
    "recent": [],            # [{"id": str, "ts": float}], newest first
    "last_used": {},         # {id: ts}
    "remember_window": True,
    "start_minimized": False,
    "sidebar_collapsed": False,
    "window_geometry": "",
}

_GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)([+-]-?\d+)([+-]-?\d+)$")


def default_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "AutomationHub" / "preferences.json"
    return Path.home() / ".config" / "automation-hub" / "preferences.json"


class Preferences:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else default_path()
        self.data: dict = json.loads(json.dumps(DEFAULTS))
        self.load()

    # ---- persistence -------------------------------------------------
    def load(self) -> None:
        try:
            with self.path.open("r", encoding="utf-8") as handler:
                stored = json.load(handler)
        except Exception:
            return
        if not isinstance(stored, dict):
            return
        for key, default in DEFAULTS.items():
            value = stored.get(key, default)
            if isinstance(value, type(default)):
                self.data[key] = value
        if self.data["theme"] not in ("light", "dark"):
            self.data["theme"] = "light"

    def save(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as handler:
                json.dump(self.data, handler, indent=2)
            os.replace(tmp, self.path)
            return True
        except Exception:
            return False

    # ---- simple values -----------------------------------------------
    def get(self, key: str):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.save()

    # ---- favourites ---------------------------------------------------
    def is_favorite(self, app_id: str) -> bool:
        return app_id in self.data["favorites"]

    def toggle_favorite(self, app_id: str) -> bool:
        favorites = self.data["favorites"]
        if app_id in favorites:
            favorites.remove(app_id)
            state = False
        else:
            favorites.append(app_id)
            state = True
        self.save()
        return state

    # ---- recent launches ---------------------------------------------
    def record_launch(self, app_id: str, when: float | None = None) -> None:
        when = time.time() if when is None else when
        recent = [r for r in self.data["recent"] if r.get("id") != app_id]
        recent.insert(0, {"id": app_id, "ts": when})
        self.data["recent"] = recent[:MAX_RECENT]
        self.data["last_used"][app_id] = when
        self.save()

    def last_used(self, app_id: str) -> float | None:
        value = self.data["last_used"].get(app_id)
        return value if isinstance(value, (int, float)) else None

    def recent_ids(self) -> list[str]:
        return [r["id"] for r in self.data["recent"] if isinstance(r, dict) and "id" in r]

    def recent_entries(self) -> list[tuple[str, float]]:
        out = []
        for r in self.data["recent"]:
            if isinstance(r, dict) and "id" in r and isinstance(r.get("ts"), (int, float)):
                out.append((r["id"], float(r["ts"])))
        return out

    def clear_recent(self) -> None:
        self.data["recent"] = []
        self.data["last_used"] = {}
        self.save()

    # ---- window geometry ---------------------------------------------
    def saved_geometry(self, screen_w: int, screen_h: int, min_w: int, min_h: int) -> str:
        """Return a safe, on-screen geometry string or '' if none/invalid."""
        if not self.data.get("remember_window"):
            return ""
        match = _GEOMETRY_RE.match(self.data.get("window_geometry", "") or "")
        if not match:
            return ""
        width, height = int(match.group(1)), int(match.group(2))
        x, y = int(match.group(3)), int(match.group(4))
        width = max(min_w, min(width, screen_w))
        height = max(min_h, min(height, screen_h))
        if x < -50 or y < -10 or x > screen_w - 120 or y > screen_h - 120:
            return f"{width}x{height}"  # size only; let the OS place it
        return f"{width}x{height}+{x}+{y}"
