"""Security Boundary Tests: Verify simulation never transmits real network packets."""

import socket
from unittest.mock import patch
import pytest

from core.network import VirtualNetwork
from core.packet import Packet, Protocol
from core.server import VirtualServer


def test_simulation_does_not_open_real_sockets():
    """Verify that transmitting virtual packets does not invoke socket.socket or real network calls."""
    with patch("socket.socket") as mock_socket:
        net = VirtualNetwork()
        srv1 = VirtualServer(name="HostA", ip_address="10.0.0.1")
        srv2 = VirtualServer(name="HostB", ip_address="10.0.0.2")
        net.add_device(srv1)
        net.add_device(srv2)

        iface1 = list(srv1.interfaces.values())[0]
        iface2 = list(srv2.interfaces.values())[0]
        net.connect(srv1.device_id, iface1.interface_id, srv2.device_id, iface2.interface_id)

        pkt = Packet(src_ip="10.0.0.1", dst_ip="10.0.0.2", protocol=Protocol.ICMP)
        result = net.transmit(pkt)

        # Transmit must complete in-memory
        assert result.state.value == "DELIVERED"
        # Real socket constructor must never have been called
        mock_socket.assert_not_called()


def test_virtual_server_start_stop_does_not_bind_real_ports():
    """Verify VirtualServer does not bind real OS sockets on start or add_service."""
    with patch("socket.socket") as mock_socket:
        srv = VirtualServer(name="WebSrv", ip_address="192.168.1.50")
        srv.start()
        srv.stop()
        mock_socket.assert_not_called()
