"""Data models for real-world network observation and snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ConfidenceLevel(str, Enum):
    """Confidence level of an observation."""

    OBSERVED = "OBSERVED"  # Directly verified from OS API/system state
    INFERRED = "INFERRED"  # Derived logically (e.g. gateway from routing table)
    UNCONFIRMED = "UNCONFIRMED"  # Incomplete response or heuristic


class ProvenanceSource(str, Enum):
    """Source of network data."""

    OS_SOCKET_API = "OS_SOCKET_API"
    SYSFS_LINUX = "SYSFS_LINUX"
    IP_ROUTE_LINUX = "IP_ROUTE_LINUX"
    RESOLV_CONF = "RESOLV_CONF"
    WINDOWS_IPCONFIG = "WINDOWS_IPCONFIG"
    MOCK_FIXTURE = "MOCK_FIXTURE"


@dataclass
class ObservedInterface:
    """Read-only local network interface observation."""

    name: str
    ip_addresses: List[str] = field(default_factory=list)
    netmasks: List[str] = field(default_factory=list)
    is_up: bool = True
    mac_address: Optional[str] = None
    interface_type: str = "ETHERNET"
    source: ProvenanceSource = ProvenanceSource.OS_SOCKET_API
    confidence: ConfidenceLevel = ConfidenceLevel.OBSERVED
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ObservedRoute:
    """Read-only route observation."""

    destination: str
    gateway: Optional[str] = None
    interface_name: Optional[str] = None
    metric: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.OBSERVED
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class NetworkSnapshot:
    """Stores a consistent, point-in-time snapshot of discovered host network configuration.

    This snapshot does NOT transmit packets and does NOT change system configuration.
    """

    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hostname: str = "localhost"
    default_gateway: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)
    interfaces: List[ObservedInterface] = field(default_factory=list)
    routes: List[ObservedRoute] = field(default_factory=list)
    notes: str = "Passive local configuration observation"

    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to JSON-safe dictionary."""
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "hostname": self.hostname,
            "default_gateway": self.default_gateway,
            "dns_servers": self.dns_servers,
            "interfaces": [
                {
                    "name": i.name,
                    "ip_addresses": i.ip_addresses,
                    "netmasks": i.netmasks,
                    "is_up": i.is_up,
                    "mac_address": i.mac_address,
                    "interface_type": i.interface_type,
                    "confidence": i.confidence.value,
                }
                for i in self.interfaces
            ],
            "routes": [
                {
                    "destination": r.destination,
                    "gateway": r.gateway,
                    "interface_name": r.interface_name,
                    "metric": r.metric,
                    "confidence": r.confidence.value,
                }
                for r in self.routes
            ],
            "notes": self.notes,
        }
