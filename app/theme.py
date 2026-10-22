"""Dark Operations Theme styling for Network Lab PySide6 GUI."""

DARK_THEME_QSS = """
QMainWindow {
    background-color: #0f141c;
}

QWidget {
    background-color: #0f141c;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}

/* Sidebar navigation */
QListWidget#navSidebar {
    background-color: #161e2e;
    border: none;
    border-right: 1px solid #2d3748;
    padding-top: 10px;
}

QListWidget#navSidebar::item {
    height: 40px;
    padding-left: 15px;
    color: #94a3b8;
    border-left: 3px solid transparent;
}

QListWidget#navSidebar::item:selected {
    background-color: #1e293b;
    color: #38bdf8;
    border-left: 3px solid #38bdf8;
    font-weight: bold;
}

QListWidget#navSidebar::item:hover {
    background-color: #1e293b;
    color: #f1f5f9;
}

/* Header & Status Bar */
QFrame#topBar {
    background-color: #161e2e;
    border-bottom: 1px solid #2d3748;
    padding: 8px 16px;
}

QLabel#titleLabel {
    font-size: 16px;
    font-weight: bold;
    color: #38bdf8;
}

QLabel#statusBadge {
    background-color: #0369a1;
    color: #ffffff;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
}

/* Cards & Panels */
QGroupBox {
    background-color: #161e2e;
    border: 1px solid #2d3748;
    border-radius: 6px;
    margin-top: 18px;
    padding: 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #38bdf8;
}

/* Buttons */
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #1d4ed8;
}

QPushButton:pressed {
    background-color: #1e40af;
}

QPushButton#btnSecondary {
    background-color: #334155;
    color: #f1f5f9;
}

QPushButton#btnSecondary:hover {
    background-color: #475569;
}

QPushButton#btnDanger {
    background-color: #dc2626;
}

QPushButton#btnDanger:hover {
    background-color: #b91c1c;
}

/* Tables */
QTableWidget {
    background-color: #111827;
    border: 1px solid #374151;
    gridline-color: #1f2937;
    border-radius: 4px;
}

QHeaderView::section {
    background-color: #1f2937;
    color: #9ca3af;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #374151;
    font-weight: 600;
}

/* Inputs */
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    background-color: #111827;
    border: 1px solid #374151;
    border-radius: 4px;
    padding: 5px 8px;
    color: #f9fafb;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #38bdf8;
}
"""
