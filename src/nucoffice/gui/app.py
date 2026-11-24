"""Startpunkt der Oberfläche."""

from __future__ import annotations

import sys

from PySide6.QtCore import QLibraryInfo, QLocale, QSettings, QTranslator
from PySide6.QtWidgets import QApplication

from . import theme
from .main_window import MainWindow


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("NucOffice")
    app.setOrganizationName("NucOffice")
    app.setDesktopFileName("nucoffice")
    translator = QTranslator(app)  # deutsche Standardknöpfe (Ja/Nein/Schließen …)
    if translator.load(QLocale("de_DE"), "qtbase", "_",
                       QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
    settings = QSettings("NucOffice", "NucOffice")
    theme.apply(app, settings.value("theme", "auto"))
    window = MainWindow(settings)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
