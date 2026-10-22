"""Discrete-event simulation engine, event models, and prioritized event scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import heapq
import itertools
import logging
from typing import Any, Callable, Dict, List, Optional
import uuid

logger = logging.getLogger("network_lab.scheduler")


class SimulationEventType(str, Enum):
    """Categorization of discrete simulation events."""

    PACKET_CREATED = "PACKET_CREATED"
    PACKET_QUEUED = "PACKET_QUEUED"
    PACKET_FORWARDED = "PACKET_FORWARDED"
    FIREWALL_EVALUATED = "FIREWALL_EVALUATED"
    LINK_DELAY_ELAPSED = "LINK_DELAY_ELAPSED"
    PACKET_DELIVERED = "PACKET_DELIVERED"
    PACKET_DROPPED = "PACKET_DROPPED"
    SERVICE_RESPONSE = "SERVICE_RESPONSE"
    TIMEOUT = "TIMEOUT"
    CUSTOM = "CUSTOM"


class SchedulerState(str, Enum):
    """State of the simulation scheduler."""

    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


@dataclass(order=True)
class SimulationEvent:
    """An event scheduled at a specific simulation virtual time (ms)."""

    scheduled_time_ms: float
    sequence_id: int = field(compare=True)
    event_type: SimulationEventType = field(compare=False)
    description: str = field(compare=False, default="")
    callback: Optional[Callable[..., Any]] = field(compare=False, default=None)
    data: Dict[str, Any] = field(compare=False, default_factory=dict)
    event_id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4()))


class DiscreteEventScheduler:
    """Deterministic, priority-queue driven discrete-event scheduler.

    Decouples simulation virtual time (in milliseconds) from wall-clock time.
    Provides pause, resume, reset, single-step execution, and event history inspection.
    """

    def __init__(self, max_history: int = 5000) -> None:
        self.current_time_ms: float = 0.0
        self.state: SchedulerState = SchedulerState.READY
        self.event_queue: List[SimulationEvent] = []
        self.event_history: List[SimulationEvent] = []
        self.max_history = max_history
        self._seq_counter = itertools.count()

    def schedule(
        self,
        delay_ms: float,
        event_type: SimulationEventType,
        description: str = "",
        callback: Optional[Callable[..., Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> SimulationEvent:
        """Schedule an event at current_time_ms + delay_ms."""
        if delay_ms < 0:
            raise ValueError(f"Event delay_ms cannot be negative: {delay_ms}")

        scheduled_time = self.current_time_ms + delay_ms
        seq = next(self._seq_counter)
        evt = SimulationEvent(
            scheduled_time_ms=scheduled_time,
            sequence_id=seq,
            event_type=event_type,
            description=description,
            callback=callback,
            data=data or {},
        )
        heapq.heappush(self.event_queue, evt)
        return evt

    def step(self) -> Optional[SimulationEvent]:
        """Advance simulation by executing exactly one scheduled event."""
        if not self.event_queue:
            return None

        event = heapq.heappop(self.event_queue)
        self.current_time_ms = event.scheduled_time_ms

        # Execute callback if defined
        if event.callback:
            try:
                event.callback(event)
            except Exception as e:
                logger.error(f"Error executing event callback: {e}", exc_info=True)

        # Record history with upper-bound trimming to prevent memory exhaustion
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        return event

    def run_until(self, target_time_ms: float) -> int:
        """Run simulation events until reaching the target virtual time."""
        self.state = SchedulerState.RUNNING
        executed_count = 0
        while self.event_queue and self.event_queue[0].scheduled_time_ms <= target_time_ms:
            if self.state == SchedulerState.PAUSED or self.state == SchedulerState.STOPPED:
                break
            self.step()
            executed_count += 1
        return executed_count

    def run_all(self, max_events: int = 10000) -> int:
        """Process all scheduled events up to max_events limit."""
        if self.state == SchedulerState.PAUSED:
            return 0
        self.state = SchedulerState.RUNNING
        count = 0
        while self.event_queue and count < max_events:
            if self.state == SchedulerState.PAUSED or self.state == SchedulerState.STOPPED:
                break
            self.step()
            count += 1
        if self.state != SchedulerState.PAUSED:
            self.state = SchedulerState.STOPPED
        return count

    def pause(self) -> None:
        """Pause the scheduler."""
        self.state = SchedulerState.PAUSED

    def resume(self) -> None:
        """Resume the paused scheduler."""
        self.state = SchedulerState.RUNNING

    def reset(self) -> None:
        """Reset the scheduler clock and clear queued events."""
        self.current_time_ms = 0.0
        self.state = SchedulerState.READY
        self.event_queue.clear()
        self.event_history.clear()

    @property
    def pending_event_count(self) -> int:
        """Number of events currently awaiting execution in the priority queue."""
        return len(self.event_queue)
