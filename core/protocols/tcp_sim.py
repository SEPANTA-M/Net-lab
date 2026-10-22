"""Simulated TCP connection state machine and virtual handshake."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.network import VirtualNetwork
from core.packet import Packet, PacketState, Protocol
from core.server import VirtualServer


class TCPState(str, Enum):
    """Simplified TCP connection states."""

    CLOSED = "CLOSED"
    SYN_SENT = "SYN_SENT"
    SYN_RECEIVED = "SYN_RECEIVED"
    ESTABLISHED = "ESTABLISHED"
    FIN_WAIT = "FIN_WAIT"
    CLOSED_WAIT = "CLOSED_WAIT"


class TCPFlag(str, Enum):
    """TCP simulation flags."""

    SYN = "SYN"
    SYN_ACK = "SYN_ACK"
    ACK = "ACK"
    FIN = "FIN"
    RST = "RST"


@dataclass
class TCPPacketPayload:
    """Safe simulation payload for TCP segments."""

    flags: TCPFlag
    seq_num: int = 0
    ack_num: int = 0
    data: str = ""


@dataclass
class TCPConnectionResult:
    """Outcome of a simulated TCP connection attempt."""

    is_connected: bool
    state: TCPState
    rtt_ms: float
    error_message: Optional[str] = None


def simulate_tcp_handshake(
    net: VirtualNetwork,
    src_ip: str,
    dst_ip: str,
    dst_port: int,
    src_port: int = 49152,
) -> TCPConnectionResult:
    """Execute a simulated 3-way handshake (SYN, SYN-ACK, ACK) inside the virtual network."""
    # Step 1: Send SYN
    syn_pkt = Packet(
        src_ip=src_ip,
        dst_ip=dst_ip,
        protocol=Protocol.TCP,
        src_port=src_port,
        dst_port=dst_port,
        payload=TCPPacketPayload(flags=TCPFlag.SYN, seq_num=100),
    )
    res_syn = net.transmit(syn_pkt)
    if res_syn.state != PacketState.DELIVERED:
        return TCPConnectionResult(
            is_connected=False,
            state=TCPState.CLOSED,
            rtt_ms=res_syn.simulated_latency_ms,
            error_message=f"SYN dropped: {res_syn.drop_or_delivery_reason}",
        )

    # Check if target host is listening on port
    dst_res = net.find_device_by_ip(dst_ip)
    if not dst_res:
        return TCPConnectionResult(
            is_connected=False,
            state=TCPState.CLOSED,
            rtt_ms=res_syn.simulated_latency_ms,
            error_message="Host unreachable",
        )
    dst_dev, _ = dst_res
    if isinstance(dst_dev, VirtualServer):
        if not dst_dev.is_listening(Protocol.TCP, dst_port) and not dst_dev.is_listening(Protocol.HTTP, dst_port):
            # Target sends RST
            return TCPConnectionResult(
                is_connected=False,
                state=TCPState.CLOSED,
                rtt_ms=res_syn.simulated_latency_ms * 2,
                error_message=f"Connection refused by {dst_dev.name}: port {dst_port} closed (RST)",
            )

    # Step 2: Target returns SYN-ACK
    syn_ack_pkt = Packet(
        src_ip=dst_ip,
        dst_ip=src_ip,
        protocol=Protocol.TCP,
        src_port=dst_port,
        dst_port=src_port,
        payload=TCPPacketPayload(flags=TCPFlag.SYN_ACK, seq_num=500, ack_num=101),
    )
    res_syn_ack = net.transmit(syn_ack_pkt)
    if res_syn_ack.state != PacketState.DELIVERED:
        return TCPConnectionResult(
            is_connected=False,
            state=TCPState.SYN_SENT,
            rtt_ms=res_syn.simulated_latency_ms + res_syn_ack.simulated_latency_ms,
            error_message=f"SYN-ACK dropped: {res_syn_ack.drop_or_delivery_reason}",
        )

    # Step 3: Source sends ACK
    ack_pkt = Packet(
        src_ip=src_ip,
        dst_ip=dst_ip,
        protocol=Protocol.TCP,
        src_port=src_port,
        dst_port=dst_port,
        payload=TCPPacketPayload(flags=TCPFlag.ACK, seq_num=101, ack_num=501),
    )
    res_ack = net.transmit(ack_pkt)
    if res_ack.state != PacketState.DELIVERED:
        return TCPConnectionResult(
            is_connected=False,
            state=TCPState.SYN_RECEIVED,
            rtt_ms=res_syn.simulated_latency_ms + res_syn_ack.simulated_latency_ms,
            error_message=f"Final ACK dropped: {res_ack.drop_or_delivery_reason}",
        )

    total_rtt = res_syn.simulated_latency_ms + res_syn_ack.simulated_latency_ms
    return TCPConnectionResult(
        is_connected=True,
        state=TCPState.ESTABLISHED,
        rtt_ms=total_rtt,
    )
