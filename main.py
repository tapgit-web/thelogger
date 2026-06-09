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
from PyQt6.QtGui import QFont

from logger_app.ui.auth_views import show_login_flow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("THE LOGGER")
    app.setOrganizationName("The Automation People")
    app.setApplicationVersion("2.0.0")

    # ── Professional font stack ──────────────────────────────────────
    # Segoe UI is the Windows system font; set it explicitly so it's
    # applied before any stylesheet rules.
    ui_font = QFont("Segoe UI", 10, QFont.Weight.Normal)
    ui_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(ui_font)

    # ── Load stylesheet ──────────────────────────────────────────────
    qss_path = os.path.join(
        os.path.dirname(__file__), "logger_app", "ui", "styles.qss"
    )
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    # ── Launch ───────────────────────────────────────────────────────
    show_login_flow()


if __name__ == "__main__":
    main()
