"""Tests for educational protocol simulations (ICMP, TCP handshake, UDP, DNS, HTTP)."""

import pytest
from core.network import VirtualNetwork
from core.packet import Protocol
from core.protocols.dns_sim import VirtualDNSServer, resolve_virtual_dns
from core.protocols.http_sim import send_virtual_http_get
from core.protocols.icmp_sim import send_virtual_ping
from core.protocols.tcp_sim import TCPState, simulate_tcp_handshake
from core.protocols.udp_sim import send_virtual_udp
from core.server import VirtualServer, VirtualService


@pytest.fixture
def basic_two_node_net():
    net = VirtualNetwork()
    srv1 = VirtualServer(name="HostA", ip_address="192.168.1.10")
    srv2 = VirtualServer(name="HostB", ip_address="192.168.1.20")
    net.add_device(srv1)
    net.add_device(srv2)

    iface1 = list(srv1.interfaces.values())[0]
    iface2 = list(srv2.interfaces.values())[0]
    net.connect(srv1.device_id, iface1.interface_id, srv2.device_id, iface2.interface_id, latency_ms=4.0)
    return net, srv1, srv2


def test_simulated_ping_success(basic_two_node_net):
    net, srv1, srv2 = basic_two_node_net
    res = send_virtual_ping(net, src_ip="192.168.1.10", dst_ip="192.168.1.20")
    assert res.is_success
    assert res.rtt_ms == 8.0  # 4.0ms each way
    assert res.error_message is None


def test_simulated_ping_unreachable(basic_two_node_net):
    net, srv1, srv2 = basic_two_node_net
    res = send_virtual_ping(net, src_ip="192.168.1.10", dst_ip="192.168.1.99")
    assert not res.is_success
    assert "no virtual host matches" in res.error_message


def test_simulated_tcp_handshake(basic_two_node_net):
    net, srv1, srv2 = basic_two_node_net
    # Configure listening TCP service on port 8080
    srv2.add_service(VirtualService(name="Web", protocol=Protocol.TCP, port=8080))

    # Success case
    res = simulate_tcp_handshake(net, src_ip="192.168.1.10", dst_ip="192.168.1.20", dst_port=8080)
    assert res.is_connected
    assert res.state == TCPState.ESTABLISHED
    assert res.rtt_ms == 8.0

    # Failure case: port closed (connection refused)
    res_closed = simulate_tcp_handshake(net, src_ip="192.168.1.10", dst_ip="192.168.1.20", dst_port=9999)
    assert not res_closed.is_connected
    assert res_closed.state == TCPState.CLOSED
    assert "Connection refused" in res_closed.error_message


def test_simulated_udp(basic_two_node_net):
    net, srv1, srv2 = basic_two_node_net
    srv2.add_service(VirtualService(name="Syslog", protocol=Protocol.UDP, port=514))

    # Send to listening port
    res = send_virtual_udp(net, src_ip="192.168.1.10", dst_ip="192.168.1.20", dst_port=514)
    assert res.is_delivered
    assert res.is_port_open

    # Send to unconfigured port: UDP delivers without error, port is closed
    res2 = send_virtual_udp(net, src_ip="192.168.1.10", dst_ip="192.168.1.20", dst_port=1234)
    assert res2.is_delivered
    assert not res2.is_port_open


def test_simulated_dns_resolution():
    net = VirtualNetwork()
    client = VirtualServer(name="Client", ip_address="10.0.0.10")
    dns_srv = VirtualDNSServer(name="DNS-1", ip_address="10.0.0.53")
    dns_srv.add_record("app.local", "10.0.0.80")

    net.add_device(client)
    net.add_device(dns_srv)

    c_iface = list(client.interfaces.values())[0]
    dns_iface = list(dns_srv.interfaces.values())[0]
    net.connect(client.device_id, c_iface.interface_id, dns_srv.device_id, dns_iface.interface_id, latency_ms=1.5)

    # Resolve existing record
    resp = resolve_virtual_dns(net, client_ip="10.0.0.10", dns_server_ip="10.0.0.53", hostname="app.local")
    assert resp.is_success
    assert resp.resolved_ip == "10.0.0.80"
    assert resp.rtt_ms == 3.0

    # Resolve nonexistent record (NXDOMAIN)
    resp_nx = resolve_virtual_dns(net, client_ip="10.0.0.10", dns_server_ip="10.0.0.53", hostname="unknown.domain")
    assert not resp_nx.is_success
    assert "NXDOMAIN" in resp_nx.error


def test_simulated_http_transaction():
    net = VirtualNetwork()
    client = VirtualServer(name="Client", ip_address="10.0.0.10")
    web_srv = VirtualServer(name="WebServer", ip_address="10.0.0.80")
    web_srv.add_service(VirtualService(name="HTTP", protocol=Protocol.HTTP, port=80))

    net.add_device(client)
    net.add_device(web_srv)

    c_iface = list(client.interfaces.values())[0]
    w_iface = list(web_srv.interfaces.values())[0]
    net.connect(client.device_id, c_iface.interface_id, web_srv.device_id, w_iface.interface_id, latency_ms=2.5)

    # Valid GET
    res = send_virtual_http_get(net, client_ip="10.0.0.10", server_ip="10.0.0.80", port=80, path="/index.html")
    assert res.is_success
    assert res.status_code == 200
    assert "Network Lab Simulation" in res.response_body
    assert res.rtt_ms == 5.0

    # Port not running HTTP service
    res_err = send_virtual_http_get(net, client_ip="10.0.0.10", server_ip="10.0.0.80", port=8080)
    assert not res_err.is_success
    assert "HTTP service not running" in res_err.error_message
