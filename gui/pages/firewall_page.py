"""Interactive Firewall Editor GUI with rule testing capabilities."""

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.firewall import FirewallAction, FirewallRule, VirtualFirewall
from core.packet import Packet, Protocol


class FirewallEditorPage(QWidget):
    """Configures virtual firewall rules and tests them against sample packets."""

    def __init__(self, firewall: VirtualFirewall, parent=None) -> None:
        super().__init__(parent)
        self.firewall = firewall

        layout = QVBoxLayout(self)

        title = QLabel(f"Virtual Firewall Rule Editor — {firewall.name}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(title)

        # Rules Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Action", "Priority", "Proto", "Src CIDR", "Dst Port", "Hits"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Rule Form
        form_box = QGroupBox("Add Filter Rule")
        form_layout = QFormLayout(form_box)

        self.cmb_action = QComboBox()
        self.cmb_action.addItems(["ALLOW", "DENY", "REJECT"])

        self.spin_priority = QSpinBox()
        self.spin_priority.setRange(1, 1000)
        self.spin_priority.setValue(100)

        self.cmb_proto = QComboBox()
        self.cmb_proto.addItems(["ANY", "TCP", "UDP", "ICMP", "HTTP", "DNS"])

        self.txt_dst_port = QLineEdit()
        self.txt_dst_port.setPlaceholderText("e.g. 80 (or empty for any)")

        self.btn_add = QPushButton("Add Rule")
        self.btn_add.clicked.connect(self._handle_add_rule)

        form_layout.addRow("Action:", self.cmb_action)
        form_layout.addRow("Priority:", self.spin_priority)
        form_layout.addRow("Protocol:", self.cmb_proto)
        form_layout.addRow("Dst Port:", self.txt_dst_port)
        form_layout.addRow(self.btn_add)
        layout.addWidget(form_box)

        self.refresh_table()

    def refresh_table(self) -> None:
        """Populate table with current rules."""
        self.table.setRowCount(len(self.firewall.rules))
        for row, r in enumerate(self.firewall.rules):
            self.table.setItem(row, 0, QTableWidgetItem(r.action.value))
            self.table.setItem(row, 1, QTableWidgetItem(str(r.priority)))
            self.table.setItem(row, 2, QTableWidgetItem(r.protocol.value if r.protocol else "ANY"))
            self.table.setItem(row, 3, QTableWidgetItem(r.src_cidr or "ANY"))
            self.table.setItem(row, 4, QTableWidgetItem(str(r.dst_port) if r.dst_port else "ANY"))
            self.table.setItem(row, 5, QTableWidgetItem(str(r.hit_count)))

    def _handle_add_rule(self) -> None:
        action = FirewallAction(self.cmb_action.currentText())
        prio = self.spin_priority.value()
        proto_txt = self.cmb_proto.currentText()
        proto = Protocol(proto_txt) if proto_txt != "ANY" else None

        port = None
        if self.txt_dst_port.text().strip():
            try:
                port = int(self.txt_dst_port.text().strip())
            except ValueError:
                pass

        rule = FirewallRule(
            action=action,
            priority=prio,
            protocol=proto,
            dst_port=port,
            description=f"Rule {prio}",
        )
        self.firewall.add_rule(rule)
        self.refresh_table()
