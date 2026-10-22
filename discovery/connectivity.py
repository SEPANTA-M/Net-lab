"""Opt-in, transparent real network connectivity diagnostic checks."""

from __future__ import annotations

from dataclasses import dataclass
import socket
import time
from typing import Optional


@dataclass
class DiagnosticCheckResult:
    """Outcome of an opt-in connectivity check.

    Transparently discloses whether real network traffic was sent.
    """

    check_name: str
    target: str
    is_successful: bool
    latency_ms: Optional[float]
    details: str
    sent_real_traffic: bool = True


class RealNetworkDiagnostics:
    """Transparent connectivity diagnostics with strict user-opt-in transparency."""

    @staticmethod
    def check_dns_resolution(hostname: str = "github.com", timeout_sec: float = 2.0) -> DiagnosticCheckResult:
        """Check if DNS resolution succeeds for a user-approved hostname."""
        start = time.perf_counter()
        try:
            socket.setdefaulttimeout(timeout_sec)
            ip = socket.gethostbyname(hostname)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return DiagnosticCheckResult(
                check_name="DNS Resolution",
                target=hostname,
                is_successful=True,
                latency_ms=round(elapsed_ms, 2),
                details=f"Resolved to {ip}",
                sent_real_traffic=True,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return DiagnosticCheckResult(
                check_name="DNS Resolution",
                target=hostname,
                is_successful=False,
                latency_ms=round(elapsed_ms, 2),
                details=f"Resolution failed: {e}",
                sent_real_traffic=True,
            )

    @staticmethod
    def check_tcp_port(host: str, port: int, timeout_sec: float = 2.0) -> DiagnosticCheckResult:
        """Check TCP port connectivity for an explicitly authorized target."""
        start = time.perf_counter()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout_sec)
        try:
            s.connect((host, port))
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            s.close()
            return DiagnosticCheckResult(
                check_name="TCP Connect",
                target=f"{host}:{port}",
                is_successful=True,
                latency_ms=round(elapsed_ms, 2),
                details="TCP handshake completed",
                sent_real_traffic=True,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            s.close()
            return DiagnosticCheckResult(
                check_name="TCP Connect",
                target=f"{host}:{port}",
                is_successful=False,
                latency_ms=round(elapsed_ms, 2),
                details=f"Connection failed or refused: {e}",
                sent_real_traffic=True,
            )
