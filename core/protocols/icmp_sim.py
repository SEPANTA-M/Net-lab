"""Simulated ICMP protocol behaviors (Echo Request, Echo Reply, TTL Expired, Unreachable)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.network import VirtualNetwork
from core.packet import Packet, PacketState, Protocol


class ICMPType(str, Enum):
    """Simulated ICMP message types."""

    ECHO_REQUEST = "ECHO_REQUEST"
    ECHO_REPLY = "ECHO_REPLY"
    DESTINATION_UNREACHABLE = "DESTINATION_UNREACHABLE"
    TIME_EXCEEDED = "TIME_EXCEEDED"


@dataclass
class ICMPPayload:
    """Safe simulation payload representing ICMP data."""

    icmp_type: ICMPType
    identifier: int = 1
    sequence_number: int = 1
    data: str = "SIMULATED_PING_DATA"


@dataclass
class PingResult:
    """Result of a virtual ping probe."""

    is_success: bool
    rtt_ms: float
    hops: int
    ttl: int
    error_message: Optional[str] = None


def send_virtual_ping(
    net: VirtualNetwork,
    src_ip: str,
    dst_ip: str,
    sequence: int = 1,
    ttl: int = 64,
) -> PingResult:
    """Execute a simulated ping request-reply cycle entirely in-memory."""
    # 1. Send Echo Request
    req = Packet(
        src_ip=src_ip,
        dst_ip=dst_ip,
        protocol=Protocol.ICMP,
        ttl=ttl,
        payload=ICMPPayload(icmp_type=ICMPType.ECHO_REQUEST, sequence_number=sequence),
    )
    res_req = net.transmit(req)
    if res_req.state != PacketState.DELIVERED:
        return PingResult(
            is_success=False,
            rtt_ms=res_req.simulated_latency_ms,
            hops=len(res_req.route_history),
            ttl=res_req.ttl,
            error_message=res_req.drop_or_delivery_reason or "Ping request dropped",
        )

    # 2. Destination sends Echo Reply back to source
    rep = Packet(
        src_ip=dst_ip,
        dst_ip=src_ip,
        protocol=Protocol.ICMP,
        ttl=64,
        payload=ICMPPayload(icmp_type=ICMPType.ECHO_REPLY, sequence_number=sequence),
    )
    res_rep = net.transmit(rep)
    if res_rep.state != PacketState.DELIVERED:
        return PingResult(
            is_success=False,
            rtt_ms=res_req.simulated_latency_ms + res_rep.simulated_latency_ms,
            hops=len(res_req.route_history) + len(res_rep.route_history),
            ttl=res_rep.ttl,
            error_message=res_rep.drop_or_delivery_reason or "Ping reply dropped",
        )

    total_rtt = res_req.simulated_latency_ms + res_rep.simulated_latency_ms
    return PingResult(
        is_success=True,
        rtt_ms=total_rtt,
        hops=len(res_req.route_history),
        ttl=res_req.ttl,
    )
