"""Main application window uniting all Network Lab panels and pages."""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.theme import DARK_THEME_QSS
from core.firewall import FirewallAction, FirewallRule, VirtualFirewall
from core.network import VirtualNetwork
from core.packet import Protocol
from discovery.collector import LocalSystemCollector
from gui.pages.diagnostics_page import DiagnosticsPage
from gui.pages.firewall_page import FirewallEditorPage
from gui.pages.overview_page import OverviewPage
from gui.topology_view.canvas import TopologyCanvas
from storage.scenarios import create_scenario_router_and_firewall


class MainWindow(QMainWindow):
    """Main window for Network Lab desktop application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Network Lab — Advanced Network Discovery & Simulation Platform")
        self.resize(1200, 800)
        self.setStyleSheet(DARK_THEME_QSS)

        # Initialize network engine with default scenario
        self.current_network = create_scenario_router_and_firewall()

        # Collector for real system observation
        self.collector = LocalSystemCollector()

        self._setup_ui()
        self._load_initial_data()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Bar
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        title_lbl = QLabel("NETWORK LAB")
        title_lbl.setObjectName("titleLabel")
        mode_badge = QLabel("SIMULATION MODE: ISOLATED")
        mode_badge.setObjectName("statusBadge")
        top_layout.addWidget(title_lbl)
        top_layout.addStretch()
        top_layout.addWidget(mode_badge)
        main_layout.addWidget(top_bar)

        # Splitter: Navigation Sidebar on Left, Content on Right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("navSidebar")
        self.sidebar.setMaximumWidth(220)
        nav_items = [
            "Overview",
            "Topology Canvas",
            "Firewall Editor",
            "Diagnostics Lab",
        ]
        self.sidebar.addItems(nav_items)
        self.sidebar.currentRowChanged.connect(self._on_navigation_change)
        splitter.addWidget(self.sidebar)

        # Stacked Pages
        self.pages = QStackedWidget()

        # Page 0: Overview
        self.page_overview = OverviewPage()
        self.pages.addWidget(self.page_overview)

        # Page 1: Topology
        self.page_topology = TopologyCanvas()
        self.pages.addWidget(self.page_topology)

        # Page 2: Firewall
        # Find firewall device in current scenario
        fw_dev = next((d for d in self.current_network.devices.values() if isinstance(d, VirtualFirewall)), None)
        if not fw_dev:
            fw_dev = VirtualFirewall(name="Default-FW", default_action=FirewallAction.DENY)
            self.current_network.add_device(fw_dev)
        self.page_firewall = FirewallEditorPage(fw_dev)
        self.pages.addWidget(self.page_firewall)

        # Page 3: Diagnostics
        self.page_diagnostics = DiagnosticsPage(self.current_network)
        self.pages.addWidget(self.page_diagnostics)

        splitter.addWidget(self.pages)
        splitter.setStretchFactor(1, 4)

        main_layout.addWidget(splitter)
        self.sidebar.setCurrentRow(0)

    def _load_initial_data(self) -> None:
        """Populate initial discovery overview and render topology canvas."""
        # 1. Real discovery
        snapshot = self.collector.collect_snapshot()
        self.page_overview.lbl_hostname.setText(f"Host: {snapshot.hostname}")
        self.page_overview.lbl_default_gw.setText(f"Default Gateway: {snapshot.default_gateway or 'None'}")
        self.page_overview.lbl_dns.setText(f"DNS Resolvers: {', '.join(snapshot.dns_servers) or 'None'}")

        # 2. Simulation Stats
        self.page_overview.lbl_vdevices.setText(f"Virtual Devices: {len(self.current_network.devices)}")
        self.page_overview.lbl_vlinks.setText(f"Virtual Links: {len(self.current_network.links)}")

        # 3. Render Canvas
        self.page_topology.render_network(self.current_network)

    def _on_navigation_change(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
