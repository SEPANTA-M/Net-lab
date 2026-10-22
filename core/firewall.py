"""Virtual firewall engine, ordered rule evaluation, and packet filtering."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import ipaddress
import logging
from typing import Any, Dict, List, Optional
import uuid

from core.device import DeviceType, VirtualDevice, VirtualInterface
from core.packet import Packet, PacketState, Protocol

logger = logging.getLogger("network_lab.firewall")


class FirewallAction(str, Enum):
    """Action taken when a firewall rule matches or default policy applies."""

    ALLOW = "ALLOW"
    DENY = "DENY"      # Silently drops packet (drop)
    REJECT = "REJECT"  # Explicitly rejects packet with an ICMP-like response indication


@dataclass
class FirewallDecision:
    """Detailed record of a firewall filtering decision."""

    action: FirewallAction
    matched_rule_id: Optional[str]
    rule_description: str
    packet_id: str
    src_ip: str
    dst_ip: str
    protocol: str
    src_port: Optional[int]
    dst_port: Optional[int]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    explanation: str = ""


@dataclass
class FirewallRule:
    """Configurable virtual firewall rule.

    Evaluated inside the simulation engine. Does NOT alter OS host firewall rules.
    """

    action: FirewallAction
    priority: int = 100  # Lower number = higher priority
    src_cidr: Optional[str] = None  # None matches any source ("0.0.0.0/0")
    dst_cidr: Optional[str] = None  # None matches any destination
    protocol: Optional[Protocol] = None  # None matches any protocol
    src_port: Optional[int] = None  # None matches any source port
    dst_port: Optional[int] = None  # None matches any destination port
    is_enabled: bool = True
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    log_matches: bool = True
    hit_count: int = 0

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate rule parameters."""
        if isinstance(self.action, str) and not isinstance(self.action, FirewallAction):
            try:
                self.action = FirewallAction(self.action.upper())
            except ValueError:
                raise ValueError(f"Invalid firewall action '{self.action}'")

        if self.src_cidr:
            try:
                self.src_net = ipaddress.ip_network(self.src_cidr, strict=False)
            except ValueError as err:
                raise ValueError(f"Invalid src_cidr '{self.src_cidr}': {err}") from err
        else:
            self.src_net = None

        if self.dst_cidr:
            try:
                self.dst_net = ipaddress.ip_network(self.dst_cidr, strict=False)
            except ValueError as err:
                raise ValueError(f"Invalid dst_cidr '{self.dst_cidr}': {err}") from err
        else:
            self.dst_net = None

        for p_name, p_val in (("src_port", self.src_port), ("dst_port", self.dst_port)):
            if p_val is not None:
                if not isinstance(p_val, int) or p_val < 0 or p_val > 65535:
                    raise ValueError(f"Invalid {p_name} '{p_val}': must be 0-65535")

    def matches(self, packet: Packet) -> bool:
        """Evaluate if this rule matches a virtual packet."""
        if not self.is_enabled:
            return False

        # Protocol check
        if self.protocol is not None and packet.protocol != self.protocol:
            return False

        # Source IP check
        if self.src_net is not None:
            try:
                src_addr = ipaddress.ip_address(packet.src_ip)
                if src_addr not in self.src_net:
                    return False
            except ValueError:
                return False

        # Destination IP check
        if self.dst_net is not None:
            try:
                dst_addr = ipaddress.ip_address(packet.dst_ip)
                if dst_addr not in self.dst_net:
                    return False
            except ValueError:
                return False

        # Source port check
        if self.src_port is not None and packet.src_port != self.src_port:
            return False

        # Destination port check
        if self.dst_port is not None and packet.dst_port != self.dst_port:
            return False

        return True


class VirtualFirewall(VirtualDevice):
    """Virtual Firewall device evaluating first-match rules on packets."""

    def __init__(
        self,
        name: str,
        default_action: FirewallAction = FirewallAction.DENY,
        device_id: Optional[str] = None,
    ) -> None:
        if device_id:
            super().__init__(name=name, device_type=DeviceType.FIREWALL, device_id=device_id)
        else:
            super().__init__(name=name, device_type=DeviceType.FIREWALL)
        self.default_action = default_action
        self.rules: List[FirewallRule] = []
        self.decision_log: List[FirewallDecision] = []

    def add_rule(self, rule: FirewallRule) -> FirewallRule:
        """Add a rule and keep rules sorted by priority."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)
        return rule

    def remove_rule(self, rule_id: str) -> Optional[FirewallRule]:
        """Remove a rule by ID."""
        for idx, r in enumerate(self.rules):
            if r.rule_id == rule_id:
                return self.rules.pop(idx)
        return None

    def evaluate(self, packet: Packet) -> FirewallDecision:
        """Evaluate a packet against ordered rules using first-match policy."""
        for rule in self.rules:
            if rule.matches(packet):
                rule.hit_count += 1
                decision = FirewallDecision(
                    action=rule.action,
                    matched_rule_id=rule.rule_id,
                    rule_description=rule.description or f"Rule priority {rule.priority}",
                    packet_id=packet.packet_id,
                    src_ip=packet.src_ip,
                    dst_ip=packet.dst_ip,
                    protocol=str(packet.protocol.value),
                    src_port=packet.src_port,
                    dst_port=packet.dst_port,
                    explanation=f"Matched rule priority {rule.priority}: {rule.action.value}",
                )
                if rule.log_matches:
                    self.decision_log.append(decision)
                return decision

        # Default policy applied
        decision = FirewallDecision(
            action=self.default_action,
            matched_rule_id=None,
            rule_description="Default Policy",
            packet_id=packet.packet_id,
            src_ip=packet.src_ip,
            dst_ip=packet.dst_ip,
            protocol=str(packet.protocol.value),
            src_port=packet.src_port,
            dst_port=packet.dst_port,
            explanation=f"No matching rule; default policy applied: {self.default_action.value}",
        )
        self.decision_log.append(decision)
        return decision

    def to_dict(self) -> Dict[str, Any]:
        """Export firewall configuration to serializable dictionary."""
        return {
            "name": self.name,
            "device_id": self.device_id,
            "default_action": self.default_action.value,
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "action": r.action.value,
                    "priority": r.priority,
                    "src_cidr": r.src_cidr,
                    "dst_cidr": r.dst_cidr,
                    "protocol": r.protocol.value if r.protocol else None,
                    "src_port": r.src_port,
                    "dst_port": r.dst_port,
                    "is_enabled": r.is_enabled,
                    "description": r.description,
                    "log_matches": r.log_matches,
                }
                for r in self.rules
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VirtualFirewall:
        """Create firewall device from configuration dictionary."""
        fw = cls(
            name=data["name"],
            default_action=FirewallAction(data.get("default_action", FirewallAction.DENY.value)),
            device_id=data.get("device_id"),
        )
        for r_data in data.get("rules", []):
            proto = Protocol(r_data["protocol"]) if r_data.get("protocol") else None
            rule = FirewallRule(
                action=FirewallAction(r_data["action"]),
                priority=r_data.get("priority", 100),
                src_cidr=r_data.get("src_cidr"),
                dst_cidr=r_data.get("dst_cidr"),
                protocol=proto,
                src_port=r_data.get("src_port"),
                dst_port=r_data.get("dst_port"),
                is_enabled=r_data.get("is_enabled", True),
                rule_id=r_data.get("rule_id", str(uuid.uuid4())),
                description=r_data.get("description", ""),
                log_matches=r_data.get("log_matches", True),
            )
            fw.add_rule(rule)
        return fw
