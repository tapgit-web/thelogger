"""
main.py  —  THE LOGGER PyQt6 Application Entry Point
Run from this directory:  python main.py
"""

import sys
import os

# NOTE: Do NOT call SetProcessDpiAwareness manually — Qt6 already sets
# DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 before Python code runs.
# Attempting to override it causes an "Access is denied" error.

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase

from logger_app.ui.auth_views import show_login_flow
from logger_app.backend.core import resource_path


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("THE LOGGER")
    app.setOrganizationName("The Automation People")
    app.setApplicationVersion("2.5.0")

    # Load custom fonts
    f1 = resource_path(os.path.join("fonts", "JosefinSans-VariableFont_wght.ttf"))
    f2 = resource_path(os.path.join("fonts", "Buongiorno Rastellino.otf"))
    if os.path.exists(f1):
        QFontDatabase.addApplicationFont(f1)
    if os.path.exists(f2):
        QFontDatabase.addApplicationFont(f2)

    # ── Professional font stack ──────────────────────────────────────
    # User requested Josefin Sans as the primary font and Buongiorno Rastellino for logos
    ui_font = QFont("Josefin Sans", 10, QFont.Weight.Normal)
    ui_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(ui_font)

    # ── Load stylesheet ──────────────────────────────────────────────
    qss_path = resource_path(
        os.path.join("logger_app", "ui", "styles.qss")
    )
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    # ── Launch ───────────────────────────────────────────────────────
    show_login_flow()


if __name__ == "__main__":
    main()
