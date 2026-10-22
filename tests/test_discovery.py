"""Tests for discovery and digital twin mapping."""

import pytest
from digital_twin.topology_mapper import DigitalTwinMapper
from discovery.collector import LocalSystemCollector
from discovery.models import (
    ConfidenceLevel,
    NetworkSnapshot,
    ObservedInterface,
    ObservedRoute,
    ProvenanceSource,
)


def test_local_collector_execution():
    collector = LocalSystemCollector()
    snapshot = collector.collect_snapshot()

    assert snapshot.hostname is not None
    assert isinstance(snapshot.interfaces, list)
    assert len(snapshot.interfaces) >= 1
    # Check provenance
    assert snapshot.interfaces[0].confidence in (ConfidenceLevel.OBSERVED, ConfidenceLevel.INFERRED)


def test_digital_twin_mapper():
    mock_snapshot = NetworkSnapshot(
        hostname="lab-workstation",
        default_gateway="192.168.1.1",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        interfaces=[
            ObservedInterface(
                name="eth0",
                ip_addresses=["192.168.1.150"],
                netmasks=["255.255.255.0"],
                is_up=True,
                mac_address="00:11:22:33:44:55",
            )
        ],
    )

    mapping = DigitalTwinMapper.snapshot_to_virtual_topology(mock_snapshot)
    assert len(mapping.created_devices) == 4  # Host + Gateway + 2 DNS servers
    assert len(mapping.inferred_devices) == 3  # Gateway + 2 DNS servers
    assert len(mapping.created_links) == 1  # Host to Gateway link

    vnet = mapping.virtual_network
    assert vnet.find_device_by_ip("192.168.1.150") is not None
    assert vnet.find_device_by_ip("192.168.1.1") is not None
