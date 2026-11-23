"""Merkt sich, welche Tools in einem Scope installiert sind (state.json)."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class InstalledTool:
    key: str
    version: str
    source: str  # "github" | "bundled"
    ref: str  # Tag oder Commit
    commit: str | None
    installed_at: str  # ISO-8601
    env: str = "venv"  # Name des aktiven venv-Ordners im Tool-Ordner


class State:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.tools: dict[str, InstalledTool] = {}
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.tools = {k: InstalledTool(**v) for k, v in raw.get("tools", {}).items()}

    def get(self, key: str) -> InstalledTool | None:
        return self.tools.get(key)

    def set(self, tool: InstalledTool) -> None:
        self.tools[tool.key] = tool
        self.save()

    def remove(self, key: str) -> None:
        if self.tools.pop(key, None) is not None:
            self.save()

    def save(self) -> None:
        """Atomar schreiben, damit ein Absturz die Datei nicht zerstört."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": 1, "tools": {k: asdict(v) for k, v in sorted(self.tools.items())}}
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".state-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
