"""Liest die Tool-Registry (tools.toml)."""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

_PLATFORM = "windows" if sys.platform == "win32" else "linux" if sys.platform.startswith("linux") else sys.platform


@dataclass(frozen=True)
class Tool:
    key: str
    display_name: str
    repo: str  # "owner/name" auf GitHub
    package: str
    gui_entry: str
    description: str = ""
    extras: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ("linux", "windows")
    docs: str = "README.md"
    requires_system: tuple[str, ...] = ()
    terminal: bool = False
    system_site_packages: bool = False

    @property
    def repo_url(self) -> str:
        return f"https://github.com/{self.repo}"

    @property
    def supported(self) -> bool:
        return _PLATFORM in self.platforms

    @property
    def requirement(self) -> str:
        """Paketname inkl. Extras, z. B. ``radonlab[gui]``."""
        return f"{self.package}[{','.join(self.extras)}]" if self.extras else self.package


_TUPLE_FIELDS = {"extras", "platforms", "requires_system"}


def _tool_from_dict(key: str, data: dict) -> Tool:
    known = set(Tool.__dataclass_fields__) - {"key"}
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"Tool '{key}': unbekannte Felder {sorted(unknown)}")
    kwargs = {k: tuple(v) if k in _TUPLE_FIELDS else v for k, v in data.items()}
    return Tool(key=key, **kwargs)


def load_registry(path: Path | None = None) -> dict[str, Tool]:
    """Registry laden; ohne Pfad die mitgelieferte ``tools.toml``."""
    if path is None:
        text = resources.files("nucoffice").joinpath("tools.toml").read_text(encoding="utf-8")
    else:
        text = Path(path).read_text(encoding="utf-8")
    data = tomllib.loads(text)
    return {key: _tool_from_dict(key, d) for key, d in data.get("tools", {}).items()}
