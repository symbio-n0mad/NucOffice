"""Gemeinsame Abläufe für Kommandozeile und Oberfläche."""

from __future__ import annotations

from dataclasses import dataclass

from . import staging
from .paths import Layout
from .registry import Tool
from .sources import bundled, github
from .state import InstalledTool, State


def short(commit: str | None) -> str:
    return f"Commit {commit[:10]}" if commit else "Commit unbekannt"


def obtain(tool: Tool, lay: Layout, source: str = "auto", ref: str | None = None, *,
           reuse_staged: bool, log=print) -> staging.Staged:
    """Quellcode bereitstellen: angesehener Stand, GitHub oder mitgelieferte Version.

    ``source="auto"``: GitHub; klappt das nicht, die mitgelieferte Version (falls vorhanden).
    """
    if reuse_staged:
        staged = staging.load_staged(tool, lay)
        if staged and source in ("auto", staged.source) and ref in (None, staged.ref):
            log(f"Verwende den angesehenen Stand {staged.ref} ({short(staged.commit)}).")
            return staged
    if source == "bundled":
        if ref:
            raise bundled.BundleError("Eine bestimmte Version geht nur mit Quelle GitHub.")
        log(f"Entpacke mitgelieferte Version von {tool.display_name} …")
        return staging.stage_bundled(tool, lay)
    try:
        log(f"Lade {tool.display_name} von GitHub …")
        return staging.stage(tool, lay, ref=ref)
    except OSError as exc:
        if source == "auto" and ref is None and bundled.available(tool.key):
            log(f"Laden von GitHub fehlgeschlagen ({exc}) – verwende die mitgelieferte Version.")
            return staging.stage_bundled(tool, lay)
        raise


@dataclass(frozen=True)
class UpdateInfo:
    key: str
    installed: InstalledTool
    latest_ref: str
    latest_commit: str

    @property
    def available(self) -> bool:
        return self.installed.commit != self.latest_commit


def check_update(tool: Tool, lay: Layout) -> UpdateInfo | None:
    """Vergleicht die installierte Version mit der neuesten auf GitHub (None: nicht installiert).

    Mitgelieferte/lokale Installationen ohne Commit gelten als veraltet, sobald es auf GitHub
    einen Stand gibt – Updates kommen immer von GitHub.
    """
    inst = State(lay.state_file).get(tool.key)
    if inst is None:
        return None
    rel = github.latest(tool.repo, tool.track)
    return UpdateInfo(key=tool.key, installed=inst, latest_ref=rel.ref, latest_commit=rel.commit)
