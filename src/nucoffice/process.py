"""Tools starten, stoppen und prüfen, ob sie laufen.

Pro gestartetem Tool wird eine Laufzeitdatei mit PID und Prozess-Startzeit abgelegt.
Die Startzeit schützt davor, eine wiederverwendete PID für das Tool zu halten.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import psutil

from .paths import runtime_dir


@dataclass(frozen=True)
class RunInfo:
    pid: int
    create_time: float
    cmd: list[str]


def _run_file(key: str, base: Path | None = None) -> Path:
    return (base or runtime_dir()) / "running" / f"{key}.json"


def _detach_kwargs() -> dict:
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        return {"creationflags": flags, "close_fds": True}
    return {"start_new_session": True, "close_fds": True}


def start(key: str, cmd: list[str], *, cwd: Path | None = None, base: Path | None = None) -> RunInfo:
    """Startet ``cmd`` losgelöst von NucOffice und merkt sich den Prozess."""
    current = status(key, base=base)
    if current is not None:
        raise RuntimeError(f"{key} läuft bereits (PID {current.pid})")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **_detach_kwargs(),
    )
    info = RunInfo(pid=proc.pid, create_time=psutil.Process(proc.pid).create_time(), cmd=list(cmd))
    path = _run_file(key, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(info.__dict__), encoding="utf-8")
    return info


def status(key: str, *, base: Path | None = None) -> RunInfo | None:
    """Liefert RunInfo, wenn das Tool läuft, sonst None (und räumt veraltete Einträge auf)."""
    path = _run_file(key, base)
    if not path.exists():
        return None
    try:
        info = RunInfo(**json.loads(path.read_text(encoding="utf-8")))
        proc = psutil.Process(info.pid)
        alive = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        if alive and abs(proc.create_time() - info.create_time) < 1.0:
            return info
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, TypeError, json.JSONDecodeError):
        pass
    path.unlink(missing_ok=True)
    return None


def stop(key: str, *, timeout: float = 10.0, base: Path | None = None) -> bool:
    """Beendet das Tool samt Kindprozessen. True, wenn etwas beendet wurde."""
    info = status(key, base=base)
    if info is None:
        return False
    try:
        parent = psutil.Process(info.pid)
        procs = [*parent.children(recursive=True), parent]
    except psutil.NoSuchProcess:
        procs = []
    for p in procs:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(procs, timeout=timeout)
    for p in alive:
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(alive, timeout=timeout)
    _run_file(key, base).unlink(missing_ok=True)
    return True
