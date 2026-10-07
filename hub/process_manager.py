"""Starting child EXEs and tracking their state.

Launch mechanics are exactly the original ones:

    subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent))

Nothing else is passed (no arguments, no environment changes) so every child
stays a fully independent application.

"Running" is only reported for processes *this launcher started* (we hold the
Popen handle), which is the one case that is technically reliable.  There is
no background process scanning; the UI polls only while something it started
is still alive.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .config import AppEntry


class Status(str, Enum):
    READY = "ready"
    MISSING = "missing"
    LAUNCHING = "launching"
    RUNNING = "running"
    ERROR = "error"


@dataclass(eq=False)
class LaunchFailure(Exception):
    """A launch problem: a friendly sentence plus the raw technical detail."""

    title: str
    friendly: str
    technical: str

    def __str__(self) -> str:  # pragma: no cover - debugging convenience
        return f"{self.title}: {self.technical}"


def describe_os_error(app_name: str, exe_path: Path, exc: BaseException) -> LaunchFailure:
    technical = f"{type(exc).__name__}: {exc}\nPath: {exe_path}"
    winerror = getattr(exc, "winerror", None)
    if isinstance(exc, FileNotFoundError):
        return LaunchFailure(
            "Unable to launch",
            f"{app_name} is currently unavailable because its executable was not found.",
            technical,
        )
    if winerror == 740:
        return LaunchFailure(
            "Administrator permission needed",
            f"{app_name} asks for administrator permission, which the launcher cannot grant.",
            technical,
        )
    if winerror == 193:
        return LaunchFailure(
            "Unable to launch",
            f"{app_name} could not be started because the file is not a valid Windows application. "
            "It may be incomplete or damaged.",
            technical,
        )
    if isinstance(exc, PermissionError):
        return LaunchFailure(
            "Unable to launch",
            f"Windows did not allow {app_name} to start. Security software may be blocking it.",
            technical,
        )
    return LaunchFailure(
        "Unable to launch",
        f"{app_name} could not be started.",
        technical,
    )


class ProcessManager:
    def __init__(self, assets_dir: Path, popen=subprocess.Popen):
        self.assets_dir = Path(assets_dir)
        self._popen = popen
        self._procs: dict[str, list] = {}
        self._launching: set[str] = set()
        self._errors: dict[str, LaunchFailure] = {}

    # ---- queries -------------------------------------------------------
    def exe_path(self, app: AppEntry) -> Path:
        return self.assets_dir / app.filename

    def exists(self, app: AppEntry) -> bool:
        return self.exe_path(app).is_file()

    def _alive(self, app_id: str) -> list:
        return [p for p in self._procs.get(app_id, []) if p.poll() is None]

    def status(self, app: AppEntry) -> Status:
        if app.id in self._launching:
            return Status.LAUNCHING
        if self._alive(app.id):
            return Status.RUNNING
        if app.id in self._errors:
            return Status.ERROR
        if not self.exists(app):
            return Status.MISSING
        return Status.READY

    def error_for(self, app: AppEntry) -> LaunchFailure | None:
        return self._errors.get(app.id)

    def missing_failure(self, app: AppEntry) -> LaunchFailure:
        path = self.exe_path(app)
        return LaunchFailure(
            "Unable to launch",
            f"{app.name} is currently unavailable because its executable was not found.",
            f"Expected file: {path}",
        )

    def any_running(self) -> bool:
        return any(self._alive(app_id) for app_id in list(self._procs))

    # ---- actions -------------------------------------------------------
    def start(self, app: AppEntry):
        """Start the EXE.  Returns the Popen handle or raises LaunchFailure."""
        exe_path = self.exe_path(app)
        self._errors.pop(app.id, None)
        if not exe_path.is_file():
            failure = self.missing_failure(app)
            self._errors[app.id] = failure
            raise failure
        try:
            proc = self._popen([str(exe_path)], cwd=str(exe_path.parent))
        except Exception as exc:
            failure = describe_os_error(app.name, exe_path, exc)
            self._errors[app.id] = failure
            raise failure from exc
        self._procs.setdefault(app.id, []).append(proc)
        self._launching.add(app.id)
        return proc

    def settle(self, app: AppEntry) -> LaunchFailure | None:
        """Called shortly after start(): leave LAUNCHING, detect instant crashes."""
        self._launching.discard(app.id)
        procs = self._procs.get(app.id, [])
        if not procs:
            return None
        last = procs[-1]
        code = last.poll()
        if code is not None and code != 0:
            failure = LaunchFailure(
                "Application closed unexpectedly",
                f"{app.name} started but closed immediately.",
                f"Exit code: {code}\nPath: {self.exe_path(app)}",
            )
            self._errors[app.id] = failure
            return failure
        return None

    def reap(self) -> set[str]:
        """Drop finished processes; return ids whose running state changed."""
        changed: set[str] = set()
        for app_id in list(self._procs):
            before = len(self._procs[app_id])
            self._procs[app_id] = self._alive(app_id)
            if len(self._procs[app_id]) != before:
                changed.add(app_id)
            if not self._procs[app_id]:
                del self._procs[app_id]
        return changed

    def clear_errors(self) -> None:
        self._errors.clear()
