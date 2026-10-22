"""Virtual device and interface abstractions for Network Lab."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import ipaddress
from typing import Any, Dict, List, Optional
import uuid


class DeviceType(str, Enum):
    """Categorization of virtual nodes."""

    HOST = "HOST"
    SERVER = "SERVER"
    ROUTER = "ROUTER"
    SWITCH = "SWITCH"
    FIREWALL = "FIREWALL"
    DNS_SERVER = "DNS_SERVER"
    GATEWAY = "GATEWAY"
    UNKNOWN = "UNKNOWN"


class DeviceState(str, Enum):
    """Operational states of a virtual device."""

    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass
class VirtualInterface:
    """A virtual network interface attached to a virtual device."""

    name: str
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = "255.255.255.0"
    mac_address: Optional[str] = None
    interface_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_up: bool = True
    connected_link_id: Optional[str] = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate interface IP and subnet mask if configured."""
        if self.ip_address:
            try:
                ipaddress.ip_address(self.ip_address)
            except ValueError as err:
                raise ValueError(f"Invalid interface ip_address '{self.ip_address}': {err}") from err

        if self.subnet_mask and self.ip_address:
            try:
                # Validates CIDR or dotted decimal mask when paired with IP
                ipaddress.ip_network(f"{self.ip_address}/{self.subnet_mask}", strict=False)
            except ValueError as err:
                raise ValueError(f"Invalid subnet mask '{self.subnet_mask}': {err}") from err

    @property
    def network(self) -> Optional[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """Return the ipaddress network object if IP is configured."""
        if not self.ip_address:
            return None
        mask = self.subnet_mask or "255.255.255.255"
        return ipaddress.ip_network(f"{self.ip_address}/{mask}", strict=False)

    def contains_ip(self, ip_str: str) -> bool:
        """Check if an IP string falls inside this interface's local subnet."""
        net = self.network
        if not net:
            return False
        try:
            return ipaddress.ip_address(ip_str) in net
        except ValueError:
            return False


@dataclass
class VirtualDevice:
    """Base class for all virtual nodes in the Network Lab simulation engine.

    All devices exist purely in-memory. They do not bind to host sockets
    or interact with physical hardware.
    """

    name: str
    device_type: DeviceType = DeviceType.HOST
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: DeviceState = DeviceState.RUNNING
    interfaces: Dict[str, VirtualInterface] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_interface(self, interface: VirtualInterface) -> VirtualInterface:
        """Add a virtual interface to the device."""
        self.interfaces[interface.interface_id] = interface
        return interface

    def get_interface(self, interface_id: str) -> Optional[VirtualInterface]:
        """Retrieve an interface by ID."""
        return self.interfaces.get(interface_id)

    def get_interface_by_name(self, name: str) -> Optional[VirtualInterface]:
        """Retrieve an interface by human-readable name."""
        for iface in self.interfaces.values():
            if iface.name == name:
                return iface
        return None

    def get_all_ips(self) -> List[str]:
        """Return a list of non-empty IP addresses configured on this device."""
        return [iface.ip_address for iface in self.interfaces.values() if iface.ip_address]

    def has_ip(self, ip_str: str) -> bool:
        """Check if any interface on this device possesses the specified IP."""
        return ip_str in self.get_all_ips()

    def start(self) -> None:
        """Start the virtual device in the simulation."""
        self.state = DeviceState.RUNNING

    def stop(self) -> None:
        """Stop the virtual device in the simulation."""
        self.state = DeviceState.STOPPED

    def is_running(self) -> bool:
        """Check if device is running."""
        return self.state == DeviceState.RUNNING
