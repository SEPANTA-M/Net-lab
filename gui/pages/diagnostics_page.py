"""Interactive Diagnostics Lab page for virtual ping and traceroute."""

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.network import VirtualNetwork
from core.protocols.icmp_sim import send_virtual_ping


class DiagnosticsPage(QWidget):
    """Virtual diagnostic ping and route inspection tools."""

    def __init__(self, network: VirtualNetwork, parent=None) -> None:
        super().__init__(parent)
        self.network = network

        layout = QVBoxLayout(self)

        title = QLabel("Simulation Diagnostics & Troubleshooting Lab")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(title)

        box = QGroupBox("Virtual Ping Tool (Safe In-Memory)")
        f_layout = QFormLayout(box)

        self.txt_src = QLineEdit("10.0.1.10")
        self.txt_dst = QLineEdit("10.0.2.50")
        self.btn_ping = QPushButton("Execute Virtual Ping")
        self.btn_ping.clicked.connect(self._run_ping)

        f_layout.addRow("Source IP:", self.txt_src)
        f_layout.addRow("Destination IP:", self.txt_dst)
        f_layout.addRow(self.btn_ping)
        layout.addWidget(box)

        # Output console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("font-family: monospace; background-color: #0b0f17; color: #10b981;")
        layout.addWidget(self.console)

    def _run_ping(self) -> None:
        src = self.txt_src.text().strip()
        dst = self.txt_dst.text().strip()
        self.console.append(f"\n--- Pinging {dst} from {src} (Simulated ICMP) ---")
        try:
            res = send_virtual_ping(self.network, src_ip=src, dst_ip=dst)
            if res.is_success:
                self.console.append(f"SUCCESS: Reply received from {dst}: time={res.rtt_ms:.2f}ms hops={res.hops}")
            else:
                self.console.append(f"FAILURE: Ping failed -> {res.error_message}")
        except Exception as e:
            self.console.append(f"ERROR: {e}")
