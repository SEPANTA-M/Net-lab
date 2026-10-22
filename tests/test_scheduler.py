"""Tests for Discrete-Event Simulation Engine and prioritized event scheduler."""

import pytest
from core.scheduler import DiscreteEventScheduler, SchedulerState, SimulationEventType


def test_scheduler_event_ordering():
    scheduler = DiscreteEventScheduler()

    execution_order = []

    # Schedule events with different delays out of order
    scheduler.schedule(delay_ms=20.0, event_type=SimulationEventType.PACKET_DELIVERED, callback=lambda evt: execution_order.append("20ms"))
    scheduler.schedule(delay_ms=5.0, event_type=SimulationEventType.PACKET_CREATED, callback=lambda evt: execution_order.append("5ms"))
    scheduler.schedule(delay_ms=10.0, event_type=SimulationEventType.LINK_DELAY_ELAPSED, callback=lambda evt: execution_order.append("10ms"))

    assert scheduler.pending_event_count == 3
    assert scheduler.current_time_ms == 0.0

    # Execute all events
    count = scheduler.run_all()
    assert count == 3
    assert execution_order == ["5ms", "10ms", "20ms"]
    assert scheduler.current_time_ms == 20.0
    assert scheduler.pending_event_count == 0


def test_scheduler_single_step():
    scheduler = DiscreteEventScheduler()

    scheduler.schedule(delay_ms=5.0, event_type=SimulationEventType.PACKET_CREATED, description="Step 1")
    scheduler.schedule(delay_ms=15.0, event_type=SimulationEventType.PACKET_DELIVERED, description="Step 2")

    # First step
    evt1 = scheduler.step()
    assert evt1 is not None
    assert evt1.scheduled_time_ms == 5.0
    assert evt1.description == "Step 1"
    assert scheduler.current_time_ms == 5.0
    assert scheduler.pending_event_count == 1

    # Second step
    evt2 = scheduler.step()
    assert evt2 is not None
    assert evt2.scheduled_time_ms == 15.0
    assert evt2.description == "Step 2"
    assert scheduler.current_time_ms == 15.0
    assert scheduler.pending_event_count == 0

    # Empty queue returns None
    assert scheduler.step() is None


def test_scheduler_pause_and_resume():
    scheduler = DiscreteEventScheduler()

    ran = []
    scheduler.schedule(delay_ms=5.0, event_type=SimulationEventType.PACKET_CREATED, callback=lambda evt: ran.append(1))
    scheduler.schedule(delay_ms=10.0, event_type=SimulationEventType.PACKET_DELIVERED, callback=lambda evt: ran.append(2))

    scheduler.pause()
    assert scheduler.state == SchedulerState.PAUSED
    scheduler.run_all()
    # When paused, run_all breaks immediately without executing
    assert len(ran) == 0

    scheduler.resume()
    assert scheduler.state == SchedulerState.RUNNING
    scheduler.run_all()
    assert ran == [1, 2]


def test_scheduler_reset():
    scheduler = DiscreteEventScheduler()
    scheduler.schedule(delay_ms=100.0, event_type=SimulationEventType.CUSTOM)
    scheduler.step()
    assert scheduler.current_time_ms == 100.0
    assert len(scheduler.event_history) == 1

    scheduler.reset()
    assert scheduler.current_time_ms == 0.0
    assert scheduler.state == SchedulerState.READY
    assert scheduler.pending_event_count == 0
    assert len(scheduler.event_history) == 0


def test_scheduler_history_cap():
    # Test memory safety bound
    scheduler = DiscreteEventScheduler(max_history=5)
    for i in range(10):
        scheduler.schedule(delay_ms=float(i), event_type=SimulationEventType.CUSTOM)

    scheduler.run_all()
    assert len(scheduler.event_history) == 5
