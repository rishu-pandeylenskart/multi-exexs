import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:  # pragma: no cover
    tk = None
    ttk = None


def get_resource_base() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def load_apps() -> list[dict]:
    config_path = get_resource_base() / "apps.json"
    if not config_path.exists():
        config_path = Path(__file__).resolve().parent / "apps.json"

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handler:
            return json.load(handler)

    assets_dir = get_assets_dir()
    exe_files = sorted(assets_dir.glob("*.exe"))
    if not exe_files:
        return []

    apps = []
    for exe_file in exe_files:
        name = exe_file.stem.replace("_", " ").replace("-", " ")
        apps.append({
            "name": name.title(),
            "filename": exe_file.name,
        })
    return apps


def get_assets_dir() -> Path:
    base = get_resource_base()
    candidate = base / "dist_assets"
    if candidate.exists():
        return candidate
    fallback = base.parent / "dist_assets"
    if fallback.exists():
        return fallback
    return base


def launch_app(exe_path: Path):
    if not exe_path.exists():
        raise FileNotFoundError(f"Missing app: {exe_path}")
    subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))


def build_gui():
    if tk is None or ttk is None:
        raise RuntimeError("Tkinter is not available in this environment.")

    root = tk.Tk()
    root.title("5-in-1 Automation Launcher")
    root.geometry("720x480")
    root.minsize(640, 400)

    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)

    title = ttk.Label(frame, text="5-in-1 Automation Launcher", font=("Segoe UI", 18, "bold"))
    title.pack(anchor="w", pady=(0, 15))

    subtitle = ttk.Label(
        frame,
        text="Run any bundled automation tool from one launcher.",
        font=("Segoe UI", 10),
    )
    subtitle.pack(anchor="w", pady=(0, 15))

    apps = load_apps()
    assets_dir = get_assets_dir()

    if not apps:
        warning = ttk.Label(
            frame,
            text="No apps were found in apps.json. Add your app list and rebuild the launcher.",
            foreground="darkred",
            wraplength=600,
            justify="left",
        )
        warning.pack(anchor="w", pady=10)
        root.mainloop()
        return

    for app in apps:
        app_name = app.get("name", "UNKNOWN APP")
        filename = app.get("filename", "")
        exe_path = assets_dir / filename

        card = ttk.Frame(frame, padding=10)
        card.pack(fill="x", pady=5)

        row = ttk.Frame(card)
        row.pack(fill="x")

        label = ttk.Label(row, text=app_name, width=25, anchor="w")
        label.pack(side="left")

        status = "Available" if exe_path.exists() else "Missing"
        status_color = "green" if exe_path.exists() else "gray"
        status_label = ttk.Label(row, text=status, foreground=status_color, width=12)
        status_label.pack(side="right")

        action = ttk.Button(
            row,
            text="Launch",
            state="normal" if exe_path.exists() else "disabled",
            command=lambda path=exe_path: launch_app(path),
        )
        action.pack(side="right", padx=(0, 10))

    root.mainloop()


if __name__ == "__main__":
    try:
        build_gui()
    except Exception as exc:
        print(f"Launcher error: {exc}", file=sys.stderr)
        if os.name == "nt":
            input("Press Enter to close...")
        raise
