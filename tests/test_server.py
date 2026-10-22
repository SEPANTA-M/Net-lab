"""Tests for VirtualDevice and VirtualServer."""

import pytest
from core.device import DeviceState, DeviceType, VirtualDevice, VirtualInterface
from core.packet import Protocol
from core.server import VirtualServer, VirtualService


def test_virtual_interface_validation():
    iface = VirtualInterface(name="eth0", ip_address="192.168.1.1", subnet_mask="255.255.255.0")
    assert iface.contains_ip("192.168.1.50")
    assert not iface.contains_ip("10.0.0.1")

    with pytest.raises(ValueError, match="Invalid interface ip_address"):
        VirtualInterface(name="eth1", ip_address="invalid_ip")

    with pytest.raises(ValueError, match="Invalid subnet mask"):
        VirtualInterface(name="eth2", ip_address="192.168.1.1", subnet_mask="invalid_mask")


def test_virtual_device_interface_management():
    dev = VirtualDevice(name="Router-1", device_type=DeviceType.ROUTER)
    iface1 = VirtualInterface(name="eth0", ip_address="10.0.1.1")
    iface2 = VirtualInterface(name="eth1", ip_address="10.0.2.1")

    dev.add_interface(iface1)
    dev.add_interface(iface2)

    assert dev.get_interface(iface1.interface_id) == iface1
    assert dev.get_interface_by_name("eth1") == iface2
    assert dev.has_ip("10.0.1.1")
    assert not dev.has_ip("10.0.3.1")


def test_virtual_server_lifecycle_and_services():
    server = VirtualServer(name="Web-Server-1", ip_address="192.168.1.100")
    assert server.is_running()
    assert server.has_ip("192.168.1.100")

    http_svc = VirtualService(name="HTTP", protocol=Protocol.HTTP, port=80)
    server.add_service(http_svc)

    assert server.is_listening(Protocol.HTTP, 80)
    assert not server.is_listening(Protocol.TCP, 80)  # protocol mismatch
    assert not server.is_listening(Protocol.HTTP, 443)  # unconfigured port

    # Stopping server shuts down listening ports in simulator without affecting OS
    server.stop()
    assert not server.is_running()
    assert not server.is_listening(Protocol.HTTP, 80)

    server.start()
    assert server.is_running()
    assert server.is_listening(Protocol.HTTP, 80)


def test_virtual_service_port_validation():
    with pytest.raises(ValueError, match="Invalid service port"):
        VirtualService(name="BadPort", protocol=Protocol.TCP, port=70000)
