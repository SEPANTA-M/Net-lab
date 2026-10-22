"""Safe, read-only collector for local machine network configuration."""

from __future__ import annotations

import logging
import os
import platform
import socket
import subprocess
from typing import List, Optional

from discovery.models import (
    ConfidenceLevel,
    NetworkSnapshot,
    ObservedInterface,
    ObservedRoute,
    ProvenanceSource,
)

logger = logging.getLogger("network_lab.discovery")


class LocalSystemCollector:
    """Collects host network configuration via safe, read-only system interfaces.

    Security & Privacy:
    - Never collects passwords, credentials, or private files.
    - Never modifies host interfaces, routing tables, or firewall.
    - Commands are invoked with explicit argument lists (no shell=True).
    - Gracefully falls back when commands fail or permissions are restricted.
    """

    def __init__(self) -> None:
        self.os_type = platform.system()

    def collect_snapshot(self) -> NetworkSnapshot:
        """Collect and return a point-in-time network snapshot."""
        hostname = socket.gethostname()
        interfaces = self._collect_interfaces()
        routes, default_gw = self._collect_routes()
        dns_servers = self._collect_dns_servers()

        return NetworkSnapshot(
            hostname=hostname,
            default_gateway=default_gw,
            dns_servers=dns_servers,
            interfaces=interfaces,
            routes=routes,
            notes=f"Collected on {self.os_type} {platform.release()}",
        )

    def _collect_interfaces(self) -> List[ObservedInterface]:
        """Collect available network interfaces safely."""
        interfaces: List[ObservedInterface] = []

        if self.os_type == "Linux":
            # Read-only inspection of /sys/class/net
            net_path = "/sys/class/net"
            if os.path.isdir(net_path):
                try:
                    for iface_name in os.listdir(net_path):
                        iface = ObservedInterface(
                            name=iface_name,
                            source=ProvenanceSource.SYSFS_LINUX,
                            confidence=ConfidenceLevel.OBSERVED,
                        )
                        operstate_path = os.path.join(net_path, iface_name, "operstate")
                        if os.path.isfile(operstate_path):
                            try:
                                with open(operstate_path, "r", encoding="utf-8") as f:
                                    status = f.read().strip()
                                    iface.is_up = status != "down"
                            except Exception:
                                pass

                        address_path = os.path.join(net_path, iface_name, "address")
                        if os.path.isfile(address_path):
                            try:
                                with open(address_path, "r", encoding="utf-8") as f:
                                    iface.mac_address = f.read().strip()
                            except Exception:
                                pass

                        interfaces.append(iface)
                except Exception as e:
                    logger.warning(f"Could not inspect {net_path}: {e}")

        # Fallback or supplementary inspection via getaddrinfo for loopback/primary hostname
        if not interfaces:
            try:
                primary_ip = socket.gethostbyname(socket.gethostname())
                interfaces.append(
                    ObservedInterface(
                        name="primary",
                        ip_addresses=[primary_ip],
                        netmasks=["255.255.255.0"],
                        is_up=True,
                        source=ProvenanceSource.OS_SOCKET_API,
                    )
                )
            except Exception:
                interfaces.append(
                    ObservedInterface(
                        name="lo",
                        ip_addresses=["127.0.0.1"],
                        netmasks=["255.0.0.0"],
                        is_up=True,
                        source=ProvenanceSource.OS_SOCKET_API,
                    )
                )

        return interfaces

    def _collect_routes(self) -> tuple[List[ObservedRoute], Optional[str]]:
        """Collect routes and identify default gateway."""
        routes: List[ObservedRoute] = []
        default_gw: Optional[str] = None

        if self.os_type == "Linux":
            # Read-only parse of /proc/net/route if readable
            proc_route = "/proc/net/route"
            if os.path.isfile(proc_route):
                try:
                    with open(proc_route, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    for line in lines[1:]:  # Skip header
                        parts = line.strip().split()
                        if len(parts) >= 8:
                            iface_name = parts[0]
                            dest_hex = parts[1]
                            gw_hex = parts[2]
                            metric = int(parts[6])

                            # Convert 8-char hex (little endian) to IP
                            gw_ip = self._hex_to_ip(gw_hex)
                            dest_ip = self._hex_to_ip(dest_hex)

                            if dest_hex == "00000000":
                                default_gw = gw_ip
                                routes.append(
                                    ObservedRoute(
                                        destination="0.0.0.0/0",
                                        gateway=gw_ip,
                                        interface_name=iface_name,
                                        metric=metric,
                                        confidence=ConfidenceLevel.OBSERVED,
                                    )
                                )
                            else:
                                routes.append(
                                    ObservedRoute(
                                        destination=dest_ip,
                                        gateway=gw_ip if gw_ip != "0.0.0.0" else None,
                                        interface_name=iface_name,
                                        metric=metric,
                                        confidence=ConfidenceLevel.OBSERVED,
                                    )
                                )
                except Exception as e:
                    logger.warning(f"Could not read {proc_route}: {e}")

        return routes, default_gw

    def _collect_dns_servers(self) -> List[str]:
        """Collect configured DNS resolvers safely."""
        resolvers: List[str] = []
        resolv_path = "/etc/resolv.conf"
        if os.path.isfile(resolv_path):
            try:
                with open(resolv_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("nameserver"):
                            parts = line.split()
                            if len(parts) >= 2:
                                resolvers.append(parts[1])
            except Exception as e:
                logger.warning(f"Could not read {resolv_path}: {e}")
        return resolvers

    @staticmethod
    def _hex_to_ip(hex_str: str) -> str:
        """Convert Linux kernel little-endian hex route IP to dotted decimal."""
        try:
            val = int(hex_str, 16)
            b0 = val & 0xFF
            b1 = (val >> 8) & 0xFF
            b2 = (val >> 16) & 0xFF
            b3 = (val >> 24) & 0xFF
            return f"{b0}.{b1}.{b2}.{b3}"
        except Exception:
            return "0.0.0.0"
