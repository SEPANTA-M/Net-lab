"""SQLite database storage and project persistence for Network Lab."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from core.device import DeviceType, VirtualDevice, VirtualInterface
from core.firewall import FirewallAction, FirewallRule, VirtualFirewall
from core.network import VirtualLink, VirtualNetwork
from core.routing import RouteEntry, RouteType, VirtualRouter
from core.server import VirtualServer, VirtualService


class StorageManager:
    """Manages SQLite persistence for projects, topologies, rules, and scenarios."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Create necessary database tables."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                topology_json TEXT
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scenarios (
                scenario_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                project_id TEXT,
                config_json TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
            );
            """
        )
        self.conn.commit()

    def save_project(self, project_id: str, name: str, description: str, network: VirtualNetwork) -> None:
        """Serialize and save a virtual network project to SQLite."""
        topology_dict = self.network_to_dict(network)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO projects (project_id, name, description, topology_json)
            VALUES (?, ?, ?, ?)
            """,
            (project_id, name, description, json.dumps(topology_dict)),
        )
        self.conn.commit()

    def load_project(self, project_id: str) -> Optional[tuple[str, str, VirtualNetwork]]:
        """Load and deserialize a project by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, description, topology_json FROM projects WHERE project_id = ?", (project_id,))
        row = cursor.fetchone()
        if not row:
            return None

        topology_dict = json.loads(row["topology_json"])
        network = self.dict_to_network(topology_dict)
        return (row["name"], row["description"], network)

    def list_projects(self) -> List[Dict[str, Any]]:
        """List summary of saved projects."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT project_id, name, description, created_at FROM projects ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def network_to_dict(net: VirtualNetwork) -> Dict[str, Any]:
        """Convert a VirtualNetwork object to a structured dictionary."""
        data: Dict[str, Any] = {"devices": [], "links": []}

        for dev in net.devices.values():
            dev_data: Dict[str, Any] = {
                "device_id": dev.device_id,
                "name": dev.name,
                "device_type": dev.device_type.value,
                "state": dev.state.value,
                "metadata": dev.metadata,
                "interfaces": [
                    {
                        "interface_id": ifc.interface_id,
                        "name": ifc.name,
                        "ip_address": ifc.ip_address,
                        "subnet_mask": ifc.subnet_mask,
                        "mac_address": ifc.mac_address,
                        "is_up": ifc.is_up,
                    }
                    for ifc in dev.interfaces.values()
                ],
            }

            if isinstance(dev, VirtualRouter):
                dev_data["routes"] = [
                    {
                        "destination_network": r.destination_network,
                        "next_hop": r.next_hop,
                        "interface_id": r.interface_id,
                        "metric": r.metric,
                        "route_type": r.route_type.value,
                        "description": r.description,
                    }
                    for r in dev.routing_table.all_routes()
                ]
            elif isinstance(dev, VirtualFirewall):
                dev_data["firewall"] = dev.to_dict()

            data["devices"].append(dev_data)

        for link in net.links.values():
            data["links"].append(
                {
                    "link_id": link.link_id,
                    "node_a_id": link.node_a_id,
                    "interface_a_id": link.interface_a_id,
                    "node_b_id": link.node_b_id,
                    "interface_b_id": link.interface_b_id,
                    "latency_ms": link.latency_ms,
                    "loss_rate": link.loss_rate,
                    "bandwidth_mbps": link.bandwidth_mbps,
                    "is_up": link.is_up,
                    "notes": link.notes,
                }
            )

        return data

    @classmethod
    def dict_to_network(cls, data: Dict[str, Any]) -> VirtualNetwork:
        """Reconstruct a VirtualNetwork from a dictionary safely."""
        net = VirtualNetwork()

        for d in data.get("devices", []):
            dtype = d.get("device_type", DeviceType.HOST.value)
            dev_id = d.get("device_id", str(uuid.uuid4()))
            name = d.get("name", "Device")

            dev: VirtualDevice
            if dtype == DeviceType.ROUTER.value:
                dev = VirtualRouter(name=name, device_id=dev_id)
                for r_data in d.get("routes", []):
                    dev.add_static_route(
                        destination_network=r_data["destination_network"],
                        next_hop=r_data.get("next_hop"),
                        interface_id=r_data.get("interface_id"),
                        metric=r_data.get("metric", 1),
                        description=r_data.get("description", ""),
                    )
            elif dtype == DeviceType.FIREWALL.value:
                dev = VirtualFirewall.from_dict(d.get("firewall", {"name": name, "device_id": dev_id}))
            elif dtype == DeviceType.SERVER.value:
                dev = VirtualServer(name=name, device_id=dev_id)
            else:
                dev = VirtualDevice(name=name, device_type=DeviceType(dtype), device_id=dev_id)

            dev.metadata = d.get("metadata", {})

            for ifc_data in d.get("interfaces", []):
                ifc = VirtualInterface(
                    name=ifc_data["name"],
                    ip_address=ifc_data.get("ip_address"),
                    subnet_mask=ifc_data.get("subnet_mask", "255.255.255.0"),
                    mac_address=ifc_data.get("mac_address"),
                    interface_id=ifc_data.get("interface_id", str(uuid.uuid4())),
                    is_up=ifc_data.get("is_up", True),
                )
                dev.add_interface(ifc)

            net.add_device(dev)

        for l_data in data.get("links", []):
            net.connect(
                node_a_id=l_data["node_a_id"],
                interface_a_id=l_data["interface_a_id"],
                node_b_id=l_data["node_b_id"],
                interface_b_id=l_data["interface_b_id"],
                latency_ms=l_data.get("latency_ms", 1.0),
                loss_rate=l_data.get("loss_rate", 0.0),
                bandwidth_mbps=l_data.get("bandwidth_mbps", 1000.0),
                link_id=l_data.get("link_id"),
            )

        return net
