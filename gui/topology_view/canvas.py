"""Interactive PySide6 topology canvas rendering virtual devices and links."""

from __future__ import annotations

from typing import Dict, Optional
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
)

from core.device import DeviceType, VirtualDevice
from core.network import VirtualLink, VirtualNetwork


class NodeGraphicsItem(QGraphicsEllipseItem):
    """Visual representation of a virtual device node."""

    def __init__(self, device: VirtualDevice, x: float, y: float, canvas: "TopologyCanvas") -> None:
        super().__init__(-30, -30, 60, 60)
        self.device = device
        self.canvas = canvas
        self.setPos(x, y)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        # Style by device type
        color_map = {
            DeviceType.SERVER: QColor("#3b82f6"),
            DeviceType.ROUTER: QColor("#10b981"),
            DeviceType.FIREWALL: QColor("#ef4444"),
            DeviceType.DNS_SERVER: QColor("#8b5cf6"),
            DeviceType.HOST: QColor("#64748b"),
        }
        color = color_map.get(device.device_type, QColor("#64748b"))

        # Highlight inferred devices with a dashed border
        is_inferred = device.metadata.get("origin") == "INFERRED"
        pen = QPen(QColor("#f59e0b" if is_inferred else "#ffffff"), 2)
        if is_inferred:
            pen.setStyle(Qt.PenStyle.DashLine)

        self.setBrush(QBrush(color))
        self.setPen(pen)

        # Label
        self.label = QGraphicsTextItem(device.name, self)
        self.label.setDefaultTextColor(QColor("#ffffff"))
        self.label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.label.setPos(-25, 32)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: any) -> any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.canvas.update_link_positions()
        return super().itemChange(change, value)


class LinkGraphicsItem(QGraphicsLineItem):
    """Visual line connecting two virtual device nodes."""

    def __init__(self, link: VirtualLink, node_a: NodeGraphicsItem, node_b: NodeGraphicsItem) -> None:
        super().__init__()
        self.link = link
        self.node_a = node_a
        self.node_b = node_b
        pen = QPen(QColor("#38bdf8" if link.is_up else "#dc2626"), 2)
        if not link.is_up:
            pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setZValue(-1)
        self.update_geometry()

    def update_geometry(self) -> None:
        p1 = self.node_a.pos()
        p2 = self.node_b.pos()
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())


class TopologyCanvas(QGraphicsView):
    """Zoomable, pannable, interactive topology canvas."""

    node_selected = Signal(str)  # Emits device_id

    def __init__(self, parent: Optional[any] = None) -> None:
        super().__init__(parent)
        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor("#0f141c")))
        self.node_items: Dict[str, NodeGraphicsItem] = {}
        self.link_items: Dict[str, LinkGraphicsItem] = {}

    def render_network(self, network: VirtualNetwork) -> None:
        """Render devices and links from a VirtualNetwork."""
        self.scene_obj.clear()
        self.node_items.clear()
        self.link_items.clear()

        # Place nodes in a circle or grid
        import math
        dev_list = list(network.devices.values())
        radius = max(150, len(dev_list) * 40)
        center_x, center_y = 300, 250

        for i, dev in enumerate(dev_list):
            angle = (2 * math.pi * i) / max(1, len(dev_list))
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            node_item = NodeGraphicsItem(dev, x, y, self)
            self.scene_obj.addItem(node_item)
            self.node_items[dev.device_id] = node_item

        for link in network.links.values():
            node_a = self.node_items.get(link.node_a_id)
            node_b = self.node_items.get(link.node_b_id)
            if node_a and node_b:
                link_item = LinkGraphicsItem(link, node_a, node_b)
                self.scene_obj.addItem(link_item)
                self.link_items[link.link_id] = link_item

    def update_link_positions(self) -> None:
        """Update line positions when nodes are dragged."""
        for link_item in self.link_items.values():
            link_item.update_geometry()
