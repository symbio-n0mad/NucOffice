"""Installations- und Datenpfade je Betriebssystem und Scope (Benutzer/System)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import platformdirs

APP = "nucoffice"


class Scope(str, Enum):
    USER = "user"
    SYSTEM = "system"


@dataclass(frozen=True)
class Layout:
    """Alle Pfade für einen Scope."""

    root: Path  # Basisordner
    bin_dir: Path  # Starter für die Kommandozeile
    scope: Scope = Scope.USER

    @property
    def tools_dir(self) -> Path:
        return self.root / "tools"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def nucdb_dir(self) -> Path:
        # Muss zu NUCDB-SPEC.md Abschnitt 1.3 passen.
        return self.data_dir / "nucdb"

    @property
    def staging_dir(self) -> Path:
        return self.root / "staging"

    @property
    def state_file(self) -> Path:
        return self.root / "state.json"

    def tool_dir(self, key: str) -> Path:
        return self.tools_dir / key


def layout(scope: Scope = Scope.USER) -> Layout:
    if sys.platform == "win32":
        if scope is Scope.USER:
            root = Path(platformdirs.user_data_dir("NucOffice", appauthor=False, roaming=False))
        else:
            root = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "NucOffice"
        return Layout(root=root, bin_dir=root / "bin", scope=scope)
    if scope is Scope.USER:
        root = Path(platformdirs.user_data_dir(APP))
        return Layout(root=root, bin_dir=Path.home() / ".local" / "bin", scope=scope)
    return Layout(root=Path("/opt") / APP, bin_dir=Path("/usr/local/bin"), scope=scope)


def runtime_dir() -> Path:
    """Laufzeitdaten des aktuellen Benutzers (PID-Dateien), unabhängig vom Scope."""
    return Path(platformdirs.user_state_dir(APP))
