"""Engineering Routing Table Workspace with Longest-Prefix Match explanation."""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.theme import COLORS
from core.network import VirtualNetwork
from core.routing import VirtualRouter
from gui.components.widgets import EmptyStateWidget, SectionHeader, StatusBadge


class RoutingWorkspacePage(QWidget):
    """Routing table inspection and route arbitration workspace."""

    def __init__(self, network: VirtualNetwork, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.network = network

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        header = SectionHeader(
            "Routing Table Workspace",
            "Inspect virtual router forwarding tables, longest-prefix matching (LPM), and metrics",
        )
        main_layout.addWidget(header)

        # Router Selector
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Select Virtual Router:"))
        self.cmb_routers = QComboBox()
        self.cmb_routers.currentIndexChanged.connect(self._on_router_changed)
        sel_row.addWidget(self.cmb_routers)
        sel_row.addStretch()
        main_layout.addLayout(sel_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel: Routing Table
        left_box = QFrame()
        left_box.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 10px;")
        left_layout = QVBoxLayout(left_box)

        lbl_tbl = QLabel("ACTIVE FORWARDING TABLE")
        lbl_tbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.6px;")
        left_layout.addWidget(lbl_tbl)

        self.table_routes = QTableWidget(0, 5)
        self.table_routes.setHorizontalHeaderLabels(["Destination CIDR", "Type", "Next Hop", "Interface", "Metric"])
        self.table_routes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.table_routes)

        splitter.addWidget(left_box)

        # Right Panel: Add Route Form & LPM Lookup Tester
        right_box = QFrame()
        right_box.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 10px;")
        right_layout = QVBoxLayout(right_box)

        # 1. LPM Lookup Tester
        lbl_test = QLabel("LONGEST-PREFIX MATCH TESTER")
        lbl_test.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.6px;")
        right_layout.addWidget(lbl_test)

        test_form = QFormLayout()
        self.txt_test_ip = QLineEdit("10.0.2.20")
        self.btn_test = QPushButton("Test Lookup")
        self.btn_test.clicked.connect(self._test_lpm)
        test_form.addRow("Target IP:", self.txt_test_ip)
        test_form.addRow(self.btn_test)
        right_layout.addLayout(test_form)

        self.lbl_lpm_res = QLabel("Enter an IP and click 'Test Lookup' to see matching route.")
        self.lbl_lpm_res.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; padding: 6px; background-color: {COLORS['bg_panel_alt']}; border-radius: 3px;")
        self.lbl_lpm_res.setWordWrap(True)
        right_layout.addWidget(self.lbl_lpm_res)

        # 2. Add Static Route
        lbl_add = QLabel("ADD STATIC ROUTE")
        lbl_add.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.6px; margin-top: 14px;")
        right_layout.addWidget(lbl_add)

        add_form = QFormLayout()
        self.txt_cidr = QLineEdit("10.0.3.0/24")
        self.txt_next_hop = QLineEdit("10.0.1.254")
        self.spin_metric = QSpinBox()
        self.spin_metric.setValue(1)
        self.btn_add_route = QPushButton("Add Route Entry")
        self.btn_add_route.setObjectName("btnPrimary")
        self.btn_add_route.clicked.connect(self._handle_add_route)

        add_form.addRow("Destination:", self.txt_cidr)
        add_form.addRow("Next Hop:", self.txt_next_hop)
        add_form.addRow("Metric:", self.spin_metric)
        add_form.addRow(self.btn_add_route)
        right_layout.addLayout(add_form)

        right_layout.addStretch()

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)
        self.refresh_routers()

    def set_network(self, network: VirtualNetwork) -> None:
        self.network = network
        self.refresh_routers()

    def refresh_routers(self) -> None:
        self.cmb_routers.clear()
        routers = [d for d in self.network.devices.values() if isinstance(d, VirtualRouter)]
        for r in routers:
            self.cmb_routers.addItem(r.name, r.device_id)

        if routers:
            self._on_router_changed(0)

    def _get_current_router(self) -> Optional[VirtualRouter]:
        r_id = self.cmb_routers.currentData()
        if not r_id:
            return None
        dev = self.network.get_device(r_id)
        return dev if isinstance(dev, VirtualRouter) else None

    def _on_router_changed(self, index: int) -> None:
        router = self._get_current_router()
        if not router:
            self.table_routes.setRowCount(0)
            return

        routes = router.routing_table.all_routes()
        self.table_routes.setRowCount(len(routes))
        for row, r in enumerate(routes):
            self.table_routes.setItem(row, 0, QTableWidgetItem(r.destination_network))
            self.table_routes.setItem(row, 1, QTableWidgetItem(r.route_type.value))
            self.table_routes.setItem(row, 2, QTableWidgetItem(r.next_hop or "DIRECT"))
            self.table_routes.setItem(row, 3, QTableWidgetItem(r.interface_id or "AUTO"))
            self.table_routes.setItem(row, 4, QTableWidgetItem(str(r.metric)))

    def _test_lpm(self) -> None:
        router = self._get_current_router()
        if not router:
            return
        target = self.txt_test_ip.text().strip()
        matched = router.route_lookup(target)
        if matched:
            self.lbl_lpm_res.setText(
                f"MATCHED: {matched.destination_network} (prefix /{matched.prefix_length}) via {matched.next_hop or 'direct connected'} [Metric: {matched.metric}]"
            )
        else:
            self.lbl_lpm_res.setText(f"NO MATCH: No route exists toward {target} on {router.name}.")

    def _handle_add_route(self) -> None:
        router = self._get_current_router()
        if not router:
            return
        cidr = self.txt_cidr.text().strip()
        next_hop = self.txt_next_hop.text().strip()
        metric = self.spin_metric.value()

        router.add_static_route(
            destination_network=cidr,
            next_hop=next_hop if next_hop else None,
            metric=metric,
        )
        self._on_router_changed(0)
