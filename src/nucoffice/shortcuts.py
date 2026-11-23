"""Einträge im Anwendungsmenü (Linux: .desktop-Dateien, Windows: Startmenü-Verknüpfungen).

Die Verknüpfung zeigt direkt auf den Startbefehl in der aktiven venv. Weil jede Installation
einen neuen venv-Ordner bekommt, wird sie bei jeder Installation/jedem Update neu geschrieben.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .paths import Scope
from .registry import Tool


def menu_dir(scope: Scope) -> Path:
    if sys.platform == "win32":
        if scope is Scope.USER:
            base = Path(os.environ["APPDATA"])
        else:
            base = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
        return base / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "NucOffice"
    if scope is Scope.USER:
        data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        return Path(data_home) / "applications"
    return Path("/usr/share/applications")


def shortcut_path(tool: Tool, scope: Scope) -> Path:
    if sys.platform == "win32":
        return menu_dir(scope) / f"{tool.display_name}.lnk"
    return menu_dir(scope) / f"nucoffice-{tool.key}.desktop"


def _desktop_quote(arg: str) -> str:
    # Desktop-Entry-Spezifikation: Argumente mit Sonderzeichen in "…" mit \-Escapes.
    if not any(c in arg for c in ' \t\n"\'\\><~|&;$*?#()`'):
        return arg
    escaped = arg.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    return f'"{escaped}"'


def desktop_entry(tool: Tool, command: Path) -> str:
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        f"Name={tool.display_name}",
        f"Comment={tool.description}",
        f"Exec={_desktop_quote(str(command))}",
        f"Terminal={'true' if tool.terminal else 'false'}",
        "Categories=Science;Education;",
        "X-NucOffice-Tool=" + tool.key,
        "",
    ])


def create(tool: Tool, command: Path, scope: Scope) -> Path:
    target = shortcut_path(tool, scope)
    target.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        _create_windows_link(target, command, tool.description)
    else:
        target.write_text(desktop_entry(tool, command), encoding="utf-8")
        target.chmod(0o755)
    return target


def remove(tool: Tool, scope: Scope) -> None:
    shortcut_path(tool, scope).unlink(missing_ok=True)


def _create_windows_link(link: Path, command: Path, description: str) -> None:
    # Über PowerShell/WScript.Shell, damit keine Zusatzpakete (pywin32) nötig sind.
    def ps(s: str) -> str:
        return "'" + s.replace("'", "''") + "'"

    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut(" + ps(str(link)) + ");"
        f"$s.TargetPath = {ps(str(command))};"
        f"$s.WorkingDirectory = {ps(str(Path.home()))};"
        f"$s.Description = {ps(description)};"
        "$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        check=True, capture_output=True,
    )
