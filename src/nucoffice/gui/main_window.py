"""Hauptfenster: Übersicht aller Tools mit Aktionen."""

from __future__ import annotations

import sys
from datetime import datetime

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from .. import __version__, actions, docs, installer, process, staging
from ..paths import Scope, layout
from ..registry import Tool, load_registry
from ..sources import bundled
from ..state import State
from . import theme
from .cards import CardState, ToolCard
from .dialogs import DocsDialog, ReviewDialog, TextDialog
from .worker import Runner, Task

THEMES = [("auto", "Design: System"), ("light", "Design: Hell"), ("dark", "Design: Dunkel")]


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle("NucOffice")
        self.resize(1040, 760)
        self.setMinimumWidth(720)

        self.registry: dict[str, Tool] = {k: t for k, t in load_registry().items()}
        self.runner = Runner(self)
        self.busy: dict[str, str] = {}
        self.updates: dict[str, actions.UpdateInfo] = {}
        self.active_tasks = 0
        scope = Scope(settings.value("scope", Scope.USER.value))
        self.lay = layout(scope)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header(scope))

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 16, 24, 16)
        bl.setSpacing(12)
        self.banner = QLabel()
        self.banner.setObjectName("Banner")
        self.banner.setWordWrap(True)
        self.banner.hide()
        bl.addWidget(self.banner)

        list_widget = QWidget()
        list_widget.setObjectName("CardList")
        self.cards_layout = QVBoxLayout(list_widget)
        self.cards_layout.setContentsMargins(0, 0, 6, 0)
        self.cards_layout.setSpacing(12)
        self.cards: dict[str, ToolCard] = {}
        for i, (key, tool) in enumerate(self.registry.items()):
            card = ToolCard(tool, i)
            card.action.connect(self._on_action)
            card.selection_changed.connect(self._update_toolbar)
            self.cards[key] = card
            self.cards_layout.addWidget(card)
        self.cards_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(list_widget)
        scroll.viewport().setAutoFillBackground(False)
        list_widget.setAutoFillBackground(False)
        bl.addWidget(scroll, 1)
        root.addWidget(body, 1)
        root.addWidget(self._build_activity())
        self.setCentralWidget(central)

        geo = settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)
        self._scope_changed()
        QTimer.singleShot(400, lambda: self.check_updates(quiet=True))

    # ------------------------------------------------------------------ Aufbau
    def _build_header(self, scope: Scope) -> QWidget:
        header = QFrame()
        header.setObjectName("Header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 14, 24, 14)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        t = QLabel("NucOffice")
        t.setObjectName("AppTitle")
        s = QLabel("NC-Tools für die Nuklearchemie")
        s.setObjectName("AppSubtitle")
        titles.addWidget(t)
        titles.addWidget(s)
        hl.addLayout(titles)
        hl.addStretch(1)

        self.scope_box = QComboBox()
        self.scope_box.addItem("Nur für mich", Scope.USER.value)
        self.scope_box.addItem("Für alle Benutzer (Admin)", Scope.SYSTEM.value)
        self.scope_box.setCurrentIndex(0 if scope is Scope.USER else 1)
        self.scope_box.setToolTip("Wo die Tools installiert werden")
        self.scope_box.currentIndexChanged.connect(self._scope_changed)

        self.theme_box = QComboBox()
        for value, label in THEMES:
            self.theme_box.addItem(label, value)
        values = [v for v, _ in THEMES]
        current = self.settings.value("theme", "auto")
        self.theme_box.setCurrentIndex(values.index(current) if current in values else 0)
        self.theme_box.currentIndexChanged.connect(self._theme_changed)

        self.btn_updates = QPushButton("Nach Updates suchen")
        self.btn_updates.clicked.connect(lambda: self.check_updates(quiet=False))
        self.btn_batch = QPushButton("Auswahl installieren")
        self.btn_batch.setProperty("primary", True)
        self.btn_batch.clicked.connect(self._install_selected)
        for w in (self.scope_box, self.theme_box, self.btn_updates, self.btn_batch):
            hl.addWidget(w)
        return header

    def _build_activity(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("ActivityBar")
        vl = QVBoxLayout(bar)
        vl.setContentsMargins(24, 8, 24, 8)
        row = QHBoxLayout()
        self.activity = QLabel("Bereit.")
        self.activity.setObjectName("Muted")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(160)
        self.progress.hide()
        version = QLabel(f"NucOffice {__version__}")
        version.setObjectName("Muted")
        self.btn_log = QPushButton("Protokoll anzeigen")
        self.btn_log.setProperty("flat", True)
        self.btn_log.setCheckable(True)
        self.btn_log.toggled.connect(self._toggle_log)
        row.addWidget(self.activity, 1)
        row.addWidget(self.progress)
        row.addWidget(version)
        row.addWidget(self.btn_log)
        vl.addLayout(row)
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("Log")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        self.log_view.setFixedHeight(180)
        self.log_view.hide()
        vl.addWidget(self.log_view)
        return bar

    # ------------------------------------------------------------------ Zustand
    def refresh(self) -> None:
        state = State(self.lay.state_file)
        for key, card in self.cards.items():
            tool = self.registry[key]
            inst = state.get(key)
            upd = self.updates.get(key)
            if upd and (not inst or upd.installed.commit != inst.commit):
                upd = None  # veraltet (inzwischen neu installiert)
            card.update_view(CardState(
                installed=inst,
                running=process.status(key) is not None,
                update=upd,
                bundled=bundled.available(key),
                busy=self.busy.get(key),
                missing=tuple(installer.missing_system_requirements(tool)),
                has_log=process.log_file(key).exists(),
            ))
        self._update_toolbar()

    def _update_toolbar(self) -> None:
        n = sum(c.selected for c in self.cards.values())
        state = State(self.lay.state_file)
        sel = [k for k, c in self.cards.items() if c.selected]
        verb = "aktualisieren" if sel and all(state.get(k) for k in sel) else "installieren"
        self.btn_batch.setText(f"Auswahl {verb} ({n})" if n else "Auswahl installieren")
        self.btn_batch.setEnabled(n > 0)

    def log(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        for line in str(text).splitlines() or [""]:
            self.log_view.appendPlainText(f"[{stamp}] {line}")

    def _toggle_log(self, on: bool) -> None:
        self.log_view.setVisible(on)
        self.btn_log.setText("Protokoll ausblenden" if on else "Protokoll anzeigen")

    def _scope_changed(self) -> None:
        scope = Scope(self.scope_box.currentData())
        self.settings.setValue("scope", scope.value)
        self.lay = layout(scope)
        self.updates.clear()
        if scope is Scope.SYSTEM and not installer.can_write(self.lay):
            admin = "als Administrator" if sys.platform == "win32" else "mit Admin-Rechten (sudo)"
            self.banner.setText(
                f"Systemweite Installation nach {self.lay.root}: Dafür werden Admin-Rechte benötigt. "
                f"Bitte NucOffice {admin} starten, um hier zu installieren oder zu entfernen. "
                "Bereits installierte Tools lassen sich trotzdem starten.")
            self.banner.show()
        else:
            self.banner.hide()
        self.refresh()

    def _theme_changed(self) -> None:
        mode = self.theme_box.currentData()
        self.settings.setValue("theme", mode)
        theme.apply(QApplication.instance(), mode)

    # ------------------------------------------------------------------ Aufgaben
    def _run(self, key: str | None, busy_text: str, fn, *args, serial: bool,
             on_done=None, on_fail=None) -> None:
        task = Task(fn, *args)
        if key:
            self.busy[key] = busy_text
        self.active_tasks += 1
        self._activity(busy_text)
        task.signals.log.connect(self.log)

        def finish():
            if key:
                self.busy.pop(key, None)
            self.active_tasks -= 1
            if self.active_tasks == 0:
                self.progress.hide()
                self.activity.setText("Bereit.")
            self.refresh()

        def done(result):
            finish()
            if on_done:
                on_done(result)

        def failed(msg):
            finish()
            self.log(f"Fehler: {msg}")
            if on_fail:
                on_fail(msg)
            else:
                self._error(busy_text.rstrip(" …"), msg)

        task.signals.done.connect(done)
        task.signals.failed.connect(failed)
        self.runner.submit(task, serial=serial)
        self.refresh()

    def _activity(self, text: str) -> None:
        self.activity.setText(text)
        self.progress.show()

    def _error(self, what: str, msg: str) -> None:
        box = QMessageBox(QMessageBox.Warning, "NucOffice", f"{what} ist fehlgeschlagen.", parent=self)
        box.setInformativeText(msg)
        box.setDetailedText(self.log_view.toPlainText()[-4000:])
        box.exec()

    # ------------------------------------------------------------------ Aktionen
    def _on_action(self, key: str, action: str) -> None:
        tool = self.registry[key]
        handler = {
            "install": lambda: self.install(tool),
            "update": lambda: self.install(tool, reuse_staged=False),
            "install_bundled": lambda: self.install(tool, source="bundled", reuse_staged=False),
            "start": lambda: self.start(tool),
            "stop": lambda: self.stop(tool),
            "review": lambda: self.review(tool),
            "docs": lambda: self.show_docs(tool),
            "uninstall": lambda: self.uninstall(tool),
            "github": lambda: QDesktopServices.openUrl(QUrl(tool.repo_url)),
            "folder": lambda: staging.open_folder(self.lay.tool_dir(key)),
            "log": lambda: self.show_log(tool),
        }.get(action)
        if handler:
            handler()

    def _confirm_missing(self, tool: Tool) -> bool:
        missing = installer.missing_system_requirements(tool)
        if not missing:
            return True
        answer = QMessageBox.question(
            self, "Zusätzliche Programme benötigt",
            f"{tool.display_name} benötigt Programme, die auf diesem System nicht gefunden wurden:\n\n"
            f"    {', '.join(missing)}\n\nDiese müssen separat installiert werden "
            "(z. B. über die Paketverwaltung). Trotzdem installieren?")
        return answer == QMessageBox.Yes

    def install(self, tool: Tool, *, source: str = "auto", reuse_staged: bool = True,
                ask: bool = True) -> None:
        if not installer.can_write(self.lay):
            self._error("Installation", f"Keine Schreibrechte für {self.lay.root}.")
            return
        if ask and not self._confirm_missing(tool):
            return
        lay = self.lay
        verb = "aktualisiert" if State(lay.state_file).get(tool.key) else "installiert"

        def job(log):
            staged = actions.obtain(tool, lay, source, None, reuse_staged=reuse_staged, log=log)
            try:
                return installer.install(tool, staged.path, lay, source=staged.source,
                                         ref=staged.ref, commit=staged.commit, log=log)
            finally:
                staging.discard(tool, lay)

        self._run(tool.key, f"Wird {verb} …", job, serial=True)

    def _install_selected(self) -> None:
        keys = [k for k, c in self.cards.items() if c.selected]
        for key in keys:
            tool = self.registry[key]
            if not self._confirm_missing(tool):
                continue
            self.install(tool, reuse_staged=False, ask=False)
            self.cards[key].check.setChecked(False)

    def uninstall(self, tool: Tool) -> None:
        answer = QMessageBox.question(
            self, "Deinstallieren",
            f"{tool.display_name} wirklich deinstallieren?\n\nProgramm, Umgebung und Menüeintrag "
            "werden entfernt. Eigene Daten und Einstellungen des Tools bleiben erhalten.")
        if answer != QMessageBox.Yes:
            return
        lay = self.lay
        self._run(tool.key, "Wird deinstalliert …",
                  lambda log: installer.uninstall(tool, lay, log=log), serial=True)

    def start(self, tool: Tool) -> None:
        try:
            info = process.start(tool.key, installer.launch_command(tool, self.lay))
        except (installer.InstallError, RuntimeError, OSError) as exc:
            self._error(f"Start von {tool.display_name}", str(exc))
            return
        self.log(f"{tool.display_name} gestartet (PID {info.pid}).")
        self.refresh()
        QTimer.singleShot(2500, lambda: self._check_started(tool))

    def _check_started(self, tool: Tool) -> None:
        if process.status(tool.key) is None:
            log = process.log_file(tool.key)
            text = log.read_text(encoding="utf-8", errors="replace")[-3000:] if log.exists() else ""
            if text.strip():  # sofort wieder beendet und Ausgabe vorhanden → vermutlich Fehler
                self.log(f"{tool.display_name} hat sich gleich wieder beendet:\n{text}")
                self.btn_log.setChecked(True)
        self.refresh()

    def stop(self, tool: Tool) -> None:
        self._run(tool.key, "Wird beendet …", lambda log: process.stop(tool.key), serial=False)

    def review(self, tool: Tool) -> None:
        lay = self.lay

        def job(log):
            staged = actions.obtain(tool, lay, "auto", None, reuse_staged=False, log=log)
            return staged, staging.summarize(staged.path)

        def show(result):
            staged, summary = result
            inst = State(lay.state_file).get(tool.key)
            dlg = ReviewDialog(tool, staged, summary, inst,
                               can_install=tool.supported and installer.can_write(lay), parent=self)
            if dlg.exec():
                self.install(tool, reuse_staged=True)
            else:
                staging.discard(tool, lay)

        self._run(tool.key, "Code wird geladen …", job, serial=False, on_done=show)

    def show_docs(self, tool: Tool) -> None:
        lay = self.lay
        self._run(None, f"Dokumentation von {tool.display_name} wird geladen …",
                  lambda log: docs.load(tool, lay), serial=False,
                  on_done=lambda d: DocsDialog(tool, d, self).exec(),
                  on_fail=lambda msg: self._docs_failed(tool, msg))

    def _docs_failed(self, tool: Tool, msg: str) -> None:
        box = QMessageBox(QMessageBox.Information, "Dokumentation",
                          f"Die Dokumentation von {tool.display_name} konnte nicht geladen werden.",
                          parent=self)
        box.setInformativeText(msg)
        open_btn = box.addButton("Auf GitHub öffnen", QMessageBox.AcceptRole)
        box.addButton("Schließen", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl(f"{tool.repo_url}#readme"))

    def show_log(self, tool: Tool) -> None:
        path = process.log_file(tool.key)
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        TextDialog(f"Ausgabe des letzten Starts – {tool.display_name}",
                   text or "(keine Ausgabe)", self).exec()

    def check_updates(self, *, quiet: bool) -> None:
        state = State(self.lay.state_file)
        installed = [self.registry[k] for k in self.registry if state.get(k)]
        if not installed:
            if not quiet:
                QMessageBox.information(self, "Updates", "Es ist noch kein Tool installiert.")
            return
        lay, results, errors = self.lay, [], []
        pending = {"n": len(installed)}

        def one_done(tool, info=None, err=None):
            if info:
                self.updates[tool.key] = info
                results.append(info)
            if err:
                errors.append(f"{tool.display_name}: {err}")
            pending["n"] -= 1
            if pending["n"] == 0:
                avail = [r for r in results if r.available]
                self.log(f"Update-Prüfung: {len(avail)} Update(s) verfügbar."
                         + (f" Nicht prüfbar: {'; '.join(errors)}" if errors else ""))
                if not quiet:
                    if avail:
                        msg = f"{len(avail)} Update(s) verfügbar."
                    elif results:
                        msg = "Alle geprüften Tools sind aktuell."
                    else:
                        msg = "Es konnte kein Tool geprüft werden."
                    if errors:
                        msg += "\n\nNicht prüfbar:\n" + "\n".join(errors)
                    QMessageBox.information(self, "Updates", msg)
                self.refresh()

        for tool in installed:
            self._run(None, "Suche nach Updates …", lambda log, t=tool: actions.check_update(t, lay),
                      serial=False,
                      on_done=lambda info, t=tool: one_done(t, info=info),
                      on_fail=lambda msg, t=tool: one_done(t, err=msg))

    # ------------------------------------------------------------------ Beenden
    def closeEvent(self, event: QCloseEvent) -> None:
        if self.busy:
            answer = QMessageBox.question(
                self, "NucOffice beenden",
                "Es laufen noch Installationen. Warten, bis sie fertig sind, und dann beenden?")
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self._activity("Warte auf laufende Aufgaben …")
            self.runner.wait(10 * 60 * 1000)
        self.settings.setValue("geometry", self.saveGeometry())
        self.timer.stop()
        self.runner.wait(5000)  # kurze Abfragen (Updates, Doku) zu Ende laufen lassen
        event.accept()
