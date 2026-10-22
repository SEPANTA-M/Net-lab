"""Tests for Virtual Firewall engine, ordered evaluation, and packet filtering."""

import json
import pytest
from core.firewall import FirewallAction, FirewallRule, VirtualFirewall
from core.packet import Packet, PacketState, Protocol


def test_firewall_rule_validation():
    # Valid rule
    rule = FirewallRule(
        action=FirewallAction.ALLOW,
        priority=10,
        src_cidr="192.168.1.0/24",
        dst_cidr="10.0.0.0/8",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    assert rule.priority == 10
    assert rule.action == FirewallAction.ALLOW

    # Invalid CIDR
    with pytest.raises(ValueError, match="Invalid src_cidr"):
        FirewallRule(action=FirewallAction.ALLOW, src_cidr="bad_cidr")

    # Invalid Port
    with pytest.raises(ValueError, match="Invalid dst_port"):
        FirewallRule(action=FirewallAction.DENY, dst_port=70000)


def test_firewall_first_match_and_ordering():
    fw = VirtualFirewall(name="Corp-FW", default_action=FirewallAction.DENY)

    # Low priority number = evaluated first
    # Rule 1: ALLOW HTTP to 10.0.0.50:80 (priority 10)
    r1 = FirewallRule(
        action=FirewallAction.ALLOW,
        priority=10,
        protocol=Protocol.TCP,
        dst_cidr="10.0.0.50/32",
        dst_port=80,
        description="Allow HTTP to WebServer",
    )
    # Rule 2: DENY all other TCP to 10.0.0.0/24 (priority 20)
    r2 = FirewallRule(
        action=FirewallAction.DENY,
        priority=20,
        protocol=Protocol.TCP,
        dst_cidr="10.0.0.0/24",
        description="Deny other TCP to subnet",
    )
    # Add out of order to test priority sorting
    fw.add_rule(r2)
    fw.add_rule(r1)

    # Packet to 10.0.0.50:80 should MATCH r1 and be ALLOWED
    pkt_http = Packet(src_ip="192.168.1.5", dst_ip="10.0.0.50", protocol=Protocol.TCP, dst_port=80)
    dec1 = fw.evaluate(pkt_http)
    assert dec1.action == FirewallAction.ALLOW
    assert dec1.matched_rule_id == r1.rule_id
    assert r1.hit_count == 1

    # Packet to 10.0.0.50:22 should MATCH r2 and be DENIED
    pkt_ssh = Packet(src_ip="192.168.1.5", dst_ip="10.0.0.50", protocol=Protocol.TCP, dst_port=22)
    dec2 = fw.evaluate(pkt_ssh)
    assert dec2.action == FirewallAction.DENY
    assert dec2.matched_rule_id == r2.rule_id
    assert r2.hit_count == 1

    # Packet to 8.8.8.8 should trigger DEFAULT POLICY (DENY)
    pkt_ext = Packet(src_ip="192.168.1.5", dst_ip="8.8.8.8", protocol=Protocol.UDP, dst_port=53)
    dec3 = fw.evaluate(pkt_ext)
    assert dec3.action == FirewallAction.DENY
    assert dec3.matched_rule_id is None
    assert "default policy" in dec3.explanation


def test_firewall_import_export():
    fw = VirtualFirewall(name="Edge-FW", default_action=FirewallAction.ALLOW)
    rule = FirewallRule(
        action=FirewallAction.DENY,
        priority=5,
        protocol=Protocol.ICMP,
        description="Block ping",
    )
    fw.add_rule(rule)

    fw_dict = fw.to_dict()
    assert fw_dict["name"] == "Edge-FW"
    assert fw_dict["default_action"] == "ALLOW"
    assert len(fw_dict["rules"]) == 1

    # Reconstitute from dict
    fw2 = VirtualFirewall.from_dict(fw_dict)
    assert fw2.name == "Edge-FW"
    assert fw2.default_action == FirewallAction.ALLOW
    assert len(fw2.rules) == 1
    assert fw2.rules[0].protocol == Protocol.ICMP
    assert fw2.rules[0].action == FirewallAction.DENY


def test_deny_vs_reject_distinction():
    rule_deny = FirewallRule(action=FirewallAction.DENY, protocol=Protocol.TCP, dst_port=23)
    rule_reject = FirewallRule(action=FirewallAction.REJECT, protocol=Protocol.TCP, dst_port=21)

    assert rule_deny.action == FirewallAction.DENY
    assert rule_reject.action == FirewallAction.REJECT
    assert rule_deny.action != rule_reject.action
