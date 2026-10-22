"""Professional Dark Engineering Workstation Theme and Design Tokens.

Inspired by Bloomberg Terminal, IDA Pro, Wireshark, Datadog, and modern IDEs:
high legibility, low glare, precise 1px borders, subtle tonal hierarchy.
"""

from __future__ import annotations

# Design Tokens
COLORS = {
    "bg_root": "#0a0d14",
    "bg_sidebar": "#080b10",
    "bg_workspace": "#0d111a",
    "bg_panel": "#111622",
    "bg_panel_alt": "#141b29",
    "bg_input": "#090c12",
    "bg_hover": "#1a2233",
    "bg_active": "#222c42",
    "bg_selected": "#172338",
    "border_subtle": "#1e2638",
    "border_medium": "#2a354c",
    "border_focus": "#38bdf8",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "text_disabled": "#475569",
    "accent_cyan": "#0ea5e9",
    "accent_cyan_glow": "#38bdf8",
    "accent_blue": "#2563eb",
    "success": "#10b981",
    "success_bg": "#064e3b",
    "warning": "#f59e0b",
    "warning_bg": "#78350f",
    "error": "#ef4444",
    "error_bg": "#7f1d1d",
    "inferred": "#d97706",
    "observed": "#059669",
    "simulated": "#2563eb",
}

DARK_ENGINEERING_THEME = """
/* Global Base */
QWidget {
    background-color: #0d111a;
    color: #f1f5f9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 12px;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}

QMainWindow {
    background-color: #0a0d14;
}

/* Toolbars & Bars */
QToolBar {
    background-color: #080b10;
    border-bottom: 1px solid #1e2638;
    spacing: 6px;
    padding: 3px 8px;
}

QStatusBar {
    background-color: #080b10;
    border-top: 1px solid #1e2638;
    color: #94a3b8;
    font-size: 11px;
}

/* Splitters */
QSplitter::handle {
    background-color: #1e2638;
}
QSplitter::handle:horizontal {
    width: 1px;
}
QSplitter::handle:vertical {
    height: 1px;
}
QSplitter::handle:hover {
    background-color: #0ea5e9;
}

/* Sidebar Navigation */
QListWidget#sidebarNav {
    background-color: #080b10;
    border: none;
    border-right: 1px solid #1e2638;
    padding: 4px 0px;
    outline: none;
}

QListWidget#sidebarNav::item {
    height: 32px;
    padding-left: 14px;
    margin: 1px 6px;
    border-radius: 4px;
    color: #94a3b8;
    font-weight: 500;
}

QListWidget#sidebarNav::item:hover {
    background-color: #141b29;
    color: #f1f5f9;
}

QListWidget#sidebarNav::item:selected {
    background-color: #172338;
    color: #38bdf8;
    font-weight: 600;
    border-left: 2px solid #38bdf8;
}

/* Group Boxes / Panels */
QGroupBox {
    background-color: #111622;
    border: 1px solid #1e2638;
    border-radius: 4px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #94a3b8;
    background-color: #111622;
}

/* Buttons */
QPushButton {
    background-color: #1a2233;
    border: 1px solid #2a354c;
    border-radius: 3px;
    color: #f1f5f9;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #222c42;
    border-color: #38bdf8;
}

QPushButton:pressed {
    background-color: #0ea5e9;
    border-color: #0284c7;
    color: #ffffff;
}

QPushButton:disabled {
    background-color: #0d111a;
    border-color: #1e2638;
    color: #475569;
}

QPushButton#btnPrimary {
    background-color: #0284c7;
    border-color: #38bdf8;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#btnPrimary:hover {
    background-color: #0369a1;
}

QPushButton#btnSuccess {
    background-color: #047857;
    border-color: #10b981;
    color: #ffffff;
}
QPushButton#btnSuccess:hover {
    background-color: #065f46;
}

QPushButton#btnDanger {
    background-color: #991b1b;
    border-color: #ef4444;
    color: #ffffff;
}
QPushButton#btnDanger:hover {
    background-color: #7f1d1d;
}

QPushButton#btnGhost {
    background-color: transparent;
    border: 1px solid transparent;
    color: #94a3b8;
}
QPushButton#btnGhost:hover {
    background-color: #141b29;
    color: #f1f5f9;
    border-color: #1e2638;
}

/* Tables */
QTableWidget, QTableView {
    background-color: #090c12;
    border: 1px solid #1e2638;
    gridline-color: #141b29;
    border-radius: 3px;
    outline: none;
    font-family: "SF Mono", "Cascadia Code", "JetBrains Mono", Consolas, monospace;
    font-size: 11px;
}

QTableWidget::item, QTableView::item {
    padding: 4px 6px;
    border-bottom: 1px solid #141b29;
}

QTableWidget::item:selected, QTableView::item:selected {
    background-color: #172338;
    color: #38bdf8;
}

QHeaderView::section {
    background-color: #111622;
    color: #94a3b8;
    padding: 5px 6px;
    border: none;
    border-bottom: 1px solid #1e2638;
    border-right: 1px solid #1e2638;
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Inputs & Form Controls */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #090c12;
    border: 1px solid #1e2638;
    border-radius: 3px;
    padding: 4px 8px;
    color: #f1f5f9;
    font-family: "SF Mono", "Cascadia Code", Consolas, monospace;
    font-size: 12px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #38bdf8;
    background-color: #0d111a;
}

QComboBox::drop-down {
    border: none;
    width: 18px;
}

QComboBox QAbstractItemView {
    background-color: #111622;
    border: 1px solid #2a354c;
    color: #f1f5f9;
    selection-background-color: #172338;
    selection-color: #38bdf8;
}

/* Text Editors & Logs */
QTextEdit, QPlainTextEdit {
    background-color: #080b10;
    border: 1px solid #1e2638;
    border-radius: 3px;
    color: #e2e8f0;
    font-family: "SF Mono", "Cascadia Code", "JetBrains Mono", Consolas, monospace;
    font-size: 11px;
    padding: 6px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #080b10;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #1e2638;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #2a354c;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background-color: #080b10;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: #1e2638;
    border-radius: 4px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #2a354c;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Tab Widgets */
QTabWidget::pane {
    border: 1px solid #1e2638;
    background-color: #0d111a;
    border-radius: 3px;
}

QTabBar::tab {
    background-color: #080b10;
    color: #94a3b8;
    border: 1px solid #1e2638;
    border-bottom: none;
    padding: 5px 12px;
    margin-right: 2px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    font-size: 11px;
}

QTabBar::tab:selected {
    background-color: #111622;
    color: #38bdf8;
    border-top: 2px solid #38bdf8;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background-color: #141b29;
    color: #f1f5f9;
}
"""
