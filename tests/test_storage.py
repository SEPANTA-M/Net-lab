"""Tests for storage and project persistence."""

import pytest
from core.packet import Protocol
from core.server import VirtualServer
from storage.database import StorageManager
from storage.scenarios import (
    create_scenario_dns_and_http,
    create_scenario_router_and_firewall,
    create_scenario_two_servers_one_router,
)


def test_sqlite_project_save_and_load():
    sm = StorageManager(":memory:")
    net = create_scenario_two_servers_one_router()

    sm.save_project(
        project_id="proj-1",
        name="Sample Router Project",
        description="Two servers connected via router",
        network=net,
    )

    projects = sm.list_projects()
    assert len(projects) == 1
    assert projects[0]["project_id"] == "proj-1"

    loaded = sm.load_project("proj-1")
    assert loaded is not None
    name, desc, loaded_net = loaded
    assert name == "Sample Router Project"
    assert len(loaded_net.devices) == 3
    assert len(loaded_net.links) == 2


def test_scenarios_construction():
    net1 = create_scenario_two_servers_one_router()
    assert len(net1.devices) == 3

    net2 = create_scenario_router_and_firewall()
    assert len(net2.devices) == 4

    net3 = create_scenario_dns_and_http()
    assert len(net3.devices) == 3
