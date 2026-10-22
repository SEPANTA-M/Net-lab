"""Core packet model and packet lifecycle states for Network Lab simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import ipaddress
from typing import Any, List, Optional
import uuid


class Protocol(str, Enum):
    """Supported virtual simulation protocols."""

    ICMP = "ICMP"
    TCP = "TCP"
    UDP = "UDP"
    DNS = "DNS"
    HTTP = "HTTP"
    CUSTOM = "CUSTOM"


class PacketState(str, Enum):
    """Lifecycle states of a simulated packet."""

    CREATED = "CREATED"
    QUEUED = "QUEUED"
    ROUTING = "ROUTING"
    DELIVERED = "DELIVERED"
    DROPPED = "DROPPED"
    TIMED_OUT = "TIMED_OUT"


@dataclass
class RouteHop:
    """Represents a recorded hop along a packet's simulated traversal."""

    device_id: str
    interface_id: Optional[str]
    timestamp: datetime
    action: str = "FORWARD"
    detail: str = ""


@dataclass
class Packet:
    """In-memory virtual packet model.

    This is an isolated simulation data structure. It is never transmitted
    over real sockets or host operating-system interfaces.
    """

    src_ip: str
    dst_ip: str
    protocol: Protocol = Protocol.ICMP
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    payload: Any = None
    ttl: int = 64
    size_bytes: int = 64
    packet_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    state: PacketState = PacketState.CREATED
    route_history: List[RouteHop] = field(default_factory=list)
    drop_or_delivery_reason: Optional[str] = None
    simulated_latency_ms: float = 0.0

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate IP addresses, ports, protocol, and TTL limits."""
        # Validate source and destination IP addresses
        try:
            ipaddress.ip_address(self.src_ip)
        except ValueError as err:
            raise ValueError(f"Invalid src_ip '{self.src_ip}': {err}") from err

        try:
            ipaddress.ip_address(self.dst_ip)
        except ValueError as err:
            raise ValueError(f"Invalid dst_ip '{self.dst_ip}': {err}") from err

        # Validate ports when provided
        for port_name, port_val in (("src_port", self.src_port), ("dst_port", self.dst_port)):
            if port_val is not None:
                if not isinstance(port_val, int) or port_val < 0 or port_val > 65535:
                    raise ValueError(f"Invalid {port_name} '{port_val}': must be integer between 0 and 65535")

        # Validate TTL
        if not isinstance(self.ttl, int) or self.ttl < 0 or self.ttl > 255:
            raise ValueError(f"Invalid TTL '{self.ttl}': must be integer between 0 and 255")

        # Validate size
        if not isinstance(self.size_bytes, int) or self.size_bytes < 0:
            raise ValueError(f"Invalid size_bytes '{self.size_bytes}': must be non-negative integer")

        # Normalize Protocol enum
        if isinstance(self.protocol, str) and not isinstance(self.protocol, Protocol):
            try:
                self.protocol = Protocol(self.protocol.upper())
            except ValueError:
                raise ValueError(f"Unsupported protocol '{self.protocol}'")

    def record_hop(self, device_id: str, interface_id: Optional[str] = None, action: str = "FORWARD", detail: str = "") -> None:
        """Record a hop into the packet's traversal history."""
        self.route_history.append(
            RouteHop(
                device_id=device_id,
                interface_id=interface_id,
                timestamp=datetime.now(timezone.utc),
                action=action,
                detail=detail,
            )
        )

    def mark_delivered(self, reason: str = "Delivered to destination") -> None:
        """Transition packet to DELIVERED state."""
        self.state = PacketState.DELIVERED
        self.drop_or_delivery_reason = reason

    def mark_dropped(self, reason: str) -> None:
        """Transition packet to DROPPED state."""
        self.state = PacketState.DROPPED
        self.drop_or_delivery_reason = reason

    def mark_timed_out(self, reason: str = "TTL expired or request timed out") -> None:
        """Transition packet to TIMED_OUT state."""
        self.state = PacketState.TIMED_OUT
        self.drop_or_delivery_reason = reason

    def decrement_ttl(self) -> int:
        """Decrement TTL by 1. If 0, packet expires."""
        self.ttl -= 1
        if self.ttl <= 0:
            self.mark_timed_out("TTL expired in transit")
        return self.ttl
