"""Simulated HTTP request and response models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

from core.network import VirtualNetwork
from core.packet import Packet, PacketState, Protocol
from core.server import VirtualServer


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


@dataclass
class HTTPRequestPayload:
    method: HTTPMethod = HTTPMethod.GET
    path: str = "/"
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""


@dataclass
class HTTPResponsePayload:
    status_code: int = 200
    status_text: str = "OK"
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = "Hello from Virtual HTTP Server"


@dataclass
class HTTPTransactionResult:
    is_success: bool
    status_code: Optional[int]
    response_body: Optional[str]
    rtt_ms: float
    error_message: Optional[str] = None


def send_virtual_http_get(
    net: VirtualNetwork,
    client_ip: str,
    server_ip: str,
    port: int = 80,
    path: str = "/",
) -> HTTPTransactionResult:
    """Execute a simulated HTTP GET transaction."""
    req_pkt = Packet(
        src_ip=client_ip,
        dst_ip=server_ip,
        protocol=Protocol.HTTP,
        src_port=52000,
        dst_port=port,
        payload=HTTPRequestPayload(method=HTTPMethod.GET, path=path),
    )
    res_req = net.transmit(req_pkt)
    if res_req.state != PacketState.DELIVERED:
        return HTTPTransactionResult(
            is_success=False,
            status_code=None,
            response_body=None,
            rtt_ms=res_req.simulated_latency_ms,
            error_message=f"HTTP request dropped: {res_req.drop_or_delivery_reason}",
        )

    # Server checks
    dst_res = net.find_device_by_ip(server_ip)
    if not dst_res:
        return HTTPTransactionResult(is_success=False, status_code=None, response_body=None, rtt_ms=0, error_message="Host unreachable")

    dst_dev, _ = dst_res
    if isinstance(dst_dev, VirtualServer):
        if not dst_dev.is_listening(Protocol.HTTP, port):
            return HTTPTransactionResult(
                is_success=False,
                status_code=None,
                response_body=None,
                rtt_ms=res_req.simulated_latency_ms * 2,
                error_message=f"HTTP service not running on port {port}",
            )

    # Server generates HTTP response
    resp_payload = HTTPResponsePayload(
        status_code=200,
        status_text="OK",
        headers={"Content-Type": "text/html", "Server": "Virtual-HTTPD/1.0"},
        body=f"<html><body><h1>Network Lab Simulation</h1><p>Served {path} safely.</p></body></html>",
    )

    resp_pkt = Packet(
        src_ip=server_ip,
        dst_ip=client_ip,
        protocol=Protocol.HTTP,
        src_port=port,
        dst_port=52000,
        payload=resp_payload,
    )
    res_resp = net.transmit(resp_pkt)
    if res_resp.state != PacketState.DELIVERED:
        return HTTPTransactionResult(
            is_success=False,
            status_code=None,
            response_body=None,
            rtt_ms=res_req.simulated_latency_ms + res_resp.simulated_latency_ms,
            error_message=f"HTTP response dropped: {res_resp.drop_or_delivery_reason}",
        )

    total_rtt = res_req.simulated_latency_ms + res_resp.simulated_latency_ms
    return HTTPTransactionResult(
        is_success=True,
        status_code=200,
        response_body=resp_payload.body,
        rtt_ms=total_rtt,
    )
