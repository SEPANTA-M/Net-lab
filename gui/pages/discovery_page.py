"""Engineering Real Network Discovery and Provenance Workspace."""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
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
from digital_twin.topology_mapper import DigitalTwinMapper
from discovery.collector import LocalSystemCollector
from discovery.models import NetworkSnapshot
from gui.components.widgets import MetricCard, SectionHeader, StatusBadge


class DiscoveryWorkspacePage(QWidget):
    """Network discovery and digital twin generation workstation page."""

    digital_twin_imported = Signal(object)  # Emits DigitalTwinMappingResult

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.collector = LocalSystemCollector()
        self.latest_snapshot: Optional[NetworkSnapshot] = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        header = SectionHeader(
            "Local Network Discovery & Provenance",
            "Read-only observation of local host configuration with explicit confidence indicators",
        )
        main_layout.addWidget(header)

        # Discovery Action Bar
        action_bar = QFrame()
        action_bar.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 6px;")
        a_layout = QHBoxLayout(action_bar)
        a_layout.setContentsMargins(8, 4, 8, 4)

        self.btn_refresh = QPushButton("Refresh Local Observation")
        self.btn_refresh.setObjectName("btnPrimary")
        self.btn_refresh.clicked.connect(self.run_observation)
        a_layout.addWidget(self.btn_refresh)

        self.btn_import_twin = QPushButton("Synthesize Digital Twin (Editable Virtual Model)")
        self.btn_import_twin.clicked.connect(self._handle_import_digital_twin)
        a_layout.addWidget(self.btn_import_twin)

        a_layout.addStretch()
        self.lbl_obs_time = QLabel("Observation: Ready")
        self.lbl_obs_time.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        a_layout.addWidget(self.lbl_obs_time)

        main_layout.addWidget(action_bar)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # 1. Observed Interfaces Table
        box_ifaces = QFrame()
        box_ifaces.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 10px;")
        layout_if = QVBoxLayout(box_ifaces)
        lbl_if = QLabel("DISCOVERED LOCAL INTERFACES (OBSERVED)")
        lbl_if.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.6px;")
        layout_if.addWidget(lbl_if)

        self.table_ifaces = QTableWidget(0, 5)
        self.table_ifaces.setHorizontalHeaderLabels(["Interface Name", "Status", "IP Addresses", "MAC Address", "Provenance"])
        self.table_ifaces.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout_if.addWidget(self.table_ifaces)
        splitter.addWidget(box_ifaces)

        # 2. Observed Routes Table
        box_routes = QFrame()
        box_routes.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 10px;")
        layout_rt = QVBoxLayout(box_routes)
        lbl_rt = QLabel("DISCOVERED HOST ROUTES & GATEWAYS")
        lbl_rt.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.6px;")
        layout_rt.addWidget(lbl_rt)

        self.table_routes = QTableWidget(0, 5)
        self.table_routes.setHorizontalHeaderLabels(["Destination", "Gateway", "Interface", "Metric", "Confidence"])
        self.table_routes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout_rt.addWidget(self.table_routes)
        splitter.addWidget(box_routes)

        main_layout.addWidget(splitter)
        self.run_observation()

    def run_observation(self) -> None:
        """Run read-only discovery inspection."""
        self.latest_snapshot = self.collector.collect_snapshot()

        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        self.lbl_obs_time.setText(f"Observed: {ts}")

        # Render Interfaces
        self.table_ifaces.setRowCount(len(self.latest_snapshot.interfaces))
        for row, ifc in enumerate(self.latest_snapshot.interfaces):
            self.table_ifaces.setItem(row, 0, QTableWidgetItem(ifc.name))
            self.table_ifaces.setItem(row, 1, QTableWidgetItem("UP" if ifc.is_up else "DOWN"))
            self.table_ifaces.setItem(row, 2, QTableWidgetItem(", ".join(ifc.ip_addresses) or "None"))
            self.table_ifaces.setItem(row, 3, QTableWidgetItem(ifc.mac_address or "Unknown"))
            self.table_ifaces.setItem(row, 4, QTableWidgetItem(f"{ifc.source.value} ({ifc.confidence.value})"))

        # Render Routes
        self.table_routes.setRowCount(len(self.latest_snapshot.routes))
        for row, rt in enumerate(self.latest_snapshot.routes):
            self.table_routes.setItem(row, 0, QTableWidgetItem(rt.destination))
            self.table_routes.setItem(row, 1, QTableWidgetItem(rt.gateway or "Direct"))
            self.table_routes.setItem(row, 2, QTableWidgetItem(rt.interface_name or "Unknown"))
            self.table_routes.setItem(row, 3, QTableWidgetItem(str(rt.metric)))
            self.table_routes.setItem(row, 4, QTableWidgetItem(rt.confidence.value))

    def _handle_import_digital_twin(self) -> None:
        if not self.latest_snapshot:
            return
        result = DigitalTwinMapper.snapshot_to_virtual_topology(self.latest_snapshot)
        self.digital_twin_imported.emit(result)
