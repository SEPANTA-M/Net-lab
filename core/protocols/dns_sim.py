"""Simulated DNS resolution, cache behavior, and record mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from core.network import VirtualNetwork
from core.packet import Packet, PacketState, Protocol
from core.server import VirtualServer


class DNSRecordType(str, Enum):
    """Supported DNS record types."""

    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"


@dataclass
class DNSRecord:
    """A simulated DNS record entry."""

    name: str
    record_type: DNSRecordType
    value: str
    ttl: int = 300


@dataclass
class DNSResponse:
    """DNS lookup response result."""

    query_name: str
    is_success: bool
    resolved_ip: Optional[str] = None
    rtt_ms: float = 0.0
    from_cache: bool = False
    error: Optional[str] = None


class VirtualDNSServer(VirtualServer):
    """Virtual DNS server device providing internal name-to-IP resolution."""

    def __init__(self, name: str, ip_address: str, device_id: Optional[str] = None) -> None:
        super().__init__(name=name, ip_address=ip_address, device_id=device_id)
        self.records: Dict[str, DNSRecord] = {}
        self.cache: Dict[str, str] = {}

    def add_record(self, hostname: str, ip_val: str, record_type: DNSRecordType = DNSRecordType.A) -> None:
        """Add a hostname mapping."""
        self.records[hostname.lower()] = DNSRecord(name=hostname.lower(), record_type=record_type, value=ip_val)

    def query(self, hostname: str) -> Optional[str]:
        """Query record locally with cache check."""
        h = hostname.lower()
        if h in self.cache:
            return self.cache[h]
        if h in self.records:
            val = self.records[h].value
            self.cache[h] = val
            return val
        return None


def resolve_virtual_dns(
    net: VirtualNetwork,
    client_ip: str,
    dns_server_ip: str,
    hostname: str,
) -> DNSResponse:
    """Send a simulated DNS query packet to DNS server and return resolved IP."""
    query_pkt = Packet(
        src_ip=client_ip,
        dst_ip=dns_server_ip,
        protocol=Protocol.DNS,
        src_port=53535,
        dst_port=53,
        payload={"query": hostname},
    )
    res_query = net.transmit(query_pkt)
    if res_query.state != PacketState.DELIVERED:
        return DNSResponse(
            query_name=hostname,
            is_success=False,
            error=f"DNS query packet dropped: {res_query.drop_or_delivery_reason}",
            rtt_ms=res_query.simulated_latency_ms,
        )

    # DNS Server resolution
    dst_res = net.find_device_by_ip(dns_server_ip)
    if not dst_res:
        return DNSResponse(query_name=hostname, is_success=False, error="DNS server host unreachable")

    dns_dev, _ = dst_res
    if not isinstance(dns_dev, VirtualDNSServer):
        return DNSResponse(query_name=hostname, is_success=False, error=f"Target {dns_dev.name} is not a DNS server")

    resolved_ip = dns_dev.query(hostname)
    if not resolved_ip:
        return DNSResponse(
            query_name=hostname,
            is_success=False,
            error=f"NXDOMAIN: Name '{hostname}' not found",
            rtt_ms=res_query.simulated_latency_ms * 2,
        )

    # Return response packet
    resp_pkt = Packet(
        src_ip=dns_server_ip,
        dst_ip=client_ip,
        protocol=Protocol.DNS,
        src_port=53,
        dst_port=53535,
        payload={"resolved_ip": resolved_ip},
    )
    res_resp = net.transmit(resp_pkt)
    if res_resp.state != PacketState.DELIVERED:
        return DNSResponse(
            query_name=hostname,
            is_success=False,
            error=f"DNS response dropped: {res_resp.drop_or_delivery_reason}",
        )

    return DNSResponse(
        query_name=hostname,
        is_success=True,
        resolved_ip=resolved_ip,
        rtt_ms=res_query.simulated_latency_ms + res_resp.simulated_latency_ms,
    )
