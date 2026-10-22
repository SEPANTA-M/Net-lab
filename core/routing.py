"""Virtual routing engine, routing table models, and longest-prefix matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import ipaddress
import logging
from typing import Dict, List, Optional, Tuple
import uuid

from core.device import DeviceType, VirtualDevice, VirtualInterface
from core.packet import Packet, PacketState

logger = logging.getLogger("network_lab.routing")


class RouteType(str, Enum):
    """Categorization of routing table entries."""

    DIRECT = "DIRECT"
    STATIC = "STATIC"
    DEFAULT = "DEFAULT"


@dataclass
class RouteEntry:
    """A single routing table entry on a virtual router or device."""

    destination_network: str  # e.g., "192.168.1.0/24" or "0.0.0.0/0"
    next_hop: Optional[str] = None  # IP of next hop; None if directly connected
    interface_id: Optional[str] = None  # Outgoing interface ID
    metric: int = 1
    route_type: RouteType = RouteType.STATIC
    is_active: bool = True
    route_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate network CIDR and next-hop IP."""
        try:
            self.network_obj = ipaddress.ip_network(self.destination_network, strict=False)
        except ValueError as err:
            raise ValueError(f"Invalid destination network '{self.destination_network}': {err}") from err

        if self.next_hop:
            try:
                ipaddress.ip_address(self.next_hop)
            except ValueError as err:
                raise ValueError(f"Invalid next_hop IP '{self.next_hop}': {err}") from err

        if self.metric < 0:
            raise ValueError(f"Metric cannot be negative: {self.metric}")

    @property
    def prefix_length(self) -> int:
        """Return the subnet mask prefix length for longest prefix matching."""
        return self.network_obj.prefixlen

    def matches(self, ip_str: str) -> bool:
        """Check if target IP falls within this route's destination network."""
        if not self.is_active:
            return False
        try:
            target_ip = ipaddress.ip_address(ip_str)
            return target_ip in self.network_obj
        except ValueError:
            return False


class RoutingTable:
    """Manages routing entries with Longest-Prefix Matching and metric arbitration."""

    def __init__(self) -> None:
        self.routes: List[RouteEntry] = []

    def add_route(self, route: RouteEntry) -> RouteEntry:
        """Add a route to the table."""
        # Replace existing route if same destination, next_hop, and interface
        for idx, r in enumerate(self.routes):
            if (
                r.destination_network == route.destination_network
                and r.next_hop == route.next_hop
                and r.interface_id == route.interface_id
            ):
                self.routes[idx] = route
                return route
        self.routes.append(route)
        return route

    def remove_route(self, route_id: str) -> Optional[RouteEntry]:
        """Remove a route entry by ID."""
        for idx, r in enumerate(self.routes):
            if r.route_id == route_id:
                return self.routes.pop(idx)
        return None

    def lookup(self, destination_ip: str) -> Optional[RouteEntry]:
        """Perform Longest-Prefix Match (LPM) on active routes.

        If multiple routes match with identical prefix lengths, selects the lowest metric.
        """
        matching_routes: List[RouteEntry] = []
        for r in self.routes:
            if r.matches(destination_ip):
                matching_routes.append(r)

        if not matching_routes:
            return None

        # Sort by:
        # 1. prefix_length descending (longest prefix match first, e.g. /32 before /24 before /0)
        # 2. metric ascending (lower metric is preferred)
        matching_routes.sort(key=lambda entry: (-entry.prefix_length, entry.metric))
        return matching_routes[0]

    def all_routes(self) -> List[RouteEntry]:
        """Return a copy of all routing entries."""
        return list(self.routes)


class VirtualRouter(VirtualDevice):
    """Virtual router device with routing table and packet forwarding capabilities."""

    def __init__(self, name: str, device_id: Optional[str] = None) -> None:
        if device_id:
            super().__init__(name=name, device_type=DeviceType.ROUTER, device_id=device_id)
        else:
            super().__init__(name=name, device_type=DeviceType.ROUTER)
        self.routing_table = RoutingTable()

    def add_interface(self, interface: VirtualInterface) -> VirtualInterface:
        """Add interface and automatically register a DIRECT connected route."""
        added = super().add_interface(interface)
        if interface.ip_address and interface.network:
            direct_route = RouteEntry(
                destination_network=str(interface.network),
                next_hop=None,
                interface_id=interface.interface_id,
                metric=0,
                route_type=RouteType.DIRECT,
                description=f"Directly connected to {interface.name}",
            )
            self.routing_table.add_route(direct_route)
        return added

    def add_static_route(
        self,
        destination_network: str,
        next_hop: Optional[str] = None,
        interface_id: Optional[str] = None,
        metric: int = 1,
        description: str = "",
    ) -> RouteEntry:
        """Add a static or default route entry."""
        rtype = RouteType.DEFAULT if destination_network in ("0.0.0.0/0", "::/0") else RouteType.STATIC
        route = RouteEntry(
            destination_network=destination_network,
            next_hop=next_hop,
            interface_id=interface_id,
            metric=metric,
            route_type=rtype,
            description=description,
        )
        return self.routing_table.add_route(route)

    def route_lookup(self, dst_ip: str) -> Optional[RouteEntry]:
        """Look up destination IP in router's routing table."""
        return self.routing_table.lookup(dst_ip)
