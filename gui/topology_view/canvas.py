"""Professional Topology Canvas with Vector Node Glyphs, Links, Grid, and Context Inspector."""

from __future__ import annotations

import math
from typing import Dict, Optional
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.theme import COLORS
from core.device import DeviceState, DeviceType, VirtualDevice, VirtualInterface
from core.firewall import VirtualFirewall
from core.network import VirtualLink, VirtualNetwork
from core.routing import VirtualRouter
from core.server import VirtualServer
from gui.components.widgets import SectionHeader, StatusBadge


class NodeVectorItem(QGraphicsPathItem):
    """Vector-styled professional network node glyph."""

    def __init__(self, device: VirtualDevice, x: float, y: float, canvas: "TopologyWorkspace") -> None:
        super().__init__()
        self.device = device
        self.canvas = canvas
        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        # Build rounded rect glyph
        path = QPainterPath()
        path.addRoundedRect(-40, -28, 80, 56, 6, 6)
        self.setPath(path)

        self._update_appearance()

        # Labels
        self.title_text = QGraphicsTextItem(device.name, self)
        self.title_text.setDefaultTextColor(QColor(COLORS["text_primary"]))
        self.title_text.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.title_text.setPos(-36, -24)

        # Primary IP display
        ips = device.get_all_ips()
        ip_label = ips[0] if ips else "No IP"
        self.ip_text = QGraphicsTextItem(ip_label, self)
        self.ip_text.setDefaultTextColor(QColor(COLORS["text_secondary"]))
        self.ip_text.setFont(QFont("SF Mono", 7))
        self.ip_text.setPos(-36, -4)

        # Device Type Tag
        self.tag_text = QGraphicsTextItem(f"[{device.device_type.value}]", self)
        self.tag_text.setDefaultTextColor(QColor(COLORS["text_muted"]))
        self.tag_text.setFont(QFont("SF Mono", 6, QFont.Weight.Bold))
        self.tag_text.setPos(-36, 12)

    def _update_appearance(self) -> None:
        type_accent = {
            DeviceType.SERVER: QColor("#3b82f6"),
            DeviceType.ROUTER: QColor("#10b981"),
            DeviceType.FIREWALL: QColor("#ef4444"),
            DeviceType.DNS_SERVER: QColor("#8b5cf6"),
            DeviceType.HOST: QColor("#64748b"),
        }.get(self.device.device_type, QColor("#64748b"))

        is_inferred = self.device.metadata.get("origin") == "INFERRED"
        is_selected = self.isSelected()

        # Fill: Dark engineering slate
        self.setBrush(QBrush(QColor("#111622" if not is_selected else "#1a253c")))

        pen = QPen()
        if is_selected:
            pen.setColor(QColor(COLORS["accent_cyan_glow"]))
            pen.setWidth(2)
        elif is_inferred:
            pen.setColor(QColor(COLORS["inferred"]))
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setWidth(1)
        else:
            pen.setColor(type_accent)
            pen.setWidth(1)

        self.setPen(pen)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: any) -> any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.canvas.update_link_positions()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._update_appearance()
            if value:
                self.canvas.on_node_selected(self.device)
        return super().itemChange(change, value)


class LinkLineItem(QGraphicsLineItem):
    """Clean engineering link line with latency and loss indicators."""

    def __init__(self, link: VirtualLink, node_a: NodeVectorItem, node_b: NodeVectorItem, canvas: "TopologyWorkspace") -> None:
        super().__init__()
        self.link = link
        self.node_a = node_a
        self.node_b = node_b
        self.canvas = canvas
        self.setZValue(-1)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self._update_pen()
        self.update_geometry()

    def _update_pen(self) -> None:
        pen = QPen()
        if self.isSelected():
            pen.setColor(QColor(COLORS["accent_cyan_glow"]))
            pen.setWidth(3)
        elif not self.link.is_up:
            pen.setColor(QColor(COLORS["error"]))
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setWidth(1)
        elif self.link.loss_rate > 0.0:
            pen.setColor(QColor(COLORS["warning"]))
            pen.setWidth(2)
        else:
            pen.setColor(QColor("#2a354c"))
            pen.setWidth(2)
        self.setPen(pen)

    def update_geometry(self) -> None:
        p1 = self.node_a.pos()
        p2 = self.node_b.pos()
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: any) -> any:
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._update_pen()
            if value:
                self.canvas.on_link_selected(self.link)
        return super().itemChange(change, value)


class ContextInspector(QFrame):
    """Right-hand side contextual property inspector for selected nodes and links."""

    device_updated = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"""
            ContextInspector {{
                background-color: {COLORS['bg_panel']};
                border-left: 1px solid {COLORS['border_subtle']};
            }}
            """
        )
        self.setMinimumWidth(260)
        self.setMaximumWidth(360)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 12, 12, 12)
        self.layout.setSpacing(10)

        self.header = SectionHeader("Context Inspector", "Properties of selected element")
        self.layout.addWidget(self.header)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.layout.addWidget(self.content_widget)

        self.layout.addStretch()
        self.show_empty()

    def show_empty(self) -> None:
        self._clear_content()
        lbl = QLabel("Select a node or link on the canvas to inspect its configuration and state.")
        lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        lbl.setWordWrap(True)
        self.content_layout.addWidget(lbl)

    def show_device(self, dev: VirtualDevice) -> None:
        self._clear_content()

        form = QFormLayout()
        form.setSpacing(6)

        # Title & Badges
        top_row = QHBoxLayout()
        name_lbl = QLabel(dev.name)
        name_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #f1f5f9;")
        top_row.addWidget(name_lbl)
        top_row.addStretch()

        origin = dev.metadata.get("origin", "SIMULATED")
        top_row.addWidget(StatusBadge(origin, "inferred" if origin == "INFERRED" else "simulated"))
        self.content_layout.addLayout(top_row)

        form.addRow("Type:", QLabel(dev.device_type.value))
        form.addRow("State:", StatusBadge(dev.state.value, "success" if dev.is_running() else "error"))

        # Primary IP
        ips = dev.get_all_ips()
        ip_str = ", ".join(ips) if ips else "None"
        form.addRow("IP(s):", QLabel(ip_str))
        self.content_layout.addLayout(form)

        # Interfaces List
        if dev.interfaces:
            iface_hdr = QLabel("INTERFACES")
            iface_hdr.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLORS['text_muted']}; margin-top: 8px;")
            self.content_layout.addWidget(iface_hdr)

            for ifc in dev.interfaces.values():
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{ifc.name}: {ifc.ip_address or 'No IP'}"))
                row.addStretch()
                row.addWidget(StatusBadge("UP" if ifc.is_up else "DOWN", "success" if ifc.is_up else "error"))
                self.content_layout.addLayout(row)

        # Actions
        act_hdr = QLabel("ACTIONS")
        act_hdr.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {COLORS['text_muted']}; margin-top: 10px;")
        self.content_layout.addWidget(act_hdr)

        btn_toggle = QPushButton("Stop Device" if dev.is_running() else "Start Device")
        btn_toggle.clicked.connect(lambda: self._toggle_device_state(dev))
        self.content_layout.addWidget(btn_toggle)

    def show_link(self, link: VirtualLink) -> None:
        self._clear_content()

        form = QFormLayout()
        form.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Virtual Link"))
        top_row.addStretch()
        top_row.addWidget(StatusBadge("UP" if link.is_up else "DOWN", "success" if link.is_up else "error"))
        self.content_layout.addLayout(top_row)

        form.addRow("Latency:", QLabel(f"{link.latency_ms} ms"))
        form.addRow("Loss Rate:", QLabel(f"{link.loss_rate * 100:.1f}%"))
        form.addRow("Bandwidth:", QLabel(f"{link.bandwidth_mbps} Mbps"))
        if link.notes:
            form.addRow("Notes:", QLabel(link.notes))
        self.content_layout.addLayout(form)

        btn_toggle = QPushButton("Disable Link" if link.is_up else "Enable Link")
        btn_toggle.clicked.connect(lambda: self._toggle_link_state(link))
        self.content_layout.addWidget(btn_toggle)

    def _toggle_device_state(self, dev: VirtualDevice) -> None:
        if dev.is_running():
            dev.stop()
        else:
            dev.start()
        self.show_device(dev)
        self.device_updated.emit()

    def _toggle_link_state(self, link: VirtualLink) -> None:
        link.is_up = not link.is_up
        self.show_link(link)
        self.device_updated.emit()

    def _clear_content(self) -> None:
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                # Clear sub-layout
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()


class CanvasGraphicsView(QGraphicsView):
    """Grid-rendered, zoomable, pannable interactive viewport."""

    def __init__(self, scene: QGraphicsScene, parent: Optional[QWidget] = None) -> None:
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor(COLORS["bg_workspace"])))
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Draw subtle engineering grid dots."""
        super().drawBackground(painter, rect)
        painter.save()
        painter.setPen(QPen(QColor(COLORS["border_subtle"]), 1))

        grid_size = 24
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        for x in range(left, int(rect.right()), grid_size):
            for y in range(top, int(rect.bottom()), grid_size):
                painter.drawPoint(x, y)
        painter.restore()

    def wheelEvent(self, event) -> None:
        """Smooth zoom in/out with mouse wheel."""
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(zoom_factor, zoom_factor)


class TopologyWorkspace(QWidget):
    """Complete Topology Workspace: Canvas, Toolbar, Grid, and Context Inspector."""

    def __init__(self, network: VirtualNetwork, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.network = network
        self.node_items: Dict[str, NodeVectorItem] = {}
        self.link_items: Dict[str, LinkLineItem] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Topology Toolbar
        self.toolbar = QFrame()
        self.toolbar.setStyleSheet(f"background-color: {COLORS['bg_panel']}; border-bottom: 1px solid {COLORS['border_subtle']}; padding: 4px;")
        t_layout = QHBoxLayout(self.toolbar)
        t_layout.setContentsMargins(8, 4, 8, 4)
        t_layout.setSpacing(6)

        title = QLabel("TOPOLOGY WORKSPACE")
        title.setStyleSheet("font-weight: 700; color: #f1f5f9; letter-spacing: 0.8px;")
        t_layout.addWidget(title)

        t_layout.addStretch()

        self.btn_fit = QPushButton("Fit to View")
        self.btn_fit.setObjectName("btnGhost")
        self.btn_fit.clicked.connect(self.fit_to_view)
        t_layout.addWidget(self.btn_fit)

        self.btn_reset_zoom = QPushButton("100%")
        self.btn_reset_zoom.setObjectName("btnGhost")
        self.btn_reset_zoom.clicked.connect(lambda: self.view.resetTransform())
        t_layout.addWidget(self.btn_reset_zoom)

        layout.addWidget(self.toolbar)

        # Splitter: Canvas Left, Inspector Right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Canvas Scene & View
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-2000, -2000, 4000, 4000)
        self.view = CanvasGraphicsView(self.scene, self)
        splitter.addWidget(self.view)

        # Inspector
        self.inspector = ContextInspector(self)
        self.inspector.device_updated.connect(self.update_link_positions)
        splitter.addWidget(self.inspector)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        self.render_topology()

    def render_topology(self) -> None:
        """Render all network devices and links."""
        self.scene.clear()
        self.node_items.clear()
        self.link_items.clear()

        dev_list = list(self.network.devices.values())
        radius = max(180, len(dev_list) * 50)
        center_x, center_y = 0, 0

        for i, dev in enumerate(dev_list):
            angle = (2 * math.pi * i) / max(1, len(dev_list))
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)

            item = NodeVectorItem(dev, x, y, self)
            self.scene.addItem(item)
            self.node_items[dev.device_id] = item

        for link in self.network.links.values():
            node_a = self.node_items.get(link.node_a_id)
            node_b = self.node_items.get(link.node_b_id)
            if node_a and node_b:
                l_item = LinkLineItem(link, node_a, node_b, self)
                self.scene.addItem(l_item)
                self.link_items[link.link_id] = l_item

        self.fit_to_view()

    def update_link_positions(self) -> None:
        for l_item in self.link_items.values():
            l_item.update_geometry()
            l_item._update_pen()

    def fit_to_view(self) -> None:
        if self.node_items:
            items_rect = self.scene.itemsBoundingRect()
            self.view.fitInView(items_rect.adjusted(-60, -60, 60, 60), Qt.AspectRatioMode.KeepAspectRatio)

    def on_node_selected(self, device: VirtualDevice) -> None:
        self.inspector.show_device(device)

    def on_link_selected(self, link: VirtualLink) -> None:
        self.inspector.show_link(link)
