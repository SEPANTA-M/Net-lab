"""Redesigned Professional Desktop Application Shell for Network Lab."""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.theme import COLORS, DARK_ENGINEERING_THEME
from core.firewall import FirewallAction, VirtualFirewall
from core.network import VirtualNetwork
from core.scheduler import DiscreteEventScheduler
from discovery.collector import LocalSystemCollector
from gui.components.widgets import StatusBadge
from gui.pages.diagnostics_page import DiagnosticsPage
from gui.pages.discovery_page import DiscoveryWorkspacePage
from gui.pages.firewall_page import FirewallEditorPage
from gui.pages.overview_page import OverviewPage
from gui.pages.packet_lab_page import PacketLabPage
from gui.pages.routing_page import RoutingWorkspacePage
from gui.topology_view.canvas import TopologyWorkspace
from storage.scenarios import (
    create_scenario_dns_and_http,
    create_scenario_router_and_firewall,
    create_scenario_two_servers_one_router,
)


class MainWindow(QMainWindow):
    """Main desktop engineering workstation shell for Network Lab."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Network Lab — Professional Network Discovery, Digital Twin & Simulation Workstation")
        self.resize(1280, 840)
        self.setMinimumSize(1024, 680)
        self.setStyleSheet(DARK_ENGINEERING_THEME)

        # Simulation & Observation State
        self.current_network: VirtualNetwork = create_scenario_router_and_firewall()
        self.scheduler: DiscreteEventScheduler = DiscreteEventScheduler()
        self.collector: LocalSystemCollector = LocalSystemCollector()

        self._setup_ui()
        self._load_initial_data()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Compact Engineering Top Bar
        top_bar = QFrame()
        top_bar.setFixedHeight(38)
        top_bar.setStyleSheet(f"background-color: {COLORS['bg_sidebar']}; border-bottom: 1px solid {COLORS['border_subtle']};")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 0, 12, 0)
        top_layout.setSpacing(10)

        # Logo & App Name
        brand_lbl = QLabel("NETWORK LAB")
        brand_lbl.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {COLORS['accent_cyan_glow']}; letter-spacing: 1px;")
        top_layout.addWidget(brand_lbl)

        sep = QLabel("|")
        sep.setStyleSheet(f"color: {COLORS['border_medium']};")
        top_layout.addWidget(sep)

        self.lbl_workspace_title = QLabel("OVERVIEW DASHBOARD")
        self.lbl_workspace_title.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {COLORS['text_muted']}; letter-spacing: 0.5px;")
        top_layout.addWidget(self.lbl_workspace_title)

        top_layout.addStretch()

        # Engine Status Badges (Never confuse real observation with virtual simulation)
        self.badge_obs = StatusBadge("DISCOVERY: READY", "observed")
        self.badge_sim = StatusBadge("SIMULATION: ISOLATED", "simulated")
        top_layout.addWidget(self.badge_obs)
        top_layout.addWidget(self.badge_sim)

        # Simulation Scheduler Controls
        self.btn_play_sim = QPushButton("Resume")
        self.btn_play_sim.setObjectName("btnGhost")
        self.btn_play_sim.setFixedHeight(24)
        self.btn_play_sim.clicked.connect(self._toggle_simulation)
        top_layout.addWidget(self.btn_play_sim)

        self.btn_step_sim = QPushButton("Step Event")
        self.btn_step_sim.setObjectName("btnGhost")
        self.btn_step_sim.setFixedHeight(24)
        self.btn_step_sim.clicked.connect(self._step_simulation)
        top_layout.addWidget(self.btn_step_sim)

        main_layout.addWidget(top_bar)

        # 2. Main Workspace Splitter: Left Sidebar & Content Pages
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Navigation Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebarNav")
        self.sidebar.setMaximumWidth(210)
        self.sidebar.setMinimumWidth(180)

        nav_items = [
            "Overview",
            "Topology Canvas",
            "Packet Lab",
            "Firewall Editor",
            "Routing Table",
            "Network Discovery",
            "Diagnostics Lab",
        ]
        self.sidebar.addItems(nav_items)
        self.sidebar.currentRowChanged.connect(self._on_navigation_change)
        splitter.addWidget(self.sidebar)

        # Content Pages Stack
        self.pages = QStackedWidget()

        # Page 0: Overview
        self.page_overview = OverviewPage(self.current_network)
        self.page_overview.load_scenario_requested.connect(self.load_scenario_by_key)
        self.pages.addWidget(self.page_overview)

        # Page 1: Topology Workspace (Most important screen)
        self.page_topology = TopologyWorkspace(self.current_network)
        self.pages.addWidget(self.page_topology)

        # Page 2: Packet Lab
        self.page_packet_lab = PacketLabPage(self.current_network)
        self.pages.addWidget(self.page_packet_lab)

        # Page 3: Firewall
        fw_dev = next((d for d in self.current_network.devices.values() if isinstance(d, VirtualFirewall)), None)
        if not fw_dev:
            fw_dev = VirtualFirewall(name="Default-FW", default_action=FirewallAction.DENY)
            self.current_network.add_device(fw_dev)
        self.page_firewall = FirewallEditorPage(fw_dev)
        self.pages.addWidget(self.page_firewall)

        # Page 4: Routing Table
        self.page_routing = RoutingWorkspacePage(self.current_network)
        self.pages.addWidget(self.page_routing)

        # Page 5: Discovery & Digital Twin
        self.page_discovery = DiscoveryWorkspacePage()
        self.page_discovery.digital_twin_imported.connect(self._apply_digital_twin)
        self.pages.addWidget(self.page_discovery)

        # Page 6: Diagnostics Lab
        self.page_diagnostics = DiagnosticsPage(self.current_network)
        self.pages.addWidget(self.page_diagnostics)

        splitter.addWidget(self.pages)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)
        self.sidebar.setCurrentRow(0)

    def _load_initial_data(self) -> None:
        """Fetch local snapshot and populate dashboard."""
        snapshot = self.collector.collect_snapshot()
        self.page_overview.update_snapshot(snapshot)
        self.page_overview.update_simulation_stats(self.current_network)
        self.page_overview.log_event("DISCOVERY", f"Observed {len(snapshot.interfaces)} local interfaces on {snapshot.hostname}")
        self.page_overview.log_event("SIMULATION", "Virtual network engine initialized with isolated Scenario 2")

    def _on_navigation_change(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        titles = [
            "OVERVIEW DASHBOARD",
            "TOPOLOGY WORKSPACE",
            "PACKET INSPECTION LABORATORY",
            "FIREWALL RULE WORKSPACE",
            "ROUTING TABLE WORKSPACE",
            "NETWORK DISCOVERY & PROVENANCE",
            "DIAGNOSTICS & TROUBLESHOOTING",
        ]
        if index < len(titles):
            self.lbl_workspace_title.setText(titles[index])

    def load_scenario_by_key(self, key: str) -> None:
        """Load preconfigured engineering scenario."""
        if key == "scenario_1":
            self.current_network = create_scenario_two_servers_one_router()
            desc = "Scenario 1: Two Subnets & Virtual Router"
        elif key == "scenario_2":
            self.current_network = create_scenario_router_and_firewall()
            desc = "Scenario 2: Router & Firewall Filter"
        else:
            self.current_network = create_scenario_dns_and_http()
            desc = "Scenario 3: DNS Resolver & HTTP Web Server"

        # Update all pages with the new network
        self.page_topology = TopologyWorkspace(self.current_network)
        self.pages.removeWidget(self.pages.widget(1))
        self.pages.insertWidget(1, self.page_topology)

        self.page_packet_lab.set_network(self.current_network)
        self.page_routing.set_network(self.current_network)
        self.page_diagnostics = DiagnosticsPage(self.current_network)
        self.pages.removeWidget(self.pages.widget(6))
        self.pages.insertWidget(6, self.page_diagnostics)

        # Update firewall
        fw_dev = next((d for d in self.current_network.devices.values() if isinstance(d, VirtualFirewall)), None)
        if fw_dev:
            self.page_firewall = FirewallEditorPage(fw_dev)
            self.pages.removeWidget(self.pages.widget(3))
            self.pages.insertWidget(3, self.page_firewall)

        self.page_overview.update_simulation_stats(self.current_network)
        self.page_overview.log_event("SCENARIO", f"Loaded {desc}")

    def _apply_digital_twin(self, result) -> None:
        """Switch active simulation topology to generated digital twin."""
        self.current_network = result.virtual_network
        self.page_topology = TopologyWorkspace(self.current_network)
        self.pages.removeWidget(self.pages.widget(1))
        self.pages.insertWidget(1, self.page_topology)

        self.page_packet_lab.set_network(self.current_network)
        self.page_routing.set_network(self.current_network)
        self.page_overview.update_simulation_stats(self.current_network)
        self.page_overview.log_event("DIGITAL_TWIN", f"Synthesized digital twin with {len(result.created_devices)} nodes")
        self.sidebar.setCurrentRow(1)  # Navigate straight to topology

    def _toggle_simulation(self) -> None:
        self.page_overview.log_event("SCHEDULER", "Simulation clock resumed")

    def _step_simulation(self) -> None:
        self.page_overview.log_event("SCHEDULER", "Executed 1 simulation event step")
