"""Mitgelieferte Tool-Versionen (Offline-Installation).

Im NucOffice-Zip liegt ein Ordner ``bundled/`` mit Quellarchiven und einer ``manifest.json``::

    {"format": "nucoffice/bundled", "version": 1,
     "tools": {"plotrde": {"file": "plotrde-0.1.0.zip", "sha256": "…", "version": "0.1.0",
                           "ref": "v0.1.0", "commit": "…"}}}

Die Archive gehören nicht ins Git-Repo von NucOffice, sie werden beim Bauen des Release-Zips
erzeugt (``nucoffice bundle``).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tomllib
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

FORMAT = "nucoffice/bundled"
EXCLUDE_DIRS = {".git", ".venv", "venv", "build", "dist", "__pycache__", ".pytest_cache",
                ".ruff_cache", ".mypy_cache", ".tox", "_build"}


class BundleError(RuntimeError):
    pass


@dataclass(frozen=True)
class BundledTool:
    key: str
    file: str
    sha256: str
    version: str | None
    ref: str
    commit: str | None


def bundled_dir() -> Path:
    """``NUCOFFICE_BUNDLED`` oder ``bundled/`` neben ``src/`` (im Repo bzw. entpackten Zip)."""
    env = os.environ.get("NUCOFFICE_BUNDLED")
    return Path(env) if env else Path(__file__).resolve().parents[3] / "bundled"


def _manifest_path(base: Path) -> Path:
    return base / "manifest.json"


def _read_manifest(base: Path) -> dict:
    path = _manifest_path(base)
    if not path.exists():
        return {"format": FORMAT, "version": 1, "tools": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != FORMAT:
        raise BundleError(f"{path} ist kein NucOffice-Manifest.")
    return data


def available(key: str, base: Path | None = None) -> BundledTool | None:
    base = base or bundled_dir()
    entry = _read_manifest(base).get("tools", {}).get(key)
    if not entry or not (base / entry["file"]).exists():
        return None
    return BundledTool(key=key, **entry)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(entry: BundledTool, dest: Path, base: Path | None = None) -> Path:
    """Prüft die Prüfsumme und entpackt das Archiv nach ``dest`` (wird ersetzt)."""
    archive = (base or bundled_dir()) / entry.file
    if sha256_of(archive) != entry.sha256:
        raise BundleError(f"Prüfsumme von {archive.name} stimmt nicht – Datei beschädigt?")
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    root = dest.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if not target.is_relative_to(root):
                raise BundleError(f"Unzulässiger Pfad im Archiv: {member}")
        zf.extractall(dest)
    inner = list(dest.iterdir())
    if len(inner) == 1 and inner[0].is_dir():
        for child in inner[0].iterdir():
            child.rename(dest / child.name)
        inner[0].rmdir()
    return dest


def _static_version(source: Path) -> str | None:
    pyproject = source / "pyproject.toml"
    if pyproject.exists():
        return tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {}).get("version")
    return None


def _git(source: Path, *args: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(source), *args], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def create(key: str, source: Path, base: Path | None = None, *, version: str | None = None,
           ref: str | None = None) -> BundledTool:
    """Packt ``source`` als mitgelieferte Version von ``key`` und trägt sie ins Manifest ein.

    Ist ``source`` ein Git-Repo, wird nur der eingecheckte Stand (HEAD) gepackt –
    lokale Messdaten, venvs usw. kommen so nicht hinein. Sonst wird der Ordner ohne
    typische Bau- und Cache-Ordner gepackt.
    """
    source, base = Path(source).resolve(), base or bundled_dir()
    base.mkdir(parents=True, exist_ok=True)
    version = version or _static_version(source)
    commit = _git(source, "rev-parse", "HEAD")
    ref = ref or (f"v{version}" if version else (commit[:10] if commit else "lokal"))
    name = f"{key}-{version or ref}.zip"
    archive = base / name
    if commit:
        subprocess.run(["git", "-C", str(source), "archive", "--format=zip",
                        f"--prefix={key}/", "-o", str(archive), "HEAD"], check=True)
    else:
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for dirpath, dirnames, filenames in os.walk(source):
                dirnames[:] = [d for d in dirnames
                               if d not in EXCLUDE_DIRS and not d.endswith(".egg-info")]
                for fn in filenames:
                    p = Path(dirpath) / fn
                    zf.write(p, Path(key) / p.relative_to(source))
    manifest = _read_manifest(base)
    old = manifest["tools"].get(key)
    if old and old["file"] != name:
        (base / old["file"]).unlink(missing_ok=True)
    entry = BundledTool(key=key, file=name, sha256=sha256_of(archive), version=version,
                        ref=ref, commit=commit)
    manifest["tools"][key] = {k: v for k, v in asdict(entry).items() if k != "key"}
    _manifest_path(base).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8")
    return entry
