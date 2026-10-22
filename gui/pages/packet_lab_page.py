"""Dedicated Packet Inspection and Creation Workspace."""

from __future__ import annotations

from typing import List, Optional
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
from core.packet import Packet, PacketState, Protocol
from gui.components.widgets import EmptyStateWidget, SectionHeader, StatusBadge


class PacketLabPage(QWidget):
    """Split-panel packet laboratory with packet history, deep inspection, and packet generator."""

    def __init__(self, network: VirtualNetwork, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.network = network
        self.captured_packets: List[Packet] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        header = SectionHeader(
            "Packet Inspection Laboratory",
            "Trace simulated packet journeys, protocol headers, and hop-by-hop forwarding decisions",
        )
        main_layout.addWidget(header)

        # Splitter: Left Packet List, Right Deep Inspection & Generator
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel: Captured Packet List
        left_box = QFrame()
        left_box.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 10px;")
        left_layout = QVBoxLayout(left_box)

        lbl_list = QLabel("SIMULATED PACKET STREAM")
        lbl_list.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.6px;")
        left_layout.addWidget(lbl_list)

        self.table_packets = QTableWidget(0, 5)
        self.table_packets.setHorizontalHeaderLabels(["State", "Protocol", "Source", "Destination", "Latency"])
        self.table_packets.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_packets.itemSelectionChanged.connect(self._on_packet_selected)
        left_layout.addWidget(self.table_packets)

        splitter.addWidget(left_box)

        # Right Panel: Inspector and Injector
        right_box = QFrame()
        right_box.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 10px;")
        right_layout = QVBoxLayout(right_box)

        # 1. Packet Detail View
        lbl_inspect = QLabel("PACKET DETAILS & HOP HISTORY")
        lbl_inspect.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.6px;")
        right_layout.addWidget(lbl_inspect)

        self.detail_area = QFrame()
        self.detail_area.setStyleSheet(f"background-color: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 8px;")
        self.detail_layout = QVBoxLayout(self.detail_area)
        self.detail_empty = QLabel("Select a packet on the left to inspect route history and protocol headers.")
        self.detail_empty.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        self.detail_layout.addWidget(self.detail_empty)
        right_layout.addWidget(self.detail_area)

        # 2. Inject Test Packet Form
        lbl_inject = QLabel("SYNTHESIZE TEST PACKET")
        lbl_inject.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {COLORS['text_muted']}; letter-spacing: 0.6px; margin-top: 10px;")
        right_layout.addWidget(lbl_inject)

        inject_box = QFrame()
        inject_box.setStyleSheet(f"background-color: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px; padding: 8px;")
        inject_form = QFormLayout(inject_box)

        self.txt_src = QLineEdit("10.0.1.10")
        self.txt_dst = QLineEdit("10.0.2.50")
        self.cmb_proto = QComboBox()
        self.cmb_proto.addItems(["ICMP", "TCP", "UDP", "HTTP", "DNS"])
        self.spin_port = QSpinBox()
        self.spin_port.setRange(0, 65535)
        self.spin_port.setValue(80)

        inject_form.addRow("Source IP:", self.txt_src)
        inject_form.addRow("Dest IP:", self.txt_dst)
        inject_form.addRow("Protocol:", self.cmb_proto)
        inject_form.addRow("Dest Port:", self.spin_port)

        self.btn_send = QPushButton("Inject Simulated Packet")
        self.btn_send.setObjectName("btnPrimary")
        self.btn_send.clicked.connect(self._handle_inject_packet)
        inject_form.addRow(self.btn_send)

        right_layout.addWidget(inject_box)
        right_layout.addStretch()

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

    def set_network(self, network: VirtualNetwork) -> None:
        self.network = network

    def record_packet(self, packet: Packet) -> None:
        """Add a transmitted packet to the inspection log."""
        self.captured_packets.append(packet)
        row = self.table_packets.rowCount()
        self.table_packets.insertRow(row)

        state_item = QTableWidgetItem(packet.state.value)
        self.table_packets.setItem(row, 0, state_item)
        self.table_packets.setItem(row, 1, QTableWidgetItem(packet.protocol.value))
        self.table_packets.setItem(row, 2, QTableWidgetItem(packet.src_ip))
        self.table_packets.setItem(row, 3, QTableWidgetItem(packet.dst_ip))
        self.table_packets.setItem(row, 4, QTableWidgetItem(f"{packet.simulated_latency_ms:.2f} ms"))

    def _on_packet_selected(self) -> None:
        rows = self.table_packets.selectionModel().selectedRows()
        if not rows:
            return
        idx = rows[0].row()
        if idx < len(self.captured_packets):
            self._render_packet_details(self.captured_packets[idx])

    def _render_packet_details(self, pkt: Packet) -> None:
        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        header = QLabel(f"Packet ID: {pkt.packet_id}")
        header.setStyleSheet("font-family: 'SF Mono', Consolas, monospace; font-size: 11px; font-weight: 700; color: #38bdf8;")
        self.detail_layout.addWidget(header)

        status_lbl = QLabel(f"Result: {pkt.state.value} — {pkt.drop_or_delivery_reason or 'None'}")
        status_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS['text_primary']};")
        self.detail_layout.addWidget(status_lbl)

        # Hop history
        hops_hdr = QLabel("ROUTING HOPS:")
        hops_hdr.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLORS['text_muted']}; margin-top: 6px;")
        self.detail_layout.addWidget(hops_hdr)

        for i, h in enumerate(pkt.route_history):
            hop_row = QLabel(f"Hop {i+1}: {h.action} -> {h.detail}")
            hop_row.setStyleSheet("font-family: 'SF Mono', Consolas, monospace; font-size: 10px; color: #94a3b8;")
            self.detail_layout.addWidget(hop_row)

    def _handle_inject_packet(self) -> None:
        src = self.txt_src.text().strip()
        dst = self.txt_dst.text().strip()
        proto = Protocol(self.cmb_proto.currentText())
        port = self.spin_port.value()

        pkt = Packet(
            src_ip=src,
            dst_ip=dst,
            protocol=proto,
            dst_port=port,
        )
        res = self.network.transmit(pkt)
        self.record_packet(res)
