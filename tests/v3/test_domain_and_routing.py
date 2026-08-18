from __future__ import annotations

from pathlib import Path

import pytest

from gemma_qat_bench.orchestration.domain import (
    CommandId,
    DomainError,
    RequiredCommand,
    RevisionBudget,
    RiskLevel,
    TaskId,
    TaskSpec,
    WorkflowDepth,
    WorkflowState,
    normalize_repository_path,
)
from gemma_qat_bench.orchestration.routing import POLICY_VERSION, RoutingPolicy
from gemma_qat_bench.orchestration.state_machine import (
    InvalidTransition,
    WorkflowMachine,
    allowed_transitions,
)


def task(root: Path, risk: RiskLevel, fast_eligible: bool) -> TaskSpec:
    return TaskSpec(
        TaskId("T-1"),
        "change one exact value",
        ("focused check passes",),
        risk,
        fast_eligible,
        root.resolve(),
        (RequiredCommand(CommandId("CMD-001"), ("pytest", "-q")),),
        ("product.py",),
    )


def test_task_and_path_invariants(tmp_path: Path) -> None:
    with pytest.raises(DomainError):
        TaskId("has whitespace")
    with pytest.raises(DomainError):
        TaskId("../../escape")
    with pytest.raises(DomainError):
        normalize_repository_path("../secret")
    with pytest.raises(DomainError):
        RequiredCommand(CommandId("CMD"), ("pytest",), cwd="../outside")
    with pytest.raises(DomainError):
        TaskSpec(
            TaskId("T"),
            "work",
            ("done",),
            RiskLevel.STANDARD,
            False,
            tmp_path.resolve(),
            (
                RequiredCommand(CommandId("CMD"), ("true",)),
                RequiredCommand(CommandId("CMD"), ("true",)),
            ),
            ("a.py",),
        )


def test_task_requires_at_least_one_required_verification_command(
    tmp_path: Path,
) -> None:
    """Regression: a task with no required command reached CHANGE_COMPLETE with an
    empty evidence ledger and without any observable command authorization."""
    for commands in (
        (),
        (RequiredCommand(CommandId("CMD-OPT"), ("true",), required=False),),
    ):
        with pytest.raises(DomainError, match="required verification command"):
            TaskSpec(
                TaskId("T-EMPTY"),
                "change one exact value",
                ("focused check passes",),
                RiskLevel.TRIVIAL_MECHANICAL,
                True,
                tmp_path.resolve(),
                commands,
                ("product.py",),
            )
    optional_plus_required = TaskSpec(
        TaskId("T-MIXED"),
        "change one exact value",
        ("focused check passes",),
        RiskLevel.TRIVIAL_MECHANICAL,
        True,
        tmp_path.resolve(),
        (
            RequiredCommand(CommandId("CMD-OPT"), ("true",), required=False),
            RequiredCommand(CommandId("CMD-REQ"), ("pytest", "-q")),
        ),
        ("product.py",),
    )
    assert any(command.required for command in optional_plus_required.required_commands)


def test_task_fingerprint_scope_is_stored_in_canonical_form(tmp_path: Path) -> None:
    """Regression: a validated-but-raw spelling such as "./product.py" was kept
    verbatim, never matched the git-normalized delta paths, and made every run
    escalate with fingerprint drift after the commands had already executed."""
    spec = TaskSpec(
        TaskId("T-NORM"),
        "change one exact value",
        ("focused check passes",),
        RiskLevel.TRIVIAL_MECHANICAL,
        True,
        tmp_path.resolve(),
        (RequiredCommand(CommandId("CMD-001"), ("pytest", "-q")),),
        ("./product.py", "src\\nested\\module.py"),
    )
    assert spec.fingerprint_scope == ("product.py", "src/nested/module.py")


def test_revision_budget_is_bounded_and_immutable() -> None:
    first = RevisionBudget("repair", 1)
    consumed = first.consume()
    assert first.consumed == 0
    assert consumed.remaining == 0
    with pytest.raises(DomainError, match="exhausted"):
        consumed.consume()


@pytest.mark.parametrize(
    ("risk", "eligible", "expected"),
    [
        (RiskLevel.TRIVIAL_MECHANICAL, True, WorkflowDepth.FAST),
        (RiskLevel.TRIVIAL_MECHANICAL, False, WorkflowDepth.FULL),
        (RiskLevel.LOW_RISK, True, WorkflowDepth.FULL),
        (RiskLevel.STANDARD, True, WorkflowDepth.FULL),
        (RiskLevel.HIGH_RISK, True, WorkflowDepth.FULL),
    ],
)
def test_routing_preserves_conservative_v2_rule(
    tmp_path: Path,
    risk: RiskLevel,
    eligible: bool,
    expected: WorkflowDepth,
) -> None:
    decision = RoutingPolicy().decide(task(tmp_path, risk, eligible))
    assert decision.native_depth is expected
    assert decision.policy_version == POLICY_VERSION
    assert decision.risk is risk


def test_state_machine_accepts_only_explicit_transitions() -> None:
    machine = WorkflowMachine(WorkflowDepth.FULL)
    machine.transition(WorkflowState.PLANNING)
    machine.transition(WorkflowState.PLAN_CRITIQUE)
    machine.transition(WorkflowState.GATE_1)
    machine.transition(WorkflowState.IMPLEMENTATION)
    assert WorkflowState.COMMAND_VERIFICATION in allowed_transitions(machine.state)
    with pytest.raises(InvalidTransition):
        machine.transition(WorkflowState.COMPLETE)


def test_waiting_authorization_is_only_reachable_from_command_verification() -> None:
    """Regression: unused GATE_1/IMPLEMENTATION edges into WAITING_AUTHORIZATION
    would have allowed resume to enter COMMAND_VERIFICATION without an
    implementation ever running."""
    entry_points = [
        state
        for state, targets in (
            (candidate, allowed_transitions(candidate)) for candidate in WorkflowState
        )
        if WorkflowState.WAITING_AUTHORIZATION in targets
    ]
    assert entry_points == [WorkflowState.COMMAND_VERIFICATION]
    for state in (WorkflowState.GATE_1, WorkflowState.IMPLEMENTATION):
        machine = WorkflowMachine(WorkflowDepth.FULL, state)
        with pytest.raises(InvalidTransition):
            machine.transition(WorkflowState.WAITING_AUTHORIZATION)


def test_fast_escalation_is_explicit_and_guarded() -> None:
    machine = WorkflowMachine(WorkflowDepth.FAST, WorkflowState.GATE_2)
    machine.escalate_fast_to_full()
    assert machine.depth is WorkflowDepth.FULL
    assert machine.state is WorkflowState.PLANNING
    with pytest.raises(InvalidTransition):
        machine.escalate_fast_to_full()
