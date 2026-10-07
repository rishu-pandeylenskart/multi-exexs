"""Automation Hub launcher - entry point.

The UI lives in the ``hub`` package.  The helpers below keep the original
module-level names (load_apps / get_assets_dir / launch_app) available so any
external script that imported them keeps working.
"""
import subprocess
import sys
from pathlib import Path

from hub.config import load_apps_config
from hub.paths import get_assets_dir, get_resource_base  # noqa: F401  (re-exported)


def load_apps() -> list[dict]:
    """Original API: list of app dicts from apps.json (or bundled EXEs)."""
    return [
        {"name": a.name, "filename": a.filename, "repo": a.repo, "asset_name": a.asset_name,
         "tag": a.tag, "required": a.required}
        for a in load_apps_config().apps
    ]


def launch_app(exe_path: Path):
    """Original API: start a child EXE exactly as before."""
    if not exe_path.exists():
        raise FileNotFoundError(f"Missing app: {exe_path}")
    subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))


def build_gui():
    try:
        import tkinter  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Tkinter is not available in this environment.") from exc
    from hub.app import main
    main()


if __name__ == "__main__":
    try:
        build_gui()
    except Exception as exc:
        print(f"Launcher error: {exc}", file=sys.stderr)
        try:  # windowed build has no console - show the problem instead
            from tkinter import messagebox
            messagebox.showerror("Automation Hub", f"The launcher could not start.\n\n{type(exc).__name__}: {exc}")
        except Exception:
            pass
        raise
