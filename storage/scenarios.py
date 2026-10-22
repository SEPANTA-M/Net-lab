"""Preconfigured educational scenarios for Network Lab."""

from core.device import VirtualInterface
from core.firewall import FirewallAction, FirewallRule, VirtualFirewall
from core.network import VirtualNetwork
from core.protocols.dns_sim import VirtualDNSServer
from core.routing import VirtualRouter
from core.server import VirtualServer, VirtualService
from core.packet import Protocol


def create_scenario_two_servers_one_router() -> VirtualNetwork:
    """Scenario 1: Two servers connected through one virtual router."""
    net = VirtualNetwork()
    srv1 = VirtualServer(name="Web1", ip_address="192.168.1.10")
    srv2 = VirtualServer(name="DB1", ip_address="192.168.2.20")
    r1 = VirtualRouter(name="Core-Router")
    if1 = VirtualInterface(name="eth0", ip_address="192.168.1.1")
    if2 = VirtualInterface(name="eth1", ip_address="192.168.2.1")
    r1.add_interface(if1)
    r1.add_interface(if2)

    net.add_device(srv1)
    net.add_device(srv2)
    net.add_device(r1)

    net.connect(srv1.device_id, list(srv1.interfaces.values())[0].interface_id, r1.device_id, if1.interface_id, latency_ms=1.5)
    net.connect(r1.device_id, if2.interface_id, srv2.device_id, list(srv2.interfaces.values())[0].interface_id, latency_ms=2.0)
    return net


def create_scenario_router_and_firewall() -> VirtualNetwork:
    """Scenario 2: A router and firewall between two virtual subnets."""
    net = VirtualNetwork()
    client = VirtualServer(name="Client", ip_address="10.0.1.10")
    r1 = VirtualRouter(name="BorderRouter")
    fw = VirtualFirewall(name="SubnetFirewall", default_action=FirewallAction.DENY)
    server = VirtualServer(name="InternalApp", ip_address="10.0.2.50")
    server.add_service(VirtualService(name="HTTP", protocol=Protocol.HTTP, port=80))

    # Allow HTTP port 80 only
    fw.add_rule(FirewallRule(action=FirewallAction.ALLOW, protocol=Protocol.TCP, dst_port=80, description="Allow HTTP"))

    r_if1 = VirtualInterface(name="eth0", ip_address="10.0.1.1")
    r_if2 = VirtualInterface(name="eth1", ip_address="10.0.2.1")
    r1.add_interface(r_if1)
    r1.add_interface(r_if2)

    fw_if1 = VirtualInterface(name="fw0", ip_address="10.0.2.2")
    fw.add_interface(fw_if1)

    net.add_device(client)
    net.add_device(r1)
    net.add_device(fw)
    net.add_device(server)

    net.connect(client.device_id, list(client.interfaces.values())[0].interface_id, r1.device_id, r_if1.interface_id)
    net.connect(r1.device_id, r_if2.interface_id, fw.device_id, fw_if1.interface_id)
    net.connect(fw.device_id, fw_if1.interface_id, server.device_id, list(server.interfaces.values())[0].interface_id)
    return net


def create_scenario_dns_and_http() -> VirtualNetwork:
    """Scenario 3: DNS service and virtual HTTP server."""
    net = VirtualNetwork()
    client = VirtualServer(name="UserHost", ip_address="192.168.1.100")
    dns_srv = VirtualDNSServer(name="LocalDNS", ip_address="192.168.1.2")
    dns_srv.add_record("shop.lab", "192.168.1.50")
    web_srv = VirtualServer(name="ShopWeb", ip_address="192.168.1.50")
    web_srv.add_service(VirtualService(name="HTTP", protocol=Protocol.HTTP, port=80))

    net.add_device(client)
    net.add_device(dns_srv)
    net.add_device(web_srv)

    c_iface = list(client.interfaces.values())[0]
    dns_iface = list(dns_srv.interfaces.values())[0]
    web_iface = list(web_srv.interfaces.values())[0]

    net.connect(client.device_id, c_iface.interface_id, dns_srv.device_id, dns_iface.interface_id, latency_ms=1.0)
    net.connect(client.device_id, c_iface.interface_id, web_srv.device_id, web_iface.interface_id, latency_ms=1.5)
    return net
