"""Tests for VirtualNetwork engine and packet delivery."""

import pytest
from core.device import DeviceType, VirtualDevice, VirtualInterface
from core.network import VirtualNetwork
from core.packet import Packet, PacketState, Protocol
from core.server import VirtualServer


def test_network_add_remove_devices():
    net = VirtualNetwork()
    srv1 = VirtualServer(name="Srv1", ip_address="192.168.1.10")
    srv2 = VirtualServer(name="Srv2", ip_address="192.168.1.20")

    net.add_device(srv1)
    net.add_device(srv2)

    assert net.get_device(srv1.device_id) == srv1
    assert net.find_device_by_ip("192.168.1.10")[0] == srv1

    net.remove_device(srv1.device_id)
    assert net.get_device(srv1.device_id) is None
    assert net.find_device_by_ip("192.168.1.10") is None


def test_network_link_creation():
    net = VirtualNetwork()
    srv1 = VirtualServer(name="Srv1", ip_address="192.168.1.10")
    srv2 = VirtualServer(name="Srv2", ip_address="192.168.1.20")

    net.add_device(srv1)
    net.add_device(srv2)

    iface1 = list(srv1.interfaces.values())[0]
    iface2 = list(srv2.interfaces.values())[0]

    link = net.connect(srv1.device_id, iface1.interface_id, srv2.device_id, iface2.interface_id, latency_ms=5.0)

    assert link.is_up
    assert link.latency_ms == 5.0
    assert iface1.connected_link_id == link.link_id
    assert iface2.connected_link_id == link.link_id


def test_successful_direct_packet_delivery():
    net = VirtualNetwork()
    srv1 = VirtualServer(name="HostA", ip_address="192.168.1.10")
    srv2 = VirtualServer(name="HostB", ip_address="192.168.1.20")

    net.add_device(srv1)
    net.add_device(srv2)

    iface1 = list(srv1.interfaces.values())[0]
    iface2 = list(srv2.interfaces.values())[0]

    net.connect(srv1.device_id, iface1.interface_id, srv2.device_id, iface2.interface_id, latency_ms=3.5)

    pkt = Packet(src_ip="192.168.1.10", dst_ip="192.168.1.20", protocol=Protocol.ICMP)
    delivered_pkt = net.transmit(pkt)

    assert delivered_pkt.state == PacketState.DELIVERED
    assert delivered_pkt.simulated_latency_ms == 3.5
    assert len(delivered_pkt.route_history) == 2
    assert delivered_pkt.route_history[0].device_id == srv1.device_id
    assert delivered_pkt.route_history[1].device_id == srv2.device_id
    assert delivered_pkt.route_history[1].action == "DELIVER"


def test_packet_drop_on_missing_destination():
    net = VirtualNetwork()
    srv1 = VirtualServer(name="HostA", ip_address="192.168.1.10")
    net.add_device(srv1)

    pkt = Packet(src_ip="192.168.1.10", dst_ip="192.168.1.99")
    res = net.transmit(pkt)

    assert res.state == PacketState.DROPPED
    assert "no virtual host matches" in res.drop_or_delivery_reason


def test_packet_drop_on_missing_link():
    net = VirtualNetwork()
    srv1 = VirtualServer(name="HostA", ip_address="192.168.1.10")
    srv2 = VirtualServer(name="HostB", ip_address="192.168.1.20")
    net.add_device(srv1)
    net.add_device(srv2)

    # Devices exist but no link is connected between them
    pkt = Packet(src_ip="192.168.1.10", dst_ip="192.168.1.20")
    res = net.transmit(pkt)

    assert res.state == PacketState.DROPPED
    assert "No direct link" in res.drop_or_delivery_reason


def test_packet_drop_when_link_is_down():
    net = VirtualNetwork()
    srv1 = VirtualServer(name="HostA", ip_address="192.168.1.10")
    srv2 = VirtualServer(name="HostB", ip_address="192.168.1.20")
    net.add_device(srv1)
    net.add_device(srv2)

    iface1 = list(srv1.interfaces.values())[0]
    iface2 = list(srv2.interfaces.values())[0]
    link = net.connect(srv1.device_id, iface1.interface_id, srv2.device_id, iface2.interface_id)
    link.is_up = False

    pkt = Packet(src_ip="192.168.1.10", dst_ip="192.168.1.20")
    res = net.transmit(pkt)

    assert res.state == PacketState.DROPPED
    assert "is DOWN" in res.drop_or_delivery_reason


def test_simulated_packet_loss_reproducibility():
    # Test deterministic packet loss with fixed random seed
    net1 = VirtualNetwork(random_seed=42)
    srv1 = VirtualServer(name="HostA", ip_address="192.168.1.10")
    srv2 = VirtualServer(name="HostB", ip_address="192.168.1.20")
    net1.add_device(srv1)
    net1.add_device(srv2)

    iface1 = list(srv1.interfaces.values())[0]
    iface2 = list(srv2.interfaces.values())[0]
    # 50% loss
    net1.connect(srv1.device_id, iface1.interface_id, srv2.device_id, iface2.interface_id, loss_rate=0.5)

    drops1 = []
    for _ in range(10):
        pkt = Packet(src_ip="192.168.1.10", dst_ip="192.168.1.20")
        net1.transmit(pkt)
        drops1.append(pkt.state == PacketState.DROPPED)

    # Identical seed should produce identical pattern
    net2 = VirtualNetwork(random_seed=42)
    s1 = VirtualServer(name="HostA", ip_address="192.168.1.10")
    s2 = VirtualServer(name="HostB", ip_address="192.168.1.20")
    net2.add_device(s1)
    net2.add_device(s2)
    i1 = list(s1.interfaces.values())[0]
    i2 = list(s2.interfaces.values())[0]
    net2.connect(s1.device_id, i1.interface_id, s2.device_id, i2.interface_id, loss_rate=0.5)

    drops2 = []
    for _ in range(10):
        pkt = Packet(src_ip="192.168.1.10", dst_ip="192.168.1.20")
        net2.transmit(pkt)
        drops2.append(pkt.state == PacketState.DROPPED)

    assert drops1 == drops2
    assert any(drops1)  # At least some were dropped
    assert not all(drops1)  # At least some succeeded
