"""Farben und Stylesheet (hell/dunkel, folgt auf Wunsch dem System)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

LIGHT = {
    "bg": "#f4f6f9",
    "surface": "#ffffff",
    "surface_alt": "#eef1f5",
    "border": "#dde2ea",
    "text": "#1c2430",
    "muted": "#5d6878",
    "accent": "#1f7a8c",
    "accent_hover": "#186473",
    "accent_text": "#ffffff",
    "ok": "#2e7d4f",
    "ok_bg": "#e3f3e9",
    "warn": "#9a6200",
    "warn_bg": "#fdf1dc",
    "danger": "#b3261e",
    "neutral_bg": "#e9edf2",
    "log_bg": "#f9fafb",
}

DARK = {
    "bg": "#14181e",
    "surface": "#1d232b",
    "surface_alt": "#252c36",
    "border": "#323b47",
    "text": "#e6eaf0",
    "muted": "#9aa5b4",
    "accent": "#3fb0c4",
    "accent_hover": "#5cc2d4",
    "accent_text": "#0d1216",
    "ok": "#6fd09a",
    "ok_bg": "#1e3a2b",
    "warn": "#f2c063",
    "warn_bg": "#3d3020",
    "danger": "#f2857d",
    "neutral_bg": "#2a313b",
    "log_bg": "#171c22",
}

# Kennfarben der Tool-Symbole (gut lesbar in beiden Modi)
TOOL_COLORS = ["#1f7a8c", "#7b4fb3", "#c0573b", "#2e7d4f", "#a8761a", "#3a62b8", "#b3407a"]


def system_is_dark() -> bool:
    hints = QGuiApplication.styleHints()
    scheme = getattr(hints, "colorScheme", None)
    if scheme is not None:
        value = scheme()
        if value == Qt.ColorScheme.Dark:
            return True
        if value == Qt.ColorScheme.Light:
            return False
    return QGuiApplication.palette().color(QPalette.Window).lightness() < 128


RESOURCES = Path(__file__).resolve().parent / "resources"


def colors(mode: str) -> dict[str, str]:
    dark = system_is_dark() if mode == "auto" else mode == "dark"
    c = dict(DARK if dark else LIGHT)
    variant = "dark" if dark else "light"
    c["_arrow"] = (RESOURCES / f"arrow-{variant}.svg").as_posix()
    c["_check"] = (RESOURCES / f"check-{variant}.svg").as_posix()
    return c


def apply(app: QApplication, mode: str) -> dict[str, str]:
    c = colors(mode)
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(c["bg"]))
    pal.setColor(QPalette.WindowText, QColor(c["text"]))
    pal.setColor(QPalette.Base, QColor(c["surface"]))
    pal.setColor(QPalette.AlternateBase, QColor(c["surface_alt"]))
    pal.setColor(QPalette.Text, QColor(c["text"]))
    pal.setColor(QPalette.Button, QColor(c["surface"]))
    pal.setColor(QPalette.ButtonText, QColor(c["text"]))
    pal.setColor(QPalette.Highlight, QColor(c["accent"]))
    pal.setColor(QPalette.HighlightedText, QColor(c["accent_text"]))
    pal.setColor(QPalette.ToolTipBase, QColor(c["surface"]))
    pal.setColor(QPalette.ToolTipText, QColor(c["text"]))
    pal.setColor(QPalette.PlaceholderText, QColor(c["muted"]))
    pal.setColor(QPalette.Link, QColor(c["accent"]))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor(c["muted"]))
    app.setPalette(pal)
    app.setStyleSheet(stylesheet(c))
    return c


def stylesheet(c: dict[str, str]) -> str:
    return f"""
    QWidget {{ font-size: 10pt; }}
    QMainWindow, QDialog {{ background: {c['bg']}; }}
    QToolTip {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
                padding: 4px 6px; }}

    #Header {{ background: {c['surface']}; border-bottom: 1px solid {c['border']}; }}
    #AppTitle {{ font-size: 17pt; font-weight: 700; color: {c['text']}; }}
    #AppSubtitle {{ color: {c['muted']}; }}

    #Card {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 10px; }}
    #Card[selected="true"] {{ border: 2px solid {c['accent']}; }}
    #ToolName {{ font-size: 13pt; font-weight: 650; color: {c['text']}; }}
    #ToolDesc, #Muted {{ color: {c['muted']}; }}
    #Hint {{ color: {c['warn']}; }}

    QLabel[chip="true"] {{ border-radius: 9px; padding: 2px 9px; font-size: 9pt; font-weight: 600; }}
    QLabel[kind="ok"] {{ background: {c['ok_bg']}; color: {c['ok']}; }}
    QLabel[kind="warn"] {{ background: {c['warn_bg']}; color: {c['warn']}; }}
    QLabel[kind="neutral"] {{ background: {c['neutral_bg']}; color: {c['muted']}; }}
    QLabel[kind="accent"] {{ background: {c['neutral_bg']}; color: {c['accent']}; }}

    QPushButton {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
                   border-radius: 6px; padding: 5px 12px; }}
    QPushButton:hover {{ background: {c['surface_alt']}; }}
    QPushButton:disabled {{ color: {c['muted']}; background: {c['surface_alt']}; }}
    QPushButton[primary="true"] {{ background: {c['accent']}; color: {c['accent_text']};
                                   border: 1px solid {c['accent']}; font-weight: 600; }}
    QPushButton[primary="true"]:hover {{ background: {c['accent_hover']}; }}
    QPushButton[primary="true"]:disabled {{ background: {c['surface_alt']}; color: {c['muted']};
                                            border: 1px solid {c['border']}; }}
    QPushButton[danger="true"] {{ color: {c['danger']}; }}
    QPushButton[flat="true"] {{ border: none; background: transparent; padding: 5px 8px; }}
    QPushButton[flat="true"]:hover {{ background: {c['surface_alt']}; }}
    QPushButton::menu-indicator {{ image: none; width: 0; }}

    QComboBox {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']};
                 border-radius: 6px; padding: 4px 10px; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox::down-arrow {{ image: url({c['_arrow']}); width: 10px; height: 6px; margin-right: 8px; }}
    QComboBox QAbstractItemView {{ background: {c['surface']}; color: {c['text']};
                                   selection-background-color: {c['accent']};
                                   selection-color: {c['accent_text']}; }}
    QCheckBox {{ color: {c['text']}; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border: 1.5px solid {c['muted']};
                            border-radius: 4px; background: {c['surface']}; }}
    QCheckBox::indicator:hover {{ border-color: {c['accent']}; }}
    QCheckBox::indicator:checked {{ background: {c['accent']}; border-color: {c['accent']};
                                    image: url({c['_check']}); }}
    QCheckBox::indicator:disabled {{ background: {c['surface_alt']}; border-color: {c['border']}; }}
    QMenu {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']}; }}
    QMenu::item {{ padding: 6px 18px; }}
    QMenu::item:selected {{ background: {c['accent']}; color: {c['accent_text']}; }}
    QMenu::separator {{ height: 1px; background: {c['border']}; margin: 4px 8px; }}

    QScrollArea, #CardList {{ background: transparent; border: none; }}
    #Banner {{ background: {c['warn_bg']}; color: {c['warn']}; border-radius: 8px; padding: 8px 12px; }}

    #ActivityBar {{ background: {c['surface']}; border-top: 1px solid {c['border']}; }}
    QPlainTextEdit#Log {{ background: {c['log_bg']}; color: {c['text']}; border: 1px solid {c['border']};
                          border-radius: 6px; font-family: monospace; font-size: 9pt; }}
    QProgressBar {{ background: {c['surface_alt']}; border: none; border-radius: 3px; max-height: 6px; }}
    QProgressBar::chunk {{ background: {c['accent']}; border-radius: 3px; }}

    QTreeView, QTextBrowser, QPlainTextEdit {{ background: {c['surface']}; color: {c['text']};
                                               border: 1px solid {c['border']}; border-radius: 6px; }}
    QTreeView::item:selected {{ background: {c['accent']}; color: {c['accent_text']}; }}
    QHeaderView::section {{ background: {c['surface_alt']}; color: {c['muted']}; border: none;
                            padding: 4px 6px; }}
    QSplitter::handle {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 3px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {c['border']}; border-radius: 3px; min-width: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    #InfoPanel {{ background: {c['surface']}; border: 1px solid {c['border']}; border-radius: 8px; }}
    #InfoKey {{ color: {c['muted']}; }}
    #Warning {{ background: {c['warn_bg']}; color: {c['warn']}; border-radius: 6px; padding: 6px 10px; }}
    """
