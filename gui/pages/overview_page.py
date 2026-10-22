"""Engineering Overview Workstation Page with Metrics, Topology Mini-map, and Activity Timeline."""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.theme import COLORS
from core.network import VirtualNetwork
from discovery.models import NetworkSnapshot
from gui.components.widgets import MetricCard, SectionHeader, StatusBadge


class OverviewPage(QWidget):
    """Redesigned Overview Dashboard combining high-density metrics, topology overview, and timeline."""

    load_scenario_requested = Signal(str)
    navigate_to_page = Signal(str)

    def __init__(self, network: VirtualNetwork, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.network = network

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # 1. Top Section Header
        header = SectionHeader(
            "Engineering Operations & Laboratory Overview",
            "Real system observation status and virtual network simulation metrics",
        )
        main_layout.addWidget(header)

        # 2. Key Metrics Strip (Real Data)
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(10)

        self.card_nodes = MetricCard("Simulated Devices", str(len(self.network.devices)), "Active in memory", "SIMULATED")
        self.card_links = MetricCard("Virtual Links", str(len(self.network.links)), "Topology edges", "CONNECTED")
        self.card_obs_ifaces = MetricCard("Discovered Interfaces", "0", "Local host adapters", "OBSERVED")
        self.card_gateway = MetricCard("Default Gateway", "None", "Inferred routing hop", "GATEWAY")

        metrics_grid.addWidget(self.card_nodes, 0, 0)
        metrics_grid.addWidget(self.card_links, 0, 1)
        metrics_grid.addWidget(self.card_obs_ifaces, 0, 2)
        metrics_grid.addWidget(self.card_gateway, 0, 3)
        main_layout.addLayout(metrics_grid)

        # 3. Main Split View: Left Topology Summary & Quick Presets, Right Activity Timeline
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel: Scenario Presets & Topology Summary
        left_box = QFrame()
        left_box.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 12px;")
        left_layout = QVBoxLayout(left_box)

        lbl_presets = QLabel("PRECONFIGURED ENGINEERING SCENARIOS")
        lbl_presets.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.6px;")
        left_layout.addWidget(lbl_presets)

        scenarios = [
            ("scenario_1", "Two Subnets & Virtual Router", "Inter-VLAN style routing between 10.0.1.0/24 and 10.0.2.0/24"),
            ("scenario_2", "Router & Firewall Filter", "Edge firewall blocking unauthorized ports, allowing HTTP"),
            ("scenario_3", "DNS Resolver & HTTP Web Server", "Name resolution and virtual HTTP GET transaction"),
        ]

        for s_id, s_name, s_desc in scenarios:
            card = QFrame()
            card.setStyleSheet(f"background-color: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 8px;")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(6, 6, 6, 6)
            c_layout.setSpacing(4)

            row = QHBoxLayout()
            row.addWidget(QLabel(s_name))
            row.addStretch()
            btn_load = QPushButton("Load Scenario")
            btn_load.setObjectName("btnGhost")
            btn_load.clicked.connect(lambda _, key=s_id: self.load_scenario_requested.emit(key))
            row.addWidget(btn_load)
            c_layout.addLayout(row)

            desc_lbl = QLabel(s_desc)
            desc_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
            c_layout.addWidget(desc_lbl)
            left_layout.addWidget(card)

        left_layout.addStretch()
        splitter.addWidget(left_box)

        # Right Panel: Activity & Diagnostics Log
        right_box = QFrame()
        right_box.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 12px;")
        right_layout = QVBoxLayout(right_box)

        lbl_activity = QLabel("SIMULATION & AUDIT TIMELINE")
        lbl_activity.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.6px;")
        right_layout.addWidget(lbl_activity)

        self.table_activity = QTableWidget(0, 3)
        self.table_activity.setHorizontalHeaderLabels(["Timestamp", "Type", "Event Detail"])
        self.table_activity.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_activity.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_activity.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.table_activity)

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def update_snapshot(self, snapshot: NetworkSnapshot) -> None:
        """Update metrics with fresh real-network observation data."""
        self.card_obs_ifaces.set_value(str(len(snapshot.interfaces)))
        self.card_gateway.set_value(snapshot.default_gateway or "None")

    def update_simulation_stats(self, network: VirtualNetwork) -> None:
        """Update simulation device counts."""
        self.network = network
        self.card_nodes.set_value(str(len(network.devices)))
        self.card_links.set_value(str(len(network.links)))

    def log_event(self, event_type: str, detail: str) -> None:
        """Add entry to activity table."""
        from datetime import datetime, timezone
        row = self.table_activity.rowCount()
        self.table_activity.insertRow(row)

        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.table_activity.setItem(row, 0, QTableWidgetItem(ts))
        self.table_activity.setItem(row, 1, QTableWidgetItem(event_type))
        self.table_activity.setItem(row, 2, QTableWidgetItem(detail))
        self.table_activity.scrollToBottom()
