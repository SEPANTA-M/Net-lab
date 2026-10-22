"""Overview Dashboard displaying system and simulation metrics."""

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class OverviewPage(QWidget):
    """High-level summary of network discovery and simulation stats."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        title = QLabel("Operations Dashboard & Laboratory Overview")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(title)

        grid = QGridLayout()

        # Real Observation Card
        obs_box = QGroupBox("Real Network Observation (Read-Only)")
        obs_layout = QVBoxLayout(obs_box)
        self.lbl_hostname = QLabel("Host: Detecting...")
        self.lbl_default_gw = QLabel("Default Gateway: None")
        self.lbl_dns = QLabel("DNS Resolvers: None")
        obs_layout.addWidget(self.lbl_hostname)
        obs_layout.addWidget(self.lbl_default_gw)
        obs_layout.addWidget(self.lbl_dns)
        grid.addWidget(obs_box, 0, 0)

        # Virtual Simulation Card
        sim_box = QGroupBox("Virtual Simulation Engine (Isolated)")
        sim_layout = QVBoxLayout(sim_box)
        self.lbl_vdevices = QLabel("Virtual Devices: 0")
        self.lbl_vlinks = QLabel("Virtual Links: 0")
        self.lbl_packets = QLabel("Packets Processed: 0")
        sim_layout.addWidget(self.lbl_vdevices)
        sim_layout.addWidget(self.lbl_vlinks)
        sim_layout.addWidget(self.lbl_packets)
        grid.addWidget(sim_box, 0, 1)

        layout.addLayout(grid)

        # Quick Actions
        actions_box = QGroupBox("Quick Scenario Presets")
        act_layout = QHBoxLayout(actions_box)
        self.btn_preset1 = QPushButton("Load Scenario: Router & 2 Subnets")
        self.btn_preset2 = QPushButton("Load Scenario: Firewall & Web Service")
        self.btn_preset3 = QPushButton("Load Scenario: DNS & HTTP Service")
        act_layout.addWidget(self.btn_preset1)
        act_layout.addWidget(self.btn_preset2)
        act_layout.addWidget(self.btn_preset3)
        layout.addWidget(actions_box)

        layout.addStretch()
