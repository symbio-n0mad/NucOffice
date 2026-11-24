"""Eine Karte pro Tool: Name, Status, Aktionen."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ..actions import UpdateInfo
from ..registry import Tool
from ..sources.bundled import BundledTool
from ..state import InstalledTool
from .theme import TOOL_COLORS


@dataclass
class CardState:
    installed: InstalledTool | None = None
    running: bool = False
    update: UpdateInfo | None = None
    bundled: BundledTool | None = None
    busy: str | None = None  # z. B. "Wird installiert …"
    missing: tuple[str, ...] = ()  # fehlende Systemprogramme
    has_log: bool = False


def initials(name: str) -> str:
    caps = [c for c in name if c.isupper()]
    if name and name[0].islower():
        caps.insert(0, name[0].upper())
    return ("".join(caps) or name[:2].upper())[:2]


def _chip(text: str, kind: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("chip", True)
    label.setProperty("kind", kind)
    return label


def _button(text: str, *, primary=False, danger=False, flat=False, tip: str = "") -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    b.setProperty("primary", primary)
    b.setProperty("danger", danger)
    b.setProperty("flat", flat)
    if tip:
        b.setToolTip(tip)
    return b


class ToolCard(QFrame):
    action = Signal(str, str)  # (tool key, aktion)
    selection_changed = Signal()

    def __init__(self, tool: Tool, index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.tool = tool
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.check = QCheckBox()
        self.check.setToolTip("Für „Auswahl installieren/aktualisieren“ markieren")
        self.check.toggled.connect(self._on_check)

        avatar = QLabel(initials(tool.display_name))
        avatar.setFixedSize(44, 44)
        avatar.setAlignment(Qt.AlignCenter)
        color = TOOL_COLORS[index % len(TOOL_COLORS)]
        avatar.setStyleSheet(f"background:{color}; color:white; border-radius:22px;"
                             "font-weight:700; font-size:12pt;")

        self.name = QLabel(tool.display_name)
        self.name.setObjectName("ToolName")
        self.version = QLabel()
        self.version.setObjectName("Muted")
        self.desc = QLabel(tool.description)
        self.desc.setObjectName("ToolDesc")
        self.desc.setWordWrap(True)
        self.hint = QLabel()
        self.hint.setObjectName("Hint")
        self.hint.setWordWrap(True)

        self.chips = QHBoxLayout()
        self.chips.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title_row.addWidget(self.name)
        title_row.addWidget(self.version)
        title_row.addStretch(1)
        title_row.addLayout(self.chips)

        self.btn_main = _button("Installieren", primary=True)
        self.btn_main.clicked.connect(lambda: self.action.emit(tool.key, self._main_action))
        self.btn_update = _button("Aktualisieren", primary=True,
                                  tip="Neueste Version von GitHub installieren")
        self.btn_update.clicked.connect(lambda: self.action.emit(tool.key, "update"))
        self.btn_review = _button("Code ansehen", tip="Code laden und prüfen, ohne ihn auszuführen")
        self.btn_review.clicked.connect(lambda: self.action.emit(tool.key, "review"))
        self.btn_docs = _button("Dokumentation", tip="Lesen, was das Tool kann – auch vor der Installation")
        self.btn_docs.clicked.connect(lambda: self.action.emit(tool.key, "docs"))
        self.btn_more = _button("Mehr ▾", flat=True)
        self.menu = QMenu(self)
        self.btn_more.setMenu(self.menu)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        for b in (self.btn_main, self.btn_update, self.btn_review, self.btn_docs):
            buttons.addWidget(b)
        buttons.addStretch(1)
        self.busy = QLabel()
        self.busy.setObjectName("Muted")
        buttons.addWidget(self.busy)
        buttons.addWidget(self.btn_more)

        text = QVBoxLayout()
        text.setSpacing(4)
        text.addLayout(title_row)
        text.addWidget(self.desc)
        text.addWidget(self.hint)
        text.addSpacing(6)
        text.addLayout(buttons)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(14)
        row.addWidget(self.check, 0, Qt.AlignTop)
        row.addWidget(avatar, 0, Qt.AlignTop)
        row.addLayout(text, 1)
        self._main_action = "install"

    # ------------------------------------------------------------------
    @property
    def selected(self) -> bool:
        return self.check.isChecked()

    def _on_check(self, on: bool) -> None:
        self.setProperty("selected", on)
        self.style().unpolish(self)
        self.style().polish(self)
        self.selection_changed.emit()

    def _set_chips(self, chips: list[tuple[str, str]]) -> None:
        if chips == getattr(self, "_chips", None):
            return  # unverändert – nicht flackern lassen
        self._chips = chips
        while self.chips.count():
            w = self.chips.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        for text, kind in chips:
            self.chips.addWidget(_chip(text, kind))

    def update_view(self, st: CardState) -> None:
        tool, inst = self.tool, st.installed
        supported = tool.supported
        update_ready = bool(inst and st.update and st.update.available)

        self.version.setText(f"Version {inst.version}" if inst else "")
        chips: list[tuple[str, str]] = []
        if not supported:
            chips.append(("Nur Linux" if tool.platforms == ("linux",) else "Nicht verfügbar", "neutral"))
        elif st.running:
            chips.append(("Läuft", "ok"))
        if update_ready:
            chips.append((f"Update: {st.update.latest_ref}", "warn"))
        if inst:
            chips.append(("Installiert", "accent"))
        elif supported:
            chips.append(("Nicht installiert", "neutral"))
        if not inst and st.bundled and supported:
            chips.append(("Offline verfügbar", "neutral"))
        self._set_chips(chips)

        hints = []
        if st.missing and supported:
            hints.append("Benötigt zusätzlich: " + ", ".join(st.missing))
        self.hint.setText(" · ".join(hints))
        self.hint.setVisible(bool(hints))

        if not supported:
            self._main_action, label = "none", "Nicht verfügbar"
        elif not inst:
            self._main_action, label = "install", "Installieren"
        elif st.running:
            self._main_action, label = "stop", "Beenden"
        else:
            self._main_action, label = "start", "Starten"
        self.btn_main.setText(label)
        self.btn_main.setProperty("primary", self._main_action in ("install", "start"))
        self.btn_main.style().unpolish(self.btn_main)
        self.btn_main.style().polish(self.btn_main)
        self.btn_update.setVisible(update_ready)

        busy = st.busy is not None
        self.busy.setText(st.busy or "")
        self.btn_main.setEnabled(not busy and supported)
        self.btn_update.setEnabled(not busy)
        self.btn_review.setEnabled(not busy)
        self.check.setEnabled(supported)
        if not supported:
            self.check.setChecked(False)

        self.menu.clear()
        if inst and supported:
            self.menu.addAction("Neu installieren (neueste Version)",
                                lambda: self.action.emit(tool.key, "update")).setEnabled(not busy)
        if st.bundled and supported:
            v = st.bundled.version or st.bundled.ref
            self.menu.addAction(f"Mitgelieferte Version {v} installieren",
                                lambda: self.action.emit(tool.key, "install_bundled")).setEnabled(not busy)
        self.menu.addAction("Auf GitHub öffnen", lambda: self.action.emit(tool.key, "github"))
        if inst:
            self.menu.addAction("Installationsordner öffnen", lambda: self.action.emit(tool.key, "folder"))
        if st.has_log:
            self.menu.addAction("Ausgabe des letzten Starts", lambda: self.action.emit(tool.key, "log"))
        if inst:
            self.menu.addSeparator()
            self.menu.addAction("Deinstallieren …",
                                lambda: self.action.emit(tool.key, "uninstall")).setEnabled(not busy)
