"""Structured, secret-minimizing orchestration event stream."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from .domain import TaskId


@dataclass(frozen=True, slots=True)
class OrchestrationEvent:
    sequence: int
    task_id: TaskId
    event_type: str
    timestamp: str
    attributes: dict[str, Any] = field(default_factory=dict)


class EventSink(Protocol):
    def emit(self, event: OrchestrationEvent) -> None: ...


class InMemoryEventSink:
    def __init__(self) -> None:
        self.events: list[OrchestrationEvent] = []

    def emit(self, event: OrchestrationEvent) -> None:
        self.events.append(event)


class EventRecorder:
    def __init__(
        self,
        task_id: TaskId,
        sink: EventSink,
        *,
        clock: Callable[[], datetime] | None = None,
        initial_sequence: int = 0,
    ) -> None:
        self._task_id = task_id
        self._sink = sink
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sequence = initial_sequence

    def record(self, event_type: str, **attributes: Any) -> OrchestrationEvent:
        self._sequence += 1
        event = OrchestrationEvent(
            self._sequence,
            self._task_id,
            event_type,
            self._clock().isoformat(),
            attributes,
        )
        self._sink.emit(event)
        return event
