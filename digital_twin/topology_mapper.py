"""Digital Twin mapper converting NetworkSnapshot into an editable VirtualNetwork topology."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import uuid

from core.device import DeviceType, VirtualDevice, VirtualInterface
from core.network import VirtualLink, VirtualNetwork
from core.routing import VirtualRouter
from core.server import VirtualServer
from discovery.models import ConfidenceLevel, NetworkSnapshot


@dataclass
class DigitalTwinMappingResult:
    """Outcome of converting a real snapshot into an editable virtual topology."""

    virtual_network: VirtualNetwork
    created_devices: List[str]
    created_links: List[str]
    inferred_devices: List[str]
    notes: str


class DigitalTwinMapper:
    """Transforms a NetworkSnapshot into an isolated virtual simulation topology.

    Crucial Guarantee:
    - Clear distinction between OBSERVED (real host) and INFERRED (gateway, external DNS).
    - Uncertainty is made explicit.
    - Edits inside the virtual model NEVER propagate to OS network settings.
    """

    @staticmethod
    def snapshot_to_virtual_topology(snapshot: NetworkSnapshot) -> DigitalTwinMappingResult:
        """Construct a VirtualNetwork from a real NetworkSnapshot."""
        vnet = VirtualNetwork()
        created_devices: List[str] = []
        created_links: List[str] = []
        inferred_devices: List[str] = []

        # 1. Map Local Host Node (Observed)
        local_host = VirtualServer(
            name=f"{snapshot.hostname} (Local Host)",
            device_id=str(uuid.uuid4()),
        )
        local_host.metadata["origin"] = "OBSERVED"
        local_host.metadata["confidence"] = ConfidenceLevel.OBSERVED.value

        for ifc in snapshot.interfaces:
            ip_str = ifc.ip_addresses[0] if ifc.ip_addresses else "192.168.1.100"
            mask_str = ifc.netmasks[0] if ifc.netmasks else "255.255.255.0"
            v_iface = VirtualInterface(
                name=ifc.name,
                ip_address=ip_str,
                subnet_mask=mask_str,
                mac_address=ifc.mac_address,
                is_up=ifc.is_up,
            )
            local_host.add_interface(v_iface)

        vnet.add_device(local_host)
        created_devices.append(local_host.name)

        # 2. Map Default Gateway if discovered (Inferred device)
        if snapshot.default_gateway:
            gw_router = VirtualRouter(
                name=f"Gateway-{snapshot.default_gateway} (Inferred)",
                device_id=str(uuid.uuid4()),
            )
            gw_router.metadata["origin"] = "INFERRED"
            gw_router.metadata["confidence"] = ConfidenceLevel.INFERRED.value

            # Gateway interface connected to local subnet
            gw_iface = VirtualInterface(
                name="lan0",
                ip_address=snapshot.default_gateway,
                subnet_mask="255.255.255.0",
            )
            gw_router.add_interface(gw_iface)
            vnet.add_device(gw_router)
            created_devices.append(gw_router.name)
            inferred_devices.append(gw_router.name)

            # Connect local host interface to gateway router
            host_iface = list(local_host.interfaces.values())[0] if local_host.interfaces else None
            if host_iface:
                link = vnet.connect(
                    local_host.device_id,
                    host_iface.interface_id,
                    gw_router.device_id,
                    gw_iface.interface_id,
                    latency_ms=1.5,
                )
                link.notes = "Inferred link to default gateway"
                created_links.append(link.link_id)

        # 3. Map DNS Resolvers (Inferred servers)
        for dns_ip in snapshot.dns_servers:
            dns_dev = VirtualServer(
                name=f"DNS-{dns_ip} (Inferred)",
                ip_address=dns_ip,
                device_id=str(uuid.uuid4()),
            )
            dns_dev.metadata["origin"] = "INFERRED"
            dns_dev.metadata["confidence"] = ConfidenceLevel.INFERRED.value
            vnet.add_device(dns_dev)
            created_devices.append(dns_dev.name)
            inferred_devices.append(dns_dev.name)

        return DigitalTwinMappingResult(
            virtual_network=vnet,
            created_devices=created_devices,
            created_links=created_links,
            inferred_devices=inferred_devices,
            notes=f"Generated virtual topology with {len(created_devices)} devices from snapshot.",
        )
