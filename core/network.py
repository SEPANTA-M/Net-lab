"""Virtual link and internal virtual network simulation engine."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import random
from typing import Dict, List, Optional, Tuple
import uuid

from core.device import DeviceState, DeviceType, VirtualDevice, VirtualInterface
from core.firewall import FirewallAction, VirtualFirewall
from core.packet import Packet, PacketState
from core.routing import RouteType

logger = logging.getLogger("network_lab.core")


@dataclass
class VirtualLink:
    """Represents a virtual link between two virtual interfaces.

    This connection exists purely in memory and does not utilize physical or TAP/TUN interfaces.
    """

    node_a_id: str
    interface_a_id: str
    node_b_id: str
    interface_b_id: str
    link_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_up: bool = True
    bandwidth_mbps: float = 1000.0
    latency_ms: float = 1.0
    loss_rate: float = 0.0  # Fraction between 0.0 and 1.0
    notes: str = ""

    def connects(self, node_id: str, interface_id: Optional[str] = None) -> bool:
        """Check if this link connects to a given node and optional interface."""
        if interface_id:
            return (self.node_a_id == node_id and self.interface_a_id == interface_id) or (
                self.node_b_id == node_id and self.interface_b_id == interface_id
            )
        return self.node_a_id == node_id or self.node_b_id == node_id

    def get_peer(self, node_id: str, interface_id: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """Given one node end, return the peer (peer_node_id, peer_interface_id)."""
        if self.node_a_id == node_id and (interface_id is None or self.interface_a_id == interface_id):
            return (self.node_b_id, self.interface_b_id)
        if self.node_b_id == node_id and (interface_id is None or self.interface_b_id == interface_id):
            return (self.node_a_id, self.interface_a_id)
        return None


class VirtualNetwork:
    """Core in-memory virtual network simulation engine.

    Responsibilities:
    - Register virtual devices and virtual links.
    - Resolve virtual IP addresses to devices/interfaces.
    - Validate topology consistency.
    - Deliver packets through directly connected and multi-hop virtual paths.
    - Apply simulated latency and packet loss safely.
    - Record route history and provide unambiguous failure reasons.

    Security Guarantee:
    - Never opens sockets, raw sockets, or operating system network hooks.
    - Packets exist solely as Python object graphs in memory.
    """

    def __init__(self, random_seed: Optional[int] = None) -> None:
        self.devices: Dict[str, VirtualDevice] = {}
        self.links: Dict[str, VirtualLink] = {}
        self.rng = random.Random(random_seed)

    def set_random_seed(self, seed: Optional[int]) -> None:
        """Set seed for deterministic simulation of loss and jitter."""
        self.rng = random.Random(seed)

    def add_device(self, device: VirtualDevice) -> VirtualDevice:
        """Register a virtual device."""
        if device.device_id in self.devices:
            raise ValueError(f"Device with ID '{device.device_id}' already registered")
        self.devices[device.device_id] = device
        return device

    def remove_device(self, device_id: str) -> Optional[VirtualDevice]:
        """Remove a device and all attached links."""
        dev = self.devices.pop(device_id, None)
        if dev:
            # Remove attached links
            to_remove = [lid for lid, link in self.links.items() if link.connects(device_id)]
            for lid in to_remove:
                self.remove_link(lid)
        return dev

    def get_device(self, device_id: str) -> Optional[VirtualDevice]:
        """Retrieve a device by ID."""
        return self.devices.get(device_id)

    def connect(
        self,
        node_a_id: str,
        interface_a_id: str,
        node_b_id: str,
        interface_b_id: str,
        latency_ms: float = 1.0,
        loss_rate: float = 0.0,
        bandwidth_mbps: float = 1000.0,
        link_id: Optional[str] = None,
    ) -> VirtualLink:
        """Connect two device interfaces with a virtual link."""
        dev_a = self.get_device(node_a_id)
        if not dev_a:
            raise ValueError(f"Node A '{node_a_id}' does not exist")
        dev_b = self.get_device(node_b_id)
        if not dev_b:
            raise ValueError(f"Node B '{node_b_id}' does not exist")

        iface_a = dev_a.get_interface(interface_a_id)
        if not iface_a:
            raise ValueError(f"Interface A '{interface_a_id}' not found on device '{node_a_id}'")
        iface_b = dev_b.get_interface(interface_b_id)
        if not iface_b:
            raise ValueError(f"Interface B '{interface_b_id}' not found on device '{node_b_id}'")

        if loss_rate < 0.0 or loss_rate > 1.0:
            raise ValueError("loss_rate must be between 0.0 and 1.0")

        link = VirtualLink(
            node_a_id=node_a_id,
            interface_a_id=interface_a_id,
            node_b_id=node_b_id,
            interface_b_id=interface_b_id,
            link_id=link_id if link_id else str(uuid.uuid4()),
            latency_ms=max(0.0, latency_ms),
            loss_rate=loss_rate,
            bandwidth_mbps=max(0.1, bandwidth_mbps),
        )

        iface_a.connected_link_id = link.link_id
        iface_b.connected_link_id = link.link_id
        self.links[link.link_id] = link
        return link

    def remove_link(self, link_id: str) -> Optional[VirtualLink]:
        """Remove a virtual link and detach from interface references."""
        link = self.links.pop(link_id, None)
        if link:
            dev_a = self.get_device(link.node_a_id)
            if dev_a:
                iface_a = dev_a.get_interface(link.interface_a_id)
                if iface_a and iface_a.connected_link_id == link_id:
                    iface_a.connected_link_id = None
            dev_b = self.get_device(link.node_b_id)
            if dev_b:
                iface_b = dev_b.get_interface(link.interface_b_id)
                if iface_b and iface_b.connected_link_id == link_id:
                    iface_b.connected_link_id = None
        return link

    def find_device_by_ip(self, ip_str: str) -> Optional[Tuple[VirtualDevice, VirtualInterface]]:
        """Locate the virtual device and specific interface assigned to ip_str."""
        for dev in self.devices.values():
            for iface in dev.interfaces.values():
                if iface.ip_address == ip_str:
                    return (dev, iface)
        return None

    def get_links_for_device(self, device_id: str) -> List[VirtualLink]:
        """Return all links attached to a device."""
        return [l for l in self.links.values() if l.connects(device_id)]

    def transmit(self, packet: Packet) -> Packet:
        """Transmit an isolated packet through the virtual network.

        Supports direct delivery and multi-hop routing across virtual routers
        using longest-prefix matching.

        Does NOT transmit anything onto physical sockets.
        """
        packet.state = PacketState.ROUTING

        # Check source device existence
        src_res = self.find_device_by_ip(packet.src_ip)
        if not src_res:
            packet.mark_dropped(f"Source IP '{packet.src_ip}' not found on any virtual device")
            return packet

        src_dev, src_iface = src_res
        if not src_dev.is_running():
            packet.mark_dropped(f"Source device '{src_dev.name}' is STOPPED")
            return packet
        if not src_iface.is_up:
            packet.mark_dropped(f"Source interface '{src_iface.name}' is DOWN")
            return packet

        packet.record_hop(
            device_id=src_dev.device_id,
            interface_id=src_iface.interface_id,
            action="ORIGINATE",
            detail=f"Packet originated at {src_dev.name} ({packet.src_ip})",
        )

        # Loopback check: source is destination
        if packet.src_ip == packet.dst_ip:
            packet.record_hop(
                device_id=src_dev.device_id,
                interface_id=src_iface.interface_id,
                action="DELIVER",
                detail="Delivered to local loopback",
            )
            packet.mark_delivered("Delivered locally (loopback)")
            return packet

        # Check destination device existence
        dst_res = self.find_device_by_ip(packet.dst_ip)
        if not dst_res:
            packet.mark_dropped(f"Destination IP '{packet.dst_ip}' unreachable: no virtual host matches")
            return packet

        # Iterative hop-by-hop forwarding starting from source
        current_dev = src_dev
        current_iface = src_iface

        # Avoid infinite simulation loops if there is a circular routing misconfiguration
        max_hops = packet.ttl + 5
        hops_taken = 0

        while hops_taken < max_hops:
            hops_taken += 1

            # 1. Did we reach a device hosting dst_ip?
            if current_dev.has_ip(packet.dst_ip):
                target_iface = next(
                    (ifc for ifc in current_dev.interfaces.values() if ifc.ip_address == packet.dst_ip),
                    current_iface,
                )
                if not current_dev.is_running():
                    packet.mark_dropped(f"Destination device '{current_dev.name}' is STOPPED")
                    return packet
                if not target_iface.is_up:
                    packet.mark_dropped(f"Destination interface '{target_iface.name}' is DOWN")
                    return packet

                packet.record_hop(
                    device_id=current_dev.device_id,
                    interface_id=target_iface.interface_id,
                    action="DELIVER",
                    detail=f"Delivered to {current_dev.name} ({packet.dst_ip})",
                )
                packet.mark_delivered(f"Successfully delivered to {current_dev.name}")
                return packet

            # 2. If directly connected to dst_ip's device via any link from current device
            # Only do direct delivery if current_dev is not a router, or if router routing table confirms direct connected route
            is_direct_subnet = False
            if hasattr(current_dev, "routing_table"):
                route = current_dev.route_lookup(packet.dst_ip)
                if route and route.route_type == RouteType.DIRECT:
                    is_direct_subnet = True
            else:
                is_direct_subnet = True

            if is_direct_subnet:
                direct_link = self._find_link_to_destination(current_dev, packet.dst_ip)
                if direct_link:
                    peer = direct_link.get_peer(current_dev.device_id)
                    if peer:
                        next_dev_id, next_iface_id = peer
                        next_dev = self.get_device(next_dev_id)
                        if not direct_link.is_up:
                            packet.mark_dropped(f"Virtual link between '{current_dev.name}' and '{next_dev.name if next_dev else 'next hop'}' is DOWN")
                            return packet

                        # Check link loss
                        if direct_link.loss_rate > 0.0 and self.rng.random() < direct_link.loss_rate:
                            packet.mark_dropped(f"Packet lost due to simulated link loss rate ({direct_link.loss_rate * 100:.1f}%)")
                            return packet

                        packet.simulated_latency_ms += direct_link.latency_ms
                        if packet.decrement_ttl() <= 0:
                            return packet

                        # If current_dev is a router forwarding to destination, record the routing hop
                        if hasattr(current_dev, "routing_table") and current_dev != src_dev:
                            packet.record_hop(
                                device_id=current_dev.device_id,
                                interface_id=direct_link.interface_a_id if direct_link.node_a_id == current_dev.device_id else direct_link.interface_b_id,
                                action="ROUTED_DIRECT",
                                detail=f"Router {current_dev.name} forwarded directly to destination {packet.dst_ip}",
                            )

                        current_dev = next_dev
                        current_iface = current_dev.get_interface(next_iface_id) if current_dev else None
                        continue

            # 3. Router forwarding lookup
            if hasattr(current_dev, "routing_table"):
                route = current_dev.route_lookup(packet.dst_ip)
                if not route:
                    packet.mark_dropped(f"No route to destination '{packet.dst_ip}' at router '{current_dev.name}'")
                    return packet

                # Determine next hop and outgoing interface
                out_iface_id = route.interface_id
                next_hop_ip = route.next_hop

                # Find link attached to out_iface or to next_hop
                out_link, next_dev, next_iface = self._resolve_route_link(current_dev, out_iface_id, next_hop_ip, packet.dst_ip)
                if not out_link or not next_dev:
                    packet.mark_dropped(f"Routing lookup succeeded but no active link found for route to '{packet.dst_ip}' at '{current_dev.name}'")
                    return packet

                if not out_link.is_up:
                    packet.mark_dropped(f"Virtual link via '{out_link.link_id}' at '{current_dev.name}' is DOWN")
                    return packet

                if out_link.loss_rate > 0.0 and self.rng.random() < out_link.loss_rate:
                    packet.mark_dropped(f"Packet lost due to simulated link loss rate ({out_link.loss_rate * 100:.1f}%)")
                    return packet

                packet.simulated_latency_ms += out_link.latency_ms
                packet.record_hop(
                    device_id=current_dev.device_id,
                    interface_id=out_iface_id,
                    action="ROUTED",
                    detail=f"Routed via {route.destination_network} (next-hop: {route.next_hop or 'direct'})",
                )

                if packet.decrement_ttl() <= 0:
                    return packet

                # Check if next device is a VirtualFirewall
                if isinstance(next_dev, VirtualFirewall) or getattr(next_dev, "device_type", None) == DeviceType.FIREWALL:
                    decision = next_dev.evaluate(packet)
                    if decision.action == FirewallAction.DENY:
                        packet.record_hop(
                            device_id=next_dev.device_id,
                            interface_id=next_iface_id,
                            action="FIREWALL_DENY",
                            detail=f"Denied by firewall rule '{decision.rule_description}'",
                        )
                        packet.mark_dropped(f"Firewall DENIED packet: {decision.rule_description}")
                        return packet
                    elif decision.action == FirewallAction.REJECT:
                        packet.record_hop(
                            device_id=next_dev.device_id,
                            interface_id=next_iface_id,
                            action="FIREWALL_REJECT",
                            detail=f"Rejected by firewall rule '{decision.rule_description}'",
                        )
                        packet.mark_dropped(f"Firewall REJECTED packet: {decision.rule_description}")
                        return packet
                    else:
                        packet.record_hop(
                            device_id=next_dev.device_id,
                            interface_id=next_iface_id,
                            action="FIREWALL_ALLOW",
                            detail=f"Allowed by firewall rule '{decision.rule_description}'",
                        )

                current_dev = next_dev
                current_iface = next_iface
                continue

            # 4. If current device is a Host/Server without a router table, find its default gateway or connected router
            gw_link, gw_dev, gw_iface = self._find_gateway_for_host(current_dev)
            if gw_link and gw_dev:
                if not gw_link.is_up:
                    packet.mark_dropped(f"Virtual link between '{current_dev.name}' and gateway '{gw_dev.name}' is DOWN")
                    return packet

                if gw_link.loss_rate > 0.0 and self.rng.random() < gw_link.loss_rate:
                    packet.mark_dropped(f"Packet lost due to simulated link loss rate ({gw_link.loss_rate * 100:.1f}%)")
                    return packet

                packet.simulated_latency_ms += gw_link.latency_ms
                packet.record_hop(
                    device_id=current_dev.device_id,
                    interface_id=current_iface.interface_id if current_iface else None,
                    action="FORWARD_GATEWAY",
                    detail=f"Forwarded from {current_dev.name} to gateway {gw_dev.name}",
                )

                if packet.decrement_ttl() <= 0:
                    return packet

                current_dev = gw_dev
                current_iface = gw_iface
                continue

            # If we reached here, no forwarding path exists
            packet.mark_dropped(f"No direct link or route from '{current_dev.name}' toward '{packet.dst_ip}'")
            return packet

        packet.mark_timed_out("Max simulation hops exceeded (possible routing loop)")
        return packet

    def _find_link_to_destination(self, current_dev: VirtualDevice, dst_ip: str) -> Optional[VirtualLink]:
        """Check if any interface of current_dev shares a link with the device holding dst_ip."""
        dst_res = self.find_device_by_ip(dst_ip)
        if not dst_res:
            return None
        dst_dev, _ = dst_res
        return self._find_link_between_devices(current_dev.device_id, dst_dev.device_id)

    def _find_gateway_for_host(self, host: VirtualDevice) -> Tuple[Optional[VirtualLink], Optional[VirtualDevice], Optional[VirtualInterface]]:
        """Find a connected router serving as gateway for host."""
        for link in self.get_links_for_device(host.device_id):
            peer = link.get_peer(host.device_id)
            if peer:
                p_dev_id, p_iface_id = peer
                p_dev = self.get_device(p_dev_id)
                if p_dev and hasattr(p_dev, "routing_table"):
                    return link, p_dev, p_dev.get_interface(p_iface_id)
        return None, None, None

    def _resolve_route_link(
        self,
        router: VirtualDevice,
        out_iface_id: Optional[str],
        next_hop_ip: Optional[str],
        dst_ip: str,
    ) -> Tuple[Optional[VirtualLink], Optional[VirtualDevice], Optional[VirtualInterface]]:
        """Resolve the outgoing link and next hop device from route details."""
        # Case A: next_hop IP specified
        if next_hop_ip:
            next_hop_res = self.find_device_by_ip(next_hop_ip)
            if next_hop_res:
                next_dev, next_iface = next_hop_res
                link = self._find_link_between_devices(router.device_id, next_dev.device_id)
                return link, next_dev, next_iface

        # Case B: Outgoing interface specified for directly connected subnet
        if out_iface_id:
            out_iface = router.get_interface(out_iface_id)
            if out_iface and out_iface.connected_link_id:
                link = self.links.get(out_iface.connected_link_id)
                if link:
                    peer = link.get_peer(router.device_id, out_iface_id)
                    if peer:
                        next_dev = self.get_device(peer[0])
                        next_iface = next_dev.get_interface(peer[1]) if next_dev else None
                        return link, next_dev, next_iface

        # Case C: Check directly connected subnet matching dst_ip
        dst_res = self.find_device_by_ip(dst_ip)
        if dst_res:
            dst_dev, dst_iface = dst_res
            link = self._find_link_between_devices(router.device_id, dst_dev.device_id)
            if link:
                return link, dst_dev, dst_iface

        return None, None, None

    def _find_link_between_interfaces(self, iface_a: str, iface_b: str) -> Optional[VirtualLink]:
        for link in self.links.values():
            if (link.interface_a_id == iface_a and link.interface_b_id == iface_b) or (
                link.interface_a_id == iface_b and link.interface_b_id == iface_a
            ):
                return link
        return None

    def _find_link_between_devices(self, dev_a_id: str, dev_b_id: str) -> Optional[VirtualLink]:
        for link in self.links.values():
            if (link.node_a_id == dev_a_id and link.node_b_id == dev_b_id) or (
                link.node_a_id == dev_b_id and link.node_b_id == dev_a_id
            ):
                return link
        return None
