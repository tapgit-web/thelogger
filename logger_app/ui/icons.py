"""
icons.py  —  Centralised icon factory using qtawesome (Font Awesome 5).

Usage:
    from .icons import icon, btn_icon
    button.setIcon(icon("fa5s.play"))
    button.setIcon(btn_icon("start"))   # semantic alias
"""

import qtawesome as qta
from PyQt6.QtGui import QIcon, QColor

# ── Brand palette ─────────────────────────────────────────────────────
BRAND_PRIMARY = "#10B981"  # TAP Emerald Green
RED       = "#D32F2F"
DARK      = "#1C1E21"
DIM       = "#65676B"
WHITE     = "#FFFFFF"
GREEN     = "#28A745"
ORANGE    = "#F29900"
BLUE      = "#2196F3"

# ── Low-level helper ──────────────────────────────────────────────────
def icon(name: str, color: str = DARK, size: int = 16) -> QIcon:
    """Return a coloured QIcon for the given Font Awesome icon name."""
    try:
        return qta.icon(name, color=color, scale_factor=1.0)
    except Exception:
        return QIcon()                  # graceful fallback


# ── Semantic aliases (used across the whole app) ───────────────────────
_ALIASES = {
    # Navigation
    "dashboard":    ("fa5s.tachometer-alt",  DIM),
    "device_mgr":   ("fa5s.microchip",        DIM),
    "live_log":     ("fa5s.list-alt",          DIM),
    "alarm_cfg":    ("fa5s.bell",              DIM),
    "export":       ("fa5s.file-export",       DIM),
    "trends":       ("fa5s.chart-area",        DIM),
    "users":        ("fa5s.users",             DIM),

    # Actions
    "start":        ("fa5s.play",              GREEN),
    "stop":         ("fa5s.stop",              RED),
    "refresh":      ("fa5s.sync-alt",          DIM),
    "save":         ("fa5s.save",              WHITE),
    "new":          ("fa5s.plus",              WHITE),
    "edit":         ("fa5s.edit",              ORANGE),
    "delete":       ("fa5s.trash-alt",         WHITE),
    "download":     ("fa5s.download",          WHITE),
    "upload":       ("fa5s.upload",            WHITE),
    "back":         ("fa5s.arrow-left",        DIM),
    "folder":       ("fa5s.folder-open",       ORANGE),
    "email":        ("fa5s.envelope",          BLUE),
    "pdf":          ("fa5s.file-pdf",          RED),
    "alarm_hist":   ("fa5s.history",           ORANGE),
    "logout":       ("fa5s.sign-out-alt",      WHITE),
    "test_email":   ("fa5s.paper-plane",       DIM),
    "lock":         ("fa5s.lock",              RED),
    "user":         ("fa5s.user-circle",       DIM),
    "settings":     ("fa5s.cogs",              DIM),
    "check":        ("fa5s.check",             GREEN),
    "warning":      ("fa5s.exclamation-triangle", ORANGE),
    "info":         ("fa5s.info-circle",       BLUE),
    "add_rule":     ("fa5s.plus-circle",       WHITE),
    "activate":     ("fa5s.key",               WHITE),
    "authenticate": ("fa5s.sign-in-alt",       WHITE),
    "chart_line":   ("fa5s.chart-line",        BRAND_PRIMARY),
    "all":          ("fa5s.check-double",      DIM),
    "start_all":    ("fa5s.play-circle",       WHITE),
    "stop_all":     ("fa5s.stop-circle",       WHITE),
}

def btn_icon(alias: str) -> QIcon:
    """Return a QIcon by semantic alias name."""
    if alias not in _ALIASES:
        return QIcon()
    fa_name, color = _ALIASES[alias]
    return icon(fa_name, color)


def nav_icon(alias: str, active: bool = False) -> QIcon:
    """Navigation sidebar icon – primary brand color when active, dim otherwise."""
    if alias not in _ALIASES:
        return QIcon()
    fa_name, _ = _ALIASES[alias]
    color = BRAND_PRIMARY if active else DIM
    return icon(fa_name, color)
