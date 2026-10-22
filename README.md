# Network Lab — Advanced Network Discovery, Digital Twin & Simulation Platform

Network Lab is a desktop application combining real-world local network observation with a fully isolated virtual network simulation engine.

## Core Tenet

> **Observe the real network carefully. Model it transparently. Simulate it safely. Never confuse simulated behavior with real network activity.**

Simulated traffic exists entirely as in-memory Python objects and is never transmitted to operating-system network interfaces, physical networks, or raw sockets.

---

## Key Features

1. **Core Virtual Simulation Engine (`core/`)**:
   - `Packet`: In-memory lifecycle states (`CREATED`, `QUEUED`, `ROUTING`, `DELIVERED`, `DROPPED`, `TIMED_OUT`), hop records, IP/CIDR/port validation.
   - `VirtualDevice` & `VirtualServer`: Isolated node models with virtual port listeners and simulated services without host socket binding.
   - `VirtualNetwork`: Link latency, reproducible packet loss (`random_seed`), TTL decrement, and multi-hop delivery.

2. **Virtual Routing (`core/routing.py`)**:
   - Directly connected routes and static routes.
   - Longest-Prefix Matching (LPM) arbitration and metric tie-breaking.
   - Loop detection and route table inspection.

3. **Configurable Firewall (`core/firewall.py`)**:
   - First-match ordered evaluation with configurable priority and default policies (`ALLOW`, `DENY`, `REJECT`).
   - Hit counters, rule match logging, JSON configuration import and export.

4. **Discrete-Event Simulation (`core/scheduler.py`)**:
   - Millisecond-precision priority queue event scheduler.
   - Pause, resume, reset, single-step execution, and event history inspection.

5. **Protocol Lab (`core/protocols/`)**:
   - Educational simulations for ICMP (Echo Request/Reply, reachability), TCP 3-way handshake (`SYN`, `SYN-ACK`, `ACK`), UDP delivery, internal DNS name resolution, and HTTP request/response.

6. **Real Network Observation (`discovery/`)**:
   - Safe, read-only collection of local interfaces, routing tables, default gateway, and DNS resolver configuration.
   - Transparent, opt-in diagnostic checks with clear indicators that real traffic is sent.

7. **Digital Twin Mapping (`digital_twin/`)**:
   - Converts real network snapshots into editable virtual topologies.
   - Explicit confidence labeling distinguishing observed hosts from inferred gateways/DNS resolvers.
   - Virtual topology edits do not alter the host operating system.

8. **Persistence & Scenarios (`storage/`)**:
   - SQLite-backed project persistence.
   - Preconfigured educational scenarios (routers, firewalls, DNS/HTTP services).

9. **PySide6 Desktop GUI (`app/`, `gui/`)**:
   - Modern dark network operations dashboard theme.
   - Sidebar navigation: Overview Dashboard, Interactive Topology Canvas, Firewall Editor, and Diagnostics Lab.

---

## Setup and Running

### Prerequisites
- Python 3.10+
- Dependencies: `pip install -r requirements.txt`

### Running the Desktop GUI
```bash
python3 main.py
```

### Running the Test Suite
All tests run offline without network access:
```bash
pytest -v
```

### Verifying Security & Isolation
Run the security boundary tests to verify that packet transmission and device lifecycles never open host sockets:
```bash
pytest tests/test_security_boundaries.py -v
```
