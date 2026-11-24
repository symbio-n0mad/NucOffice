"""Dokumentation eines Tools finden – auch vor der Installation.

Reihenfolge: lokale Kopie (installiert) → mitgeliefertes Archiv → GitHub.
"""

from __future__ import annotations

import posixpath
import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .paths import Layout
from .registry import Tool
from .sources import bundled, github


@dataclass
class Docs:
    text: str  # Markdown
    origin: str  # "installiert" | "mitgeliefert" | "GitHub"
    base: Path | None = None  # Ordner für relative Bilder (nur lokal)
    pages: list[str] = field(default_factory=list)  # weitere Markdown-Seiten (relativ zu base)
    web_url: str | None = None


def _md_pages(base: Path) -> list[str]:
    pages = []
    for p in sorted(base.rglob("*.md")):
        rel = p.relative_to(base).as_posix()
        if "_build" not in rel:
            pages.append(rel)
    return pages


def load(tool: Tool, lay: Layout, *, timeout: float = 10.0) -> Docs:
    web = f"{tool.repo_url}#readme"
    local = lay.tool_dir(tool.key) / "docs"
    if (local / tool.docs).exists():
        return Docs(text=(local / tool.docs).read_text(encoding="utf-8"), origin="installiert",
                    base=local, pages=_md_pages(local), web_url=web)

    entry = bundled.available(tool.key)
    if entry is not None:
        with zipfile.ZipFile(bundled.bundled_dir() / entry.file) as zf:
            for name in zf.namelist():
                parts = name.split("/", 1)
                if len(parts) == 2 and parts[1] == tool.docs:
                    text = zf.read(name).decode("utf-8")
                    return Docs(text=text, origin="mitgeliefert", web_url=web)

    ref = tool.track or "HEAD"
    raw = f"https://raw.githubusercontent.com/{tool.repo}/{ref}/"
    try:
        with github._open(raw + tool.docs, timeout) as resp:
            text = resp.read().decode("utf-8")
    except github.GitHubError as exc:
        if exc.code == 404:
            raise github.GitHubError("Auf GitHub ist (noch) keine Dokumentation vorhanden.", 404) from exc
        raise
    cache = lay.root / "cache" / "docs" / tool.key
    text = _fetch_images(text, raw, posixpath.dirname(tool.docs), cache, timeout)
    return Docs(text=text, origin="GitHub", base=cache, web_url=web)


_MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
_HTML_IMAGE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
MAX_IMAGE_BYTES = 5_000_000
MAX_IMAGES = 20


def _fetch_images(text: str, raw_base: str, doc_dir: str, cache: Path, timeout: float) -> str:
    """Relative Bilder von GitHub in einen Zwischenspeicher laden; externe Bilder (Abzeichen
    u. Ä.) weglassen. QTextBrowser kann selbst nichts aus dem Netz nachladen."""
    shutil.rmtree(cache, ignore_errors=True)
    cache.mkdir(parents=True, exist_ok=True)
    count = 0

    def local(src: str) -> str | None:
        nonlocal count
        if "://" in src or src.startswith(("data:", "#", "/")):
            return None
        rel = posixpath.normpath(posixpath.join(doc_dir, src.split("#")[0].split("?")[0]))
        if rel.startswith(".."):
            return None
        target = cache / rel
        if not target.exists():
            if count >= MAX_IMAGES:
                return None
            count += 1
            try:
                with github._open(raw_base + rel, timeout) as resp:
                    data = resp.read(MAX_IMAGE_BYTES + 1)
            except OSError:
                return None
            if len(data) > MAX_IMAGE_BYTES:
                return None
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return rel

    def md(m: re.Match) -> str:
        rel = local(m.group(2))
        return f"![{m.group(1)}]({rel})" if rel else ""

    def html(m: re.Match) -> str:
        src = re.search(r'src\s*=\s*["\']([^"\']+)["\']', m.group(0), re.IGNORECASE)
        rel = local(src.group(1)) if src else None
        return f'<img src="{rel}">' if rel else ""

    # verlinkte Bilder [![…](bild)](link) zuerst, damit keine leeren Links übrig bleiben
    text = re.sub(r"\[(!\[[^\]]*\]\([^)]*\))\]\([^)]*\)", lambda m: m.group(1), text)
    text = _MD_IMAGE.sub(md, text)
    return _HTML_IMAGE.sub(html, text)
