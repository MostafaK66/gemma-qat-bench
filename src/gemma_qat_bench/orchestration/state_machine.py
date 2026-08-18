"""Explicit, provider-independent orchestration state transitions."""

from __future__ import annotations

from dataclasses import dataclass

from .domain import DomainError, WorkflowDepth, WorkflowState


class InvalidTransition(DomainError):
    """Raised when a caller attempts a transition outside the graph."""


_ALLOWED: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.INTAKE: frozenset(
        {WorkflowState.PLANNING, WorkflowState.IMPLEMENTATION, WorkflowState.ESCALATED}
    ),
    WorkflowState.PLANNING: frozenset(
        {WorkflowState.PLAN_CRITIQUE, WorkflowState.ESCALATED, WorkflowState.FAILED}
    ),
    WorkflowState.PLAN_CRITIQUE: frozenset(
        {WorkflowState.GATE_1, WorkflowState.ESCALATED, WorkflowState.FAILED}
    ),
    WorkflowState.GATE_1: frozenset(
        {
            WorkflowState.PLANNING,
            WorkflowState.IMPLEMENTATION,
            WorkflowState.ESCALATED,
        }
    ),
    WorkflowState.IMPLEMENTATION: frozenset(
        {
            WorkflowState.COMMAND_VERIFICATION,
            WorkflowState.ESCALATED,
            WorkflowState.FAILED,
        }
    ),
    WorkflowState.COMMAND_VERIFICATION: frozenset(
        {
            WorkflowState.GATE_2,
            WorkflowState.IMPLEMENTATION,
            WorkflowState.WAITING_AUTHORIZATION,
            WorkflowState.ESCALATED,
            WorkflowState.FAILED,
        }
    ),
    WorkflowState.GATE_2: frozenset(
        {
            WorkflowState.IMPLEMENTATION,
            WorkflowState.REVIEW,
            WorkflowState.COMPLETE,
            WorkflowState.ESCALATING,
            WorkflowState.ESCALATED,
            WorkflowState.FAILED,
        }
    ),
    WorkflowState.REVIEW: frozenset(
        {WorkflowState.GATE_3, WorkflowState.ESCALATED, WorkflowState.FAILED}
    ),
    WorkflowState.GATE_3: frozenset(
        {WorkflowState.IMPLEMENTATION, WorkflowState.COMPLETE, WorkflowState.ESCALATED}
    ),
    WorkflowState.ESCALATING: frozenset(
        {WorkflowState.PLANNING, WorkflowState.ESCALATED}
    ),
    WorkflowState.WAITING_AUTHORIZATION: frozenset(
        {WorkflowState.COMMAND_VERIFICATION, WorkflowState.ESCALATED}
    ),
    WorkflowState.ESCALATED: frozenset(),
    WorkflowState.FAILED: frozenset(),
    WorkflowState.COMPLETE: frozenset(),
}


@dataclass(slots=True)
class WorkflowMachine:
    depth: WorkflowDepth
    state: WorkflowState = WorkflowState.INTAKE

    def transition(self, target: WorkflowState) -> None:
        if target not in _ALLOWED[self.state]:
            raise InvalidTransition(
                f"illegal workflow transition: {self.state} -> {target}"
            )
        self.state = target

    def escalate_fast_to_full(self) -> None:
        if self.depth is not WorkflowDepth.FAST or self.state is not WorkflowState.GATE_2:
            raise InvalidTransition(
                "FAST to FULL escalation is only valid at FAST Gate 2"
            )
        self.transition(WorkflowState.ESCALATING)
        self.depth = WorkflowDepth.FULL
        self.transition(WorkflowState.PLANNING)


def allowed_transitions(state: WorkflowState) -> frozenset[WorkflowState]:
    """Expose a read-only graph projection for diagnostics and tests."""
    return _ALLOWED[state]
