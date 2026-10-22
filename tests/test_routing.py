"""Tests for Virtual Routing engine, routing table, and longest-prefix matching."""

import pytest
from core.device import DeviceType, VirtualDevice, VirtualInterface
from core.network import VirtualNetwork
from core.packet import Packet, PacketState, Protocol
from core.routing import RouteEntry, RouteType, RoutingTable, VirtualRouter
from core.server import VirtualServer


def test_route_entry_validation():
    # Valid static route
    r = RouteEntry(destination_network="192.168.1.0/24", next_hop="10.0.0.1", metric=1)
    assert r.prefix_length == 24
    assert r.matches("192.168.1.55")
    assert not r.matches("192.168.2.1")

    # Invalid network CIDR
    with pytest.raises(ValueError, match="Invalid destination network"):
        RouteEntry(destination_network="not_a_cidr")

    # Invalid next hop IP
    with pytest.raises(ValueError, match="Invalid next_hop IP"):
        RouteEntry(destination_network="10.0.0.0/8", next_hop="invalid_ip")


def test_longest_prefix_matching():
    table = RoutingTable()

    # Default route: 0.0.0.0/0
    r_default = RouteEntry(destination_network="0.0.0.0/0", next_hop="172.16.0.1", metric=10)
    # Less specific subnet: 10.0.0.0/16
    r_wide = RouteEntry(destination_network="10.0.0.0/16", next_hop="172.16.0.2", metric=5)
    # More specific subnet: 10.0.1.0/24
    r_narrow = RouteEntry(destination_network="10.0.1.0/24", next_hop="172.16.0.3", metric=5)
    # Host route: 10.0.1.50/32
    r_host = RouteEntry(destination_network="10.0.1.50/32", next_hop="172.16.0.4", metric=5)

    table.add_route(r_default)
    table.add_route(r_wide)
    table.add_route(r_narrow)
    table.add_route(r_host)

    # 1. Exact host match (/32)
    best = table.lookup("10.0.1.50")
    assert best == r_host

    # 2. Subnet match (/24)
    best = table.lookup("10.0.1.99")
    assert best == r_narrow

    # 3. Wider subnet match (/16)
    best = table.lookup("10.0.2.1")
    assert best == r_wide

    # 4. Default route match (/0)
    best = table.lookup("8.8.8.8")
    assert best == r_default


def test_metric_tie_breaking():
    table = RoutingTable()

    # Two routes for same prefix but different metric
    r_costly = RouteEntry(destination_network="192.168.0.0/16", next_hop="1.1.1.1", metric=100)
    r_cheap = RouteEntry(destination_network="192.168.0.0/16", next_hop="2.2.2.2", metric=10)

    table.add_route(r_costly)
    table.add_route(r_cheap)

    best = table.lookup("192.168.5.5")
    assert best == r_cheap


def test_two_subnets_routed_through_virtual_router():
    """Sample Project 1: Two servers on different subnets connected via a virtual router."""
    net = VirtualNetwork()

    # Host A on subnet 10.0.1.0/24
    host_a = VirtualServer(name="HostA", ip_address="10.0.1.10", subnet_mask="255.255.255.0")
    iface_a = list(host_a.interfaces.values())[0]

    # Host B on subnet 10.0.2.0/24
    host_b = VirtualServer(name="HostB", ip_address="10.0.2.20", subnet_mask="255.255.255.0")
    iface_b = list(host_b.interfaces.values())[0]

    # Router R1 with two interfaces
    r1 = VirtualRouter(name="Router1")
    r1_iface1 = VirtualInterface(name="eth0", ip_address="10.0.1.1", subnet_mask="255.255.255.0")
    r1_iface2 = VirtualInterface(name="eth1", ip_address="10.0.2.1", subnet_mask="255.255.255.0")
    r1.add_interface(r1_iface1)
    r1.add_interface(r1_iface2)

    net.add_device(host_a)
    net.add_device(host_b)
    net.add_device(r1)

    # Connect HostA <-> Router eth0
    net.connect(host_a.device_id, iface_a.interface_id, r1.device_id, r1_iface1.interface_id, latency_ms=2.0)
    # Connect Router eth1 <-> HostB
    net.connect(r1.device_id, r1_iface2.interface_id, host_b.device_id, iface_b.interface_id, latency_ms=3.0)

    pkt = Packet(src_ip="10.0.1.10", dst_ip="10.0.2.20", protocol=Protocol.ICMP)
    delivered_pkt = net.transmit(pkt)

    assert delivered_pkt.state == PacketState.DELIVERED
    assert delivered_pkt.simulated_latency_ms == 5.0  # 2.0 + 3.0 ms
    # Verify hops recorded
    hop_devices = [h.device_id for h in delivered_pkt.route_history]
    assert host_a.device_id in hop_devices
    assert r1.device_id in hop_devices
    assert host_b.device_id in hop_devices


def test_routing_failure_when_no_route_exists():
    net = VirtualNetwork()
    host_a = VirtualServer(name="HostA", ip_address="10.0.1.10", subnet_mask="255.255.255.0")
    iface_a = list(host_a.interfaces.values())[0]

    r1 = VirtualRouter(name="Router1")
    r1_iface1 = VirtualInterface(name="eth0", ip_address="10.0.1.1", subnet_mask="255.255.255.0")
    r1.add_interface(r1_iface1)

    # Isolated Host C on another network
    host_c = VirtualServer(name="HostC", ip_address="172.16.5.5")

    net.add_device(host_a)
    net.add_device(r1)
    net.add_device(host_c)

    net.connect(host_a.device_id, iface_a.interface_id, r1.device_id, r1_iface1.interface_id)

    # Transmit to 172.16.5.5 for which Router1 has no route
    pkt = Packet(src_ip="10.0.1.10", dst_ip="172.16.5.5")
    result = net.transmit(pkt)

    assert result.state == PacketState.DROPPED
    assert "No route" in result.drop_or_delivery_reason
