"""Protocol simulation module exports."""

from core.protocols.dns_sim import DNSRecord, DNSRecordType, DNSResponse, VirtualDNSServer, resolve_virtual_dns
from core.protocols.http_sim import (
    HTTPMethod,
    HTTPRequestPayload,
    HTTPResponsePayload,
    HTTPTransactionResult,
    send_virtual_http_get,
)
from core.protocols.icmp_sim import ICMPPayload, ICMPType, PingResult, send_virtual_ping
from core.protocols.tcp_sim import TCPConnectionResult, TCPFlag, TCPPacketPayload, TCPState, simulate_tcp_handshake
from core.protocols.udp_sim import UDPTransmissionResult, send_virtual_udp

__all__ = [
    "ICMPType",
    "ICMPPayload",
    "PingResult",
    "send_virtual_ping",
    "TCPState",
    "TCPFlag",
    "TCPPacketPayload",
    "TCPConnectionResult",
    "simulate_tcp_handshake",
    "UDPTransmissionResult",
    "send_virtual_udp",
    "DNSRecordType",
    "DNSRecord",
    "DNSResponse",
    "VirtualDNSServer",
    "resolve_virtual_dns",
    "HTTPMethod",
    "HTTPRequestPayload",
    "HTTPResponsePayload",
    "HTTPTransactionResult",
    "send_virtual_http_get",
]
