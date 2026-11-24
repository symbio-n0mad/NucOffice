"""Länger laufende Aufgaben (Download, pip, GitHub-Abfragen) im Hintergrund ausführen."""

from __future__ import annotations

import traceback
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _Signals(QObject):
    log = Signal(str)
    done = Signal(object)
    failed = Signal(str)


class Task(QRunnable):
    """Führt ``fn(log, *args)`` in einem Hintergrund-Thread aus.

    ``log`` ist eine Funktion, deren Ausgaben thread-sicher als Signal ankommen.
    """

    def __init__(self, fn: Callable[..., Any], *args: Any):
        super().__init__()
        self.fn, self.args = fn, args
        self.signals = _Signals()
        self.setAutoDelete(False)  # Lebensdauer verwaltet der Runner

    def _emit(self, signal: str, *args: Any) -> None:
        try:
            getattr(self.signals, signal).emit(*args)
        except RuntimeError:
            pass  # Fenster wurde inzwischen geschlossen – niemand hört mehr zu

    def run(self) -> None:
        try:
            result = self.fn(lambda text: self._emit("log", text), *self.args)
        except Exception as exc:  # noqa: BLE001 – alles an die Oberfläche melden
            if not isinstance(exc, OSError):  # erwartete Fehler (Netz, Dateien) ohne Traceback
                self._emit("log", traceback.format_exc().rstrip())
            self._emit("failed", str(exc) or exc.__class__.__name__)
        else:
            self._emit("done", result)


class Runner(QObject):
    """Zwei Warteschlangen: Installationen nacheinander, kurze Abfragen parallel."""

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.serial = QThreadPool(self)
        self.serial.setMaxThreadCount(1)
        self.parallel = QThreadPool(self)
        self.parallel.setMaxThreadCount(4)
        self._alive: set[Task] = set()  # Python-Objekte (und ihre Signale) am Leben halten

    def submit(self, task: Task, *, serial: bool) -> Task:
        self._alive.add(task)
        release = lambda *_: self._alive.discard(task)  # noqa: E731
        task.signals.done.connect(release)
        task.signals.failed.connect(release)
        (self.serial if serial else self.parallel).start(task)
        return task

    def wait(self, msecs: int = 30000) -> None:
        self.serial.waitForDone(msecs)
        self.parallel.waitForDone(msecs)
