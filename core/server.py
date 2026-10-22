"""Virtual server node with virtual services and port listener metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from core.device import DeviceState, DeviceType, VirtualDevice, VirtualInterface
from core.packet import Protocol


@dataclass
class VirtualService:
    """Represents a virtual software service running on a virtual server.

    Does not bind to host OS sockets or listen to physical network ports.
    """

    name: str
    protocol: Protocol
    port: int
    is_active: bool = True
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.port < 0 or self.port > 65535:
            raise ValueError(f"Invalid service port '{self.port}': must be 0-65535")


class VirtualServer(VirtualDevice):
    """Virtual server device capable of hosting virtual services.

    Lifecycle methods (start/stop) modify only simulated state.
    """

    def __init__(
        self,
        name: str,
        ip_address: Optional[str] = None,
        subnet_mask: Optional[str] = "255.255.255.0",
        os_label: str = "Virtual Linux 6.x",
        device_id: Optional[str] = None,
    ) -> None:
        if device_id:
            super().__init__(name=name, device_type=DeviceType.SERVER, device_id=device_id)
        else:
            super().__init__(name=name, device_type=DeviceType.SERVER)
        self.os_label = os_label
        self.services: Dict[int, VirtualService] = {}

        # Default virtual interface eth0
        if ip_address:
            default_iface = VirtualInterface(
                name="eth0",
                ip_address=ip_address,
                subnet_mask=subnet_mask,
            )
            self.add_interface(default_iface)

    def add_service(self, service: VirtualService) -> None:
        """Register a simulated service on this virtual server."""
        self.services[service.port] = service

    def remove_service(self, port: int) -> Optional[VirtualService]:
        """Unregister a simulated service."""
        return self.services.pop(port, None)

    def get_service(self, port: int) -> Optional[VirtualService]:
        """Look up a simulated service by port."""
        return self.services.get(port)

    def is_listening(self, protocol: Protocol, port: int) -> bool:
        """Check if server is running and a service is actively listening on port."""
        if not self.is_running():
            return False
        svc = self.services.get(port)
        if svc and svc.is_active and svc.protocol == protocol:
            return True
        return False
