"""Dialoge: Code ansehen, Dokumentation, Textanzeige."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QDir, QModelIndex, Qt, QUrl
from PySide6.QtGui import (
    QDesktopServices, QFont, QFontDatabase, QImage, QPixmap, QTextCursor, QTextDocument,
)
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileSystemModel, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QSplitter, QTextBrowser, QTreeView, QVBoxLayout, QWidget,
)

from .. import staging
from ..actions import short
from ..docs import Docs
from ..registry import Tool
from ..state import InstalledTool

MAX_VIEW_BYTES = 1_000_000


def _fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return ""


def _mono() -> QFont:
    f = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    f.setPointSize(max(9, f.pointSize()))
    return f


def _open_url(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


class ReviewDialog(QDialog):
    """Zeigt den geladenen (nicht ausgeführten) Code. Akzeptieren = diesen Stand installieren."""

    def __init__(self, tool: Tool, staged: staging.Staged, summary: staging.Summary,
                 installed: InstalledTool | None, can_install: bool, parent: QWidget | None = None):
        super().__init__(parent)
        self.staged = staged
        self.setWindowTitle(f"Code ansehen – {tool.display_name}")
        self.resize(1100, 720)

        origin = "mitgelieferte Version" if staged.source == "bundled" else "GitHub"
        title = QLabel(f"{tool.display_name} · {staged.ref}")
        title.setObjectName("ToolName")
        sub = QLabel(f"{short(staged.commit)} · Quelle: {origin} · Der Code wurde nur geladen, "
                     "nicht ausgeführt.")
        sub.setObjectName("Muted")
        sub.setWordWrap(True)

        # --- Überblick ---------------------------------------------------
        info = QFrame()
        info.setObjectName("InfoPanel")
        form = QFormLayout(info)
        form.setContentsMargins(14, 12, 14, 12)
        form.setLabelAlignment(Qt.AlignLeft)

        def row(key: str, value: str) -> None:
            k = QLabel(key)
            k.setObjectName("InfoKey")
            v = QLabel(value or "–")
            v.setWordWrap(True)
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addRow(k, v)

        s = summary
        row("Paket", f"{s.name or '(aus setup.py)'} {s.version or ''}".strip())
        row("Python", s.requires_python or "?")
        row("Dateien", f"{s.file_count} ({s.python_files} Python) · {_fmt_size(s.size_bytes)}")
        row("Abhängigkeiten", ", ".join(s.dependencies) or "keine")
        for extra in tool.extras:
            row(f"Zusatz [{extra}]", ", ".join(s.optional.get(extra, [])))
        row("Startbefehle", ", ".join(s.entry_points) or "keine")
        if installed:
            same = installed.commit and installed.commit == staged.commit
            row("Installiert", f"{installed.version}" + (" (genau dieser Stand)" if same else ""))
        warn = None
        if s.build_hooks:
            warn = QLabel("Achtung: Beim Installieren wird Code aus " + ", ".join(s.build_hooks)
                          + " ausgeführt – diese Dateien besonders prüfen.")
            warn.setObjectName("Warning")
            warn.setWordWrap(True)

        # --- Dateien + Inhalt --------------------------------------------
        self.model = QFileSystemModel(self)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Hidden)
        root = self.model.setRootPath(str(staged.path))
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(root)
        for col in (1, 2, 3):
            self.tree.hideColumn(col)
        self.tree.setHeaderHidden(True)
        self.tree.clicked.connect(self._show_file)
        self.tree.activated.connect(self._show_file)

        self.file_label = QLabel("Datei links auswählen, um sie anzusehen.")
        self.file_label.setObjectName("Muted")
        self.viewer = QPlainTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setFont(_mono())
        self.viewer.setLineWrapMode(QPlainTextEdit.NoWrap)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(self.file_label)
        rl.addWidget(self.viewer, 1)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(info)
        if warn:
            ll.addWidget(warn)
        ll.addWidget(self.tree, 1)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([380, 720])

        # --- Knöpfe -------------------------------------------------------
        buttons = QHBoxLayout()
        if staged.browse_url:
            b = QPushButton("Auf GitHub ansehen")
            b.clicked.connect(lambda: _open_url(staged.browse_url))
            buttons.addWidget(b)
        if installed and installed.commit and staged.commit and installed.commit != staged.commit:
            b = QPushButton("Änderungen seit installierter Version")
            b.clicked.connect(lambda: _open_url(staged.compare_url(installed.commit)))
            buttons.addWidget(b)
        b = QPushButton("Im Dateimanager öffnen")
        b.clicked.connect(lambda: staging.open_folder(staged.path))
        buttons.addWidget(b)
        buttons.addStretch(1)
        close = QPushButton("Schließen")
        close.clicked.connect(self.reject)
        buttons.addWidget(close)
        self.install_btn = QPushButton("Diesen Stand installieren")
        self.install_btn.setProperty("primary", True)
        self.install_btn.setEnabled(can_install)
        self.install_btn.clicked.connect(self.accept)
        buttons.addWidget(self.install_btn)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.addWidget(title)
        lay.addWidget(sub)
        lay.addSpacing(6)
        lay.addWidget(split, 1)
        lay.addLayout(buttons)

        readme = staged.path / "README.md"
        if readme.exists():
            self._load(readme)

    def _show_file(self, index: QModelIndex) -> None:
        path = Path(self.model.filePath(index))
        if path.is_file():
            self._load(path)

    def _load(self, path: Path) -> None:
        rel = path.relative_to(self.staged.path).as_posix()
        size = path.stat().st_size
        self.file_label.setText(f"{rel} · {_fmt_size(size)}")
        if size > MAX_VIEW_BYTES:
            self.viewer.setPlainText("(Datei zu groß für die Vorschau – bitte im Dateimanager öffnen.)")
            return
        data = path.read_bytes()
        if b"\0" in data[:4096]:
            self.viewer.setPlainText("(Binärdatei – keine Textvorschau.)")
            return
        self.viewer.setPlainText(data.decode("utf-8", errors="replace"))


def _as_image(res) -> QImage | None:
    if isinstance(res, QImage):
        return res
    if isinstance(res, QPixmap):
        return res.toImage()
    if isinstance(res, (bytes, bytearray, QByteArray)):
        return QImage.fromData(res)
    return None


class DocsDialog(QDialog):
    def __init__(self, tool: Tool, docs: Docs, parent: QWidget | None = None):
        super().__init__(parent)
        self.docs, self.tool = docs, tool
        self.setWindowTitle(f"Dokumentation – {tool.display_name}")
        self.resize(900, 760)

        title = QLabel(f"{tool.display_name} – Dokumentation")
        title.setObjectName("ToolName")
        origin = QLabel(f"Quelle: {docs.origin}")
        origin.setObjectName("Muted")

        self.pages = QComboBox()
        self.pages.setVisible(len(docs.pages) > 1)
        if docs.pages:
            self.pages.addItems(docs.pages)
            self.pages.setCurrentText(tool.docs)
            self.pages.currentTextChanged.connect(self._load_page)

        top = QHBoxLayout()
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.pages)

        self.view = QTextBrowser()
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(self._link)
        self.view.document().setDocumentMargin(18)

        buttons = QHBoxLayout()
        buttons.addWidget(origin)
        buttons.addStretch(1)
        if docs.web_url:
            web = QPushButton("Im Browser öffnen")
            web.clicked.connect(lambda: _open_url(docs.web_url))
            buttons.addWidget(web)
        close = QPushButton("Schließen")
        close.setProperty("primary", True)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.addLayout(top)
        lay.addWidget(self.view, 1)
        lay.addLayout(buttons)
        self._current = tool.docs
        self._show(docs.text)

    def _show(self, text: str) -> None:
        if self.docs.base:
            page_dir = (self.docs.base / self._current).parent
            self.view.setSearchPaths([str(page_dir), str(self.docs.base)])
        self.view.setMarkdown(text)
        self._fit_images()

    def _fit_images(self) -> None:
        """Große Bilder auf die Fensterbreite verkleinern (QTextBrowser skaliert nicht selbst)."""
        doc = self.view.document()
        max_w = max(200, self.view.viewport().width() - 2 * int(doc.documentMargin()) - 8)
        block = doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                fmt = frag.charFormat()
                if fmt.isImageFormat():
                    img_fmt = fmt.toImageFormat()
                    res = self.view.loadResource(QTextDocument.ImageResource, QUrl(img_fmt.name()))
                    img = _as_image(res)
                    if img is not None and not img.isNull() and img.width() > max_w:
                        img_fmt.setWidth(max_w)
                        img_fmt.setHeight(img.height() * max_w / img.width())
                        cur = QTextCursor(doc)
                        cur.setPosition(frag.position())
                        cur.setPosition(frag.position() + frag.length(), QTextCursor.KeepAnchor)
                        cur.setCharFormat(img_fmt)
                it += 1
            block = block.next()

    def showEvent(self, event) -> None:  # Breite steht erst beim Anzeigen fest
        super().showEvent(event)
        self._fit_images()

    def _load_page(self, rel: str) -> None:
        if not self.docs.base:
            return
        path = self.docs.base / rel
        if path.is_file():
            self._current = rel
            self._show(path.read_text(encoding="utf-8"))

    def _link(self, url: QUrl) -> None:
        if url.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)
            return
        if url.toString().startswith("#"):
            self.view.scrollToAnchor(url.fragment())
            return
        if self.docs.base:
            target = ((self.docs.base / self._current).parent / url.path()).resolve()
            try:
                rel = target.relative_to(self.docs.base.resolve()).as_posix()
            except ValueError:
                return
            if rel.endswith(".md") and target.is_file():
                if rel in self.docs.pages:
                    self.pages.setCurrentText(rel)
                else:
                    self._load_page(rel)
            elif target.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))


class TextDialog(QDialog):
    def __init__(self, title: str, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 520)
        view = QPlainTextEdit(text)
        view.setReadOnly(True)
        view.setFont(_mono())
        close = QPushButton("Schließen")
        close.clicked.connect(self.accept)
        lay = QVBoxLayout(self)
        lay.addWidget(view, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        lay.addLayout(row)
