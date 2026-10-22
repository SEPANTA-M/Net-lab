"""Tests for Virtual Packet model and validation."""

import pytest
from core.packet import Packet, PacketState, Protocol


def test_packet_creation_and_defaults():
    pkt = Packet(src_ip="192.168.1.10", dst_ip="192.168.1.20")
    assert pkt.packet_id is not None
    assert pkt.protocol == Protocol.ICMP
    assert pkt.ttl == 64
    assert pkt.state == PacketState.CREATED
    assert pkt.route_history == []
    assert pkt.drop_or_delivery_reason is None


def test_packet_custom_fields():
    pkt = Packet(
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        protocol=Protocol.TCP,
        src_port=12345,
        dst_port=80,
        payload="GET / HTTP/1.1",
        ttl=128,
        size_bytes=100,
    )
    assert pkt.src_port == 12345
    assert pkt.dst_port == 80
    assert pkt.payload == "GET / HTTP/1.1"
    assert pkt.ttl == 128
    assert pkt.size_bytes == 100


def test_packet_ip_validation():
    with pytest.raises(ValueError, match="Invalid src_ip"):
        Packet(src_ip="not_an_ip", dst_ip="192.168.1.1")

    with pytest.raises(ValueError, match="Invalid dst_ip"):
        Packet(src_ip="192.168.1.1", dst_ip="999.999.999.999")


def test_packet_port_validation():
    with pytest.raises(ValueError, match="Invalid src_port"):
        Packet(src_ip="10.0.0.1", dst_ip="10.0.0.2", src_port=70000)

    with pytest.raises(ValueError, match="Invalid dst_port"):
        Packet(src_ip="10.0.0.1", dst_ip="10.0.0.2", dst_port=-1)


def test_packet_ttl_validation_and_decrement():
    with pytest.raises(ValueError, match="Invalid TTL"):
        Packet(src_ip="10.0.0.1", dst_ip="10.0.0.2", ttl=300)

    pkt = Packet(src_ip="10.0.0.1", dst_ip="10.0.0.2", ttl=2)
    assert pkt.decrement_ttl() == 1
    assert pkt.state == PacketState.CREATED
    assert pkt.decrement_ttl() == 0
    assert pkt.state == PacketState.TIMED_OUT
    assert "TTL expired" in pkt.drop_or_delivery_reason


def test_packet_unique_ids():
    p1 = Packet(src_ip="10.0.0.1", dst_ip="10.0.0.2")
    p2 = Packet(src_ip="10.0.0.1", dst_ip="10.0.0.2")
    assert p1.packet_id != p2.packet_id
