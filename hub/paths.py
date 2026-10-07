"""Resource / asset locations (identical rules to the original launcher)."""
from __future__ import annotations

import sys
from pathlib import Path


def get_resource_base() -> Path:
    """Folder that holds bundled data (PyInstaller temp dir or the repo root)."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_assets_dir() -> Path:
    """Folder that holds the bundled child EXEs (``dist_assets``)."""
    base = get_resource_base()
    candidate = base / "dist_assets"
    if candidate.exists():
        return candidate
    fallback = base.parent / "dist_assets"
    if fallback.exists():
        return fallback
    return base
