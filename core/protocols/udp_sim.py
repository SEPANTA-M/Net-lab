"""Simulated UDP datagram transmission and destination service check."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.network import VirtualNetwork
from core.packet import Packet, PacketState, Protocol
from core.server import VirtualServer


@dataclass
class UDPTransmissionResult:
    """Outcome of a simulated UDP datagram delivery."""

    is_delivered: bool
    is_port_open: bool
    latency_ms: float
    error_message: Optional[str] = None


def send_virtual_udp(
    net: VirtualNetwork,
    src_ip: str,
    dst_ip: str,
    dst_port: int,
    payload_data: str = "UDP_PAYLOAD",
    src_port: int = 54321,
) -> UDPTransmissionResult:
    """Simulate connectionless UDP transmission."""
    pkt = Packet(
        src_ip=src_ip,
        dst_ip=dst_ip,
        protocol=Protocol.UDP,
        src_port=src_port,
        dst_port=dst_port,
        payload=payload_data,
    )
    res = net.transmit(pkt)
    if res.state != PacketState.DELIVERED:
        return UDPTransmissionResult(
            is_delivered=False,
            is_port_open=False,
            latency_ms=res.simulated_latency_ms,
            error_message=res.drop_or_delivery_reason,
        )

    # Check if target port has an active UDP or DNS service
    dst_res = net.find_device_by_ip(dst_ip)
    is_open = False
    if dst_res:
        dst_dev, _ = dst_res
        if isinstance(dst_dev, VirtualServer):
            is_open = dst_dev.is_listening(Protocol.UDP, dst_port) or dst_dev.is_listening(Protocol.DNS, dst_port)

    return UDPTransmissionResult(
        is_delivered=True,
        is_port_open=is_open,
        latency_ms=res.simulated_latency_ms,
    )
