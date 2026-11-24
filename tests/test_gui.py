"""Rauchtest der Oberfläche (ohne Bildschirm, ohne Netz)."""

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture
def window(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("NUCOFFICE_BUNDLED", str(tmp_path / "bundled"))
    from nucoffice.gui import theme
    from nucoffice.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    theme.apply(app, "light")
    MainWindow.check_updates = lambda self, quiet: None  # kein Netz im Test
    w = MainWindow(QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    yield w
    w.timer.stop()
    w.close()


def test_cards_for_all_tools(window):
    assert set(window.cards) == set(window.registry)
    card = window.cards["activitypartitioner"]
    assert card.btn_main.text() == "Installieren"
    assert not card.btn_update.isVisibleTo(window)


def test_selection_updates_batch_button(window):
    assert not window.btn_batch.isEnabled()
    window.cards["plotrde"].check.setChecked(True)
    assert window.btn_batch.isEnabled() and "(1)" in window.btn_batch.text()


def test_dark_theme_applies(window):
    from nucoffice.gui import theme

    c = theme.apply(QApplication.instance(), "dark")
    assert c["bg"] == theme.DARK["bg"] and os.path.exists(c["_arrow"])
