"""Code vor der Installation ansehen.

Der Quellcode wird in einen Staging-Ordner geladen, aber **nicht ausgeführt**. Man kann ihn dort
ansehen; installiert wird danach genau dieser geprüfte Stand (gepinnter Commit).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from .paths import Layout
from .registry import Tool
from .sources import github

MARKER = ".nucoffice-staged.json"


@dataclass(frozen=True)
class Staged:
    key: str
    repo: str
    ref: str
    commit: str
    path: Path

    @property
    def browse_url(self) -> str:
        """Ansicht genau dieses Stands auf GitHub."""
        return f"https://github.com/{self.repo}/tree/{self.commit}"

    def compare_url(self, old_commit: str) -> str:
        """Änderungen gegenüber einer installierten Version auf GitHub."""
        return f"https://github.com/{self.repo}/compare/{old_commit}...{self.commit}"


def stage(tool: Tool, lay: Layout, *, ref: str | None = None) -> Staged:
    """Lädt die neueste Version (oder ``ref``) in den Staging-Ordner."""
    if ref is None:
        rel = github.latest(tool.repo)
        ref, commit = rel.ref, rel.commit
    else:
        commit = github.resolve(tool.repo, ref)
    dest = lay.staging_dir / tool.key
    github.download_source(tool.repo, commit, dest)
    staged = Staged(key=tool.key, repo=tool.repo, ref=ref, commit=commit, path=dest)
    data = {k: v for k, v in asdict(staged).items() if k != "path"}
    (dest / MARKER).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return staged


def load_staged(tool: Tool, lay: Layout) -> Staged | None:
    path = lay.staging_dir / tool.key
    marker = path / MARKER
    if not marker.exists():
        return None
    data = json.loads(marker.read_text(encoding="utf-8"))
    if data.get("repo") != tool.repo:
        return None
    return Staged(path=path, **data)


def discard(tool: Tool, lay: Layout) -> None:
    shutil.rmtree(lay.staging_dir / tool.key, ignore_errors=True)


@dataclass(frozen=True)
class Summary:
    name: str | None
    version: str | None
    requires_python: str | None
    dependencies: list[str]
    optional: dict[str, list[str]]
    entry_points: dict[str, str]
    file_count: int
    python_files: int
    size_bytes: int
    build_hooks: list[str]  # Dateien, die beim Bauen Code ausführen (genauer ansehen!)


def summarize(path: Path) -> Summary:
    """Überblick über den geladenen Code, ohne etwas daraus auszuführen."""
    project: dict = {}
    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
    files = [p for p in path.rglob("*") if p.is_file() and p.name != MARKER]
    hooks = [n for n in ("setup.py", "hatch_build.py", "build.py") if (path / n).exists()]
    entries = {**project.get("scripts", {}), **project.get("gui-scripts", {})}
    return Summary(
        name=project.get("name"),
        version=project.get("version"),
        requires_python=project.get("requires-python"),
        dependencies=list(project.get("dependencies", [])),
        optional=dict(project.get("optional-dependencies", {})),
        entry_points=entries,
        file_count=len(files),
        python_files=sum(1 for p in files if p.suffix == ".py"),
        size_bytes=sum(p.stat().st_size for p in files),
        build_hooks=hooks,
    )


def open_folder(path: Path) -> None:
    """Öffnet den Ordner im Dateimanager des Systems."""
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
