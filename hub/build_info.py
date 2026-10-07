"""Build metadata written by ``scripts/write_build_info.py`` during CI."""
from __future__ import annotations

import json
from dataclasses import dataclass

from .paths import get_resource_base


@dataclass
class BuildInfo:
    build: str = ""
    commit: str = ""
    date: str = ""
    ref: str = ""

    @property
    def known(self) -> bool:
        return bool(self.build or self.commit or self.date)

    def short(self) -> str:
        if self.build:
            return f"Build {self.build}"
        if self.commit:
            return f"Build {self.commit}"
        return "Development build"

    def long(self) -> str:
        if not self.known:
            return "Development build (not produced by the release workflow)"
        parts = []
        if self.build:
            parts.append(f"Build {self.build}")
        if self.commit:
            parts.append(f"commit {self.commit}")
        if self.date:
            parts.append(self.date)
        return " \u00b7 ".join(parts)


def load_build_info() -> BuildInfo:
    path = get_resource_base() / "build_info.json"
    try:
        with path.open("r", encoding="utf-8-sig") as handler:
            data = json.load(handler)
        return BuildInfo(
            build=str(data.get("build", "") or ""),
            commit=str(data.get("commit", "") or "")[:7],
            date=str(data.get("date", "") or ""),
            ref=str(data.get("ref", "") or ""),
        )
    except Exception:
        return BuildInfo()
