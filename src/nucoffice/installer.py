"""Installiert Tools in eine eigene venv, deinstalliert sie und liefert den Startbefehl.

Ablauf einer Installation (auch Update):
1. neue venv in ``<tool>/venv-<zeitstempel>`` anlegen und das Tool hineininstallieren,
2. prüfen, dass der Startbefehl existiert,
3. in state.json auf die neue venv umschalten, dann alte venvs löschen.
Schlägt etwas fehl, bleibt die bisherige Installation unverändert.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import process
from .paths import Layout
from .registry import Tool
from .state import InstalledTool, State

DOC_ITEMS = ("README.md", "README.en.md", "docs")


class InstallError(RuntimeError):
    pass


def _venv_bin(venv: Path) -> Path:
    return venv / ("Scripts" if sys.platform == "win32" else "bin")


def _venv_python(venv: Path) -> Path:
    return _venv_bin(venv) / ("python.exe" if sys.platform == "win32" else "python")


def _entry_path(venv: Path, entry: str) -> Path:
    return _venv_bin(venv) / (f"{entry}.exe" if sys.platform == "win32" else entry)


def _run(cmd: list[str], log) -> None:
    log("$ " + " ".join(map(str, cmd)))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.stdout:
        log(proc.stdout.rstrip())
    if proc.returncode != 0:
        raise InstallError(f"Befehl fehlgeschlagen (Code {proc.returncode}): {cmd[0]}")


def missing_system_requirements(tool: Tool) -> list[str]:
    return [req for req in tool.requires_system if shutil.which(req) is None]


def _check_writable(lay: Layout) -> None:
    probe = lay.root
    while not probe.exists():
        probe = probe.parent
    if not os.access(probe, os.W_OK):
        raise InstallError(
            f"Keine Schreibrechte für {lay.root}. Für die systemweite Installation werden "
            "Admin-Rechte benötigt."
        )


def install(
    tool: Tool,
    source_dir: Path,
    lay: Layout,
    *,
    source: str,
    ref: str,
    commit: str | None = None,
    log=print,
) -> InstalledTool:
    """Installiert (oder aktualisiert) ``tool`` aus dem entpackten Quellordner ``source_dir``."""
    if not tool.supported:
        raise InstallError(f"{tool.display_name} ist auf diesem Betriebssystem nicht verfügbar.")
    if not (Path(source_dir) / "pyproject.toml").exists() and not (Path(source_dir) / "setup.py").exists():
        raise InstallError(f"{source_dir} enthält kein installierbares Python-Paket.")
    _check_writable(lay)
    missing = missing_system_requirements(tool)
    if missing:
        log(f"Hinweis: nicht gefunden: {', '.join(missing)} – {tool.display_name} läuft evtl. nicht.")

    tool_dir = lay.tool_dir(tool.key)
    state = State(lay.state_file)
    previous = state.get(tool.key)
    fresh = not tool_dir.exists()
    tool_dir.mkdir(parents=True, exist_ok=True)
    # Jede Installation bekommt einen eigenen venv-Ordner: venvs lassen sich nicht umbenennen,
    # weil ihre Pfade in Startskripten fest eingetragen sind.
    env_name = "venv-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    new = tool_dir / env_name

    try:
        venv_cmd = [sys.executable, "-m", "venv", str(new)]
        if tool.system_site_packages:
            venv_cmd.append("--system-site-packages")
        _run(venv_cmd, log)
        py = str(_venv_python(new))
        _run([py, "-m", "pip", "install", "--disable-pip-version-check", "-q", "--upgrade", "pip"], log)
        target = str(Path(source_dir).resolve())
        if tool.extras:
            target += f"[{','.join(tool.extras)}]"
        _run([py, "-m", "pip", "install", "--disable-pip-version-check", target], log)
        if not _entry_path(new, tool.gui_entry).exists():
            raise InstallError(f"Startbefehl '{tool.gui_entry}' wurde nicht installiert.")
        version = subprocess.run(
            [py, "-c", f"import importlib.metadata as m; print(m.version({tool.package!r}))"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except BaseException:
        shutil.rmtree(tool_dir if fresh else new, ignore_errors=True)
        raise

    # Laufende alte Version beenden, auf die neue umschalten, dann alte venvs aufräumen.
    process.stop(tool.key)
    _copy_docs(Path(source_dir), tool_dir / "docs")
    entry = InstalledTool(
        key=tool.key, version=version, source=source, ref=ref, commit=commit,
        installed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        env=env_name,
    )
    state.set(entry)
    for old in tool_dir.glob("venv*"):
        if old.name != env_name:
            shutil.rmtree(old, ignore_errors=True)
    if previous:
        log(f"Vorherige Version {previous.version} ersetzt.")
    log(f"{tool.display_name} {version} installiert.")
    return entry


def _copy_docs(source_dir: Path, dest: Path) -> None:
    """Lokale Kopie der Doku, damit sie auch offline angezeigt werden kann."""
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    for name in DOC_ITEMS:
        src = source_dir / name
        if src.is_dir():
            shutil.copytree(src, dest / name, ignore=shutil.ignore_patterns("_build", "__pycache__"))
        elif src.is_file():
            shutil.copy2(src, dest / name)


def uninstall(tool: Tool, lay: Layout, log=print) -> bool:
    """Entfernt das Tool vollständig. False, wenn es nicht installiert war."""
    tool_dir = lay.tool_dir(tool.key)
    state = State(lay.state_file)
    if not tool_dir.exists() and state.get(tool.key) is None:
        return False
    _check_writable(lay)
    process.stop(tool.key)
    shutil.rmtree(tool_dir)
    state.remove(tool.key)
    log(f"{tool.display_name} deinstalliert.")
    return True


def _terminal_wrapper() -> list[str]:
    for term, args in (("x-terminal-emulator", ["-e"]), ("gnome-terminal", ["--wait", "--"]),
                       ("konsole", ["-e"]), ("xfce4-terminal", ["-x"]), ("xterm", ["-e"])):
        if shutil.which(term):
            return [term, *args]
    raise InstallError("Kein Terminalprogramm gefunden, um das Konsolen-Tool zu starten.")


def active_venv(tool: Tool, lay: Layout) -> Path | None:
    inst = State(lay.state_file).get(tool.key)
    return lay.tool_dir(tool.key) / inst.env if inst else None


def launch_command(tool: Tool, lay: Layout) -> list[str]:
    venv = active_venv(tool, lay)
    entry = _entry_path(venv, tool.gui_entry) if venv else None
    if entry is None or not entry.exists():
        raise InstallError(f"{tool.display_name} ist nicht installiert.")
    return [*_terminal_wrapper(), str(entry)] if tool.terminal else [str(entry)]
