"""apps.json loading.

``apps.json`` stays the single source of truth.  The original keys
(name, filename, repo, asset_name, tag, required) are untouched; the UI only
*adds* optional keys (category, description, icon).  Anything missing falls
back to a neutral default - nothing is invented.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .paths import get_assets_dir, get_resource_base

DEFAULT_CATEGORY = "General"


@dataclass
class AppEntry:
    id: str
    name: str
    filename: str
    repo: str = ""
    asset_name: str = ""
    tag: str = "latest"
    required: bool = True
    category: str = DEFAULT_CATEGORY
    description: str = ""
    icon: str = "app"

    def search_blob(self) -> str:
        return " ".join(
            [self.name, self.description, self.category, self.repo, self.filename, self.asset_name]
        ).casefold()

    def matches(self, query: str) -> bool:
        tokens = query.casefold().split()
        if not tokens:
            return True
        blob = self.search_blob()
        return all(token in blob for token in tokens)


@dataclass
class LoadResult:
    apps: list[AppEntry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str = ""          # non-empty when apps.json could not be used
    source: str = ""         # where the list came from


def _text(value, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _normalise(raw_items, warnings: list[str]) -> list[AppEntry]:
    apps: list[AppEntry] = []
    seen: dict[str, int] = {}
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            warnings.append(f"Entry #{index + 1} in apps.json is not an object and was skipped.")
            continue
        filename = _text(item.get("filename"))
        if not filename:
            warnings.append(
                f"Entry '{_text(item.get('name'), '#' + str(index + 1))}' has no filename and was skipped."
            )
            continue
        name = _text(item.get("name")) or Path(filename).stem.replace("_", " ").replace("-", " ").title()
        app_id = filename.casefold()
        if app_id in seen:
            seen[app_id] += 1
            app_id = f"{app_id}#{seen[app_id]}"
        else:
            seen[app_id] = 1
        apps.append(
            AppEntry(
                id=app_id,
                name=name,
                filename=filename,
                repo=_text(item.get("repo")),
                asset_name=_text(item.get("asset_name")),
                tag=_text(item.get("tag"), "latest"),
                required=bool(item.get("required", True)),
                category=_text(item.get("category"), DEFAULT_CATEGORY),
                description=_text(item.get("description")),
                icon=_text(item.get("icon"), "app"),
            )
        )
    return apps


def scan_assets(assets_dir: Path) -> list[dict]:
    """Original fallback: no apps.json -> list whatever EXEs were bundled."""
    items = []
    try:
        exe_files = sorted(assets_dir.glob("*.exe"))
    except OSError:
        exe_files = []
    for exe_file in exe_files:
        name = exe_file.stem.replace("_", " ").replace("-", " ")
        items.append({"name": name.title(), "filename": exe_file.name})
    return items


def config_candidates() -> list[Path]:
    return [
        get_resource_base() / "apps.json",
        Path(__file__).resolve().parent.parent / "apps.json",
    ]


def load_apps_config(config_path: Path | None = None, assets_dir: Path | None = None) -> LoadResult:
    result = LoadResult()
    if assets_dir is None:
        assets_dir = get_assets_dir()

    path = config_path
    if path is None:
        path = next((c for c in config_candidates() if c.exists()), None)

    if path is not None and path.exists():
        result.source = str(path)
        try:
            with path.open("r", encoding="utf-8-sig") as handler:
                data = json.load(handler)
            if not isinstance(data, list):
                raise ValueError("apps.json must contain a list of applications.")
            result.apps = _normalise(data, result.warnings)
            return result
        except Exception as exc:  # invalid JSON etc. - keep the launcher usable
            result.error = f"{type(exc).__name__}: {exc}"
            result.warnings.append("apps.json could not be read; showing bundled EXEs instead.")

    raw = scan_assets(assets_dir)
    if not result.source:
        result.source = f"scan of {assets_dir}"
    result.apps = _normalise(raw, result.warnings)
    return result


def categories_in_order(apps: list[AppEntry]) -> list[str]:
    seen: list[str] = []
    for app in apps:
        if app.category not in seen:
            seen.append(app.category)
    return seen


def search_apps(apps: list[AppEntry], query: str) -> list[AppEntry]:
    """Filter by name/description/category/repo/filename; name hits rank first."""
    query = (query or "").strip()
    if not query:
        return list(apps)
    hits = [a for a in apps if a.matches(query)]
    needle = query.casefold()
    return sorted(hits, key=lambda a: 0 if needle in a.name.casefold() else 1)
