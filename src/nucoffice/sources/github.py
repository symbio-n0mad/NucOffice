"""Neueste Version auf GitHub ermitteln und Quellcode als Archiv laden (ohne git).

Es wird nie die Git-Historie übertragen, nur der Code-Stand eines Tags oder Commits.
"""

from __future__ import annotations

import json
import shutil
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .. import __version__

API = "https://api.github.com"
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": f"NucOffice/{__version__}",
}


@dataclass(frozen=True)
class Release:
    ref: str  # Tag-Name oder Branch
    commit: str  # vollständiger Commit-Hash (gepinnt)
    is_tag: bool


def _get_json(url: str, timeout: float = 15.0):
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def latest(repo: str, track: str | None = None) -> Release:
    """Neueste Version: letztes GitHub-Release, sonst letzter Tag, sonst Standard-Branch.

    Mit ``track`` wird stattdessen immer der aktuelle Stand dieses Branches genommen.
    """
    if track:
        return Release(ref=track, commit=resolve(repo, track), is_tag=False)
    try:
        tag = _get_json(f"{API}/repos/{repo}/releases/latest")["tag_name"]
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        tags = _get_json(f"{API}/repos/{repo}/tags?per_page=100")
        tag = _newest_tag([t["name"] for t in tags]) if tags else None
    if tag:
        commit = _get_json(f"{API}/repos/{repo}/commits/{tag}")["sha"]
        return Release(ref=tag, commit=commit, is_tag=True)
    branch = _get_json(f"{API}/repos/{repo}")["default_branch"]
    commit = _get_json(f"{API}/repos/{repo}/commits/{branch}")["sha"]
    return Release(ref=branch, commit=commit, is_tag=False)


def resolve(repo: str, ref: str) -> str:
    """Tag, Branch oder (Kurz-)Commit in einen vollständigen Commit-Hash auflösen."""
    return _get_json(f"{API}/repos/{repo}/commits/{urllib.parse.quote(ref, safe='')}")["sha"]


def _version_key(tag: str):
    parts = []
    for p in tag.lstrip("vV").replace("-", ".").split("."):
        parts.append((0, int(p), "") if p.isdigit() else (1, 0, p))
    return parts


def _newest_tag(tags: list[str]) -> str:
    return max(tags, key=_version_key)


def download_source(repo: str, commit: str, dest: Path, timeout: float = 60.0) -> Path:
    """Lädt den Code-Stand ``commit`` nach ``dest`` (wird ersetzt) und gibt den Ordner zurück."""
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    archive = dest.with_suffix(".tar.gz")
    req = urllib.request.Request(f"{API}/repos/{repo}/tarball/{commit}", headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(archive, "wb") as fh:
        shutil.copyfileobj(resp, fh)
    try:
        with tarfile.open(archive) as tar:
            tar.extractall(dest, filter="data")  # verhindert Pfade außerhalb von dest
    finally:
        archive.unlink(missing_ok=True)
    # GitHub packt alles in einen Ordner "<owner>-<repo>-<sha>/" – den eine Ebene hochziehen.
    inner = [p for p in dest.iterdir()]
    if len(inner) == 1 and inner[0].is_dir():
        for child in inner[0].iterdir():
            child.rename(dest / child.name)
        inner[0].rmdir()
    return dest
