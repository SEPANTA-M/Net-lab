"""Reusable design components for Network Lab engineering workstation."""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.theme import COLORS


class StatusBadge(QLabel):
    """Compact status chip for states like OBSERVED, INFERRED, RUNNING, ALLOW, DENY."""

    def __init__(self, text: str, variant: str = "default", parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(18)
        self.set_variant(variant)

    def set_variant(self, variant: str) -> None:
        style_map = {
            "success": (COLORS["success_bg"], COLORS["success"], "#10b981"),
            "warning": (COLORS["warning_bg"], COLORS["warning"], "#f59e0b"),
            "error": (COLORS["error_bg"], COLORS["error"], "#ef4444"),
            "cyan": ("#0c4a6e", "#38bdf8", "#0284c7"),
            "inferred": ("#451a03", "#fbbf24", "#d97706"),
            "observed": ("#064e3b", "#34d399", "#059669"),
            "simulated": ("#1e3a8a", "#60a5fa", "#2563eb"),
            "default": ("#1e293b", "#94a3b8", "#334155"),
        }
        bg, fg, border = style_map.get(variant, style_map["default"])
        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 3px;
                padding: 1px 6px;
                font-family: -apple-system, sans-serif;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            """
        )


class SectionHeader(QWidget):
    """Clean engineering section header with action slot."""

    def __init__(self, title: str, subtitle: Optional[str] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 8)
        layout.setSpacing(8)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #f1f5f9; letter-spacing: 0.8px;")
        text_layout.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
            text_layout.addWidget(sub_lbl)

        layout.addLayout(text_layout)
        layout.addStretch()
        self.actions_layout = QHBoxLayout()
        layout.addLayout(self.actions_layout)

    def add_action_button(self, text: str, callback=None) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("btnGhost")
        btn.setFixedHeight(24)
        if callback:
            btn.clicked.connect(callback)
        self.actions_layout.addWidget(btn)
        return btn


class SearchInput(QLineEdit):
    """Monospace filter search input with clear button."""

    def __init__(self, placeholder: str = "Filter entries...", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setFixedHeight(28)


class MetricCard(QFrame):
    """Dense technical statistic display card."""

    def __init__(self, label: str, value: str, subtext: str = "", badge: Optional[str] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"""
            MetricCard {{
                background-color: {COLORS['bg_panel']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 4px;
                padding: 10px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        lbl_widget = QLabel(label.upper())
        lbl_widget.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.6px;")
        top_row.addWidget(lbl_widget)
        top_row.addStretch()
        if badge:
            top_row.addWidget(StatusBadge(badge, "cyan"))
        layout.addLayout(top_row)

        self.val_widget = QLabel(value)
        self.val_widget.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLORS['text_primary']}; font-family: 'SF Mono', Consolas, monospace;")
        layout.addWidget(self.val_widget)

        if subtext:
            sub_widget = QLabel(subtext)
            sub_widget.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']};")
            layout.addWidget(sub_widget)

    def set_value(self, value: str) -> None:
        self.val_widget.setText(value)


class EmptyStateWidget(QWidget):
    """Engineered empty state guidance with working call to action."""

    def __init__(self, title: str, description: str, action_text: Optional[str] = None, on_action=None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {COLORS['text_primary']};")
        t_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(t_lbl)

        d_lbl = QLabel(description)
        d_lbl.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']}; max-width: 400px;")
        d_lbl.setWordWrap(True)
        d_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(d_lbl)

        if action_text and on_action:
            btn = QPushButton(action_text)
            btn.setObjectName("btnPrimary")
            btn.setFixedHeight(30)
            btn.clicked.connect(on_action)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
