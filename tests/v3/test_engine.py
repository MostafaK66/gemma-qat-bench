from __future__ import annotations

import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any

import pytest

from gemma_qat_bench.orchestration.authorization import StaticAuthorization
from gemma_qat_bench.orchestration.commands import CommandBroker, RunnerResult
from gemma_qat_bench.orchestration.domain import (
    AuthorizationStatus,
    CommandId,
    CompletionStatus,
    FailureKind,
    RequiredCommand,
    RiskLevel,
    SpecialistRole,
    TaskId,
    TaskSpec,
    WorkflowDepth,
    WorkflowState,
)
from gemma_qat_bench.orchestration.engine import Orchestrator
from gemma_qat_bench.orchestration.events import InMemoryEventSink
from gemma_qat_bench.orchestration.fingerprint import FingerprintService
from gemma_qat_bench.orchestration.persistence import InMemoryWorkflowStore
from gemma_qat_bench.orchestration.scope import WorkspaceChangeDetector
from gemma_qat_bench.orchestration.specialists import (
    ProviderCapabilities,
    ScriptedResponse,
    ScriptedSpecialistClient,
    SpecialistClient,
    SpecialistRequest,
    SpecialistResult,
)


def encoded(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True)


def plan(task_id: str = "T-1") -> dict[str, Any]:
    return {
        "task_id": task_id,
        "goal": "make the requested change",
        "current_behavior": "the old value is present",
        "owning_responsibility": "product.py",
        "files_expected_to_change": ["product.py"],
        "implementation_steps": ["update product.py"],
        "acceptance_criteria": ["focused check passes"],
        "risks": [],
        "out_of_scope": [],
        "open_questions": [],
    }


def critique(verdict: str = "APPROVED", *, human: bool = False) -> dict[str, Any]:
    findings = []
    if verdict == "CHANGES_REQUESTED":
        findings = [
            {
                "finding_id": "PLAN-1",
                "classification": (
                    "HUMAN_INTENT_REQUIRED" if human else "EVIDENCE_RESOLVABLE"
                ),
                "decision_question": "which existing contract controls?",
                "impact_scope": "product.py",
                "evidence_basis": "repository contract",
                "required_correction": "cite and follow the existing contract",
                "why_not_uniquely_resolved": "human choice remains"
                if human
                else "not applicable",
            }
        ]
    return {
        "task_id": "T-1",
        "plan_version": 1 if verdict == "CHANGES_REQUESTED" else 1,
        "verdict": verdict,
        "blocking_findings": findings,
        "suggestions": [],
        "evidence_checked": ["product.py"],
        "residual_risks": [],
    }


def approved_critique(version: int = 1) -> dict[str, Any]:
    value = critique()
    value["plan_version"] = version
    return value


def implementation(
    *, depth: str = "FAST", iteration: int = 1, plan_reference: str | None = None
) -> dict[str, Any]:
    return {
        "task_id": "T-1",
        "depth": depth,
        "plan_reference": plan_reference
        or ("FAST-INTAKE" if depth == "FAST" else "PLAN-1"),
        "iteration": iteration,
        "disposition": "COMPLETED",
        "steps_implemented": ["updated product.py"],
        "files_changed": ["product.py"],
        "tests_changed": [],
        "documentation_changes": [],
        "deviations": [],
        "blockers": [],
        "residual_risks": [],
    }


def verification(
    *,
    depth: str = "FAST",
    verdict: str = "PASSED",
    implementation_iteration: int = 1,
    plan_reference: str | None = None,
) -> dict[str, Any]:
    findings = []
    quality = "sufficient"
    if verdict == "FAILED":
        quality = "insufficient"
        findings = [
            {
                "finding_id": "VERIFY-1",
                "finding_kind": "IMPLEMENTATION_DEFECT",
                "resolution_class": "EVIDENCE_RESOLVABLE",
                "affected_criterion": "focused check passes",
                "evidence": "implementation behavior is incomplete",
                "required_next_action": "repair the implementation",
            }
        ]
    return {
        "task_id": "T-1",
        "depth": depth,
        "plan_reference": plan_reference
        or ("FAST-INTAKE" if depth == "FAST" else "PLAN-1"),
        "implementation_iteration": implementation_iteration,
        "verification_iteration": 1,
        "verdict": verdict,
        "acceptance_checks": ["focused criterion checked"],
        "command_assessments": [
            {
                "command_id": "CMD-001",
                "evidence_quality": quality,
                "evidence_assessment": "command evidence reviewed",
                "rationale": "canonical result supports this assessment",
            }
        ],
        "blocking_findings": findings,
        "environment_limitations": [],
        "residual_risks": [],
    }


def review(
    *,
    verdict: str = "APPROVED",
    implementation_iteration: int = 1,
    plan_version: int = 1,
) -> dict[str, Any]:
    findings = []
    if verdict == "CHANGES_REQUESTED":
        findings = [
            {
                "finding_id": "REVIEW-1",
                "finding_kind": "IMPLEMENTATION_DEFECT",
                "resolution_class": "EVIDENCE_RESOLVABLE",
                "severity": "medium",
                "location": "product.py",
                "problem": "edge case is missing",
                "impact": "behavior is incomplete",
                "evidence_basis": "current source",
                "required_next_action": "handle the edge case",
            }
        ]
    return {
        "task_id": "T-1",
        "plan_version": plan_version,
        "implementation_iteration": implementation_iteration,
        "verdict": verdict,
        "evidence_reviewed": ["implementation", "verification"],
        "blocking_findings": findings,
        "scope_assessment": "within scope",
        "quality_assessment": "acceptable" if not findings else "repair required",
        "residual_risks": [],
    }


def response(role: SpecialistRole, value: dict[str, Any] | str) -> ScriptedResponse:
    return ScriptedResponse(role, value if isinstance(value, str) else encoded(value))


class FileIdentities:
    def __init__(self, root: Path) -> None:
        self.root = root

    def identity(self, relative_path: str) -> str:
        return hashlib.sha256((self.root / relative_path).read_bytes()).hexdigest()


class StaticScopeDetector:
    def capture(self) -> dict[str, str]:
        return {}


class OutOfScopeDetector:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.calls = 0

    def capture(self) -> dict[str, str]:
        self.calls += 1
        if self.calls < 3:
            return {}
        self.path.write_text("unexpected", encoding="utf-8")
        return {self.path.name: "unexpected-identity"}


class Runner:
    def __init__(
        self,
        results: list[RunnerResult] | None = None,
        *,
        mutate: Path | None = None,
    ) -> None:
        self.results = deque(results or [RunnerResult(0, "passed")])
        self.mutate = mutate

    def run(self, command: RequiredCommand) -> RunnerResult:
        if self.mutate is not None:
            self.mutate.write_text("drift", encoding="utf-8")
            self.mutate = None
        return self.results.popleft()


class CrashRunner:
    def run(self, command: RequiredCommand) -> RunnerResult:
        raise RuntimeError("simulated process interruption")


class CountingRunner:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, command: RequiredCommand) -> RunnerResult:
        self.calls += 1
        return RunnerResult(0, "passed")


class MutatingClient:
    def __init__(self, delegate: ScriptedSpecialistClient, path: Path) -> None:
        self.delegate = delegate
        self.path = path

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self.delegate.capabilities

    def invoke(self, request: SpecialistRequest) -> SpecialistResult:
        result = self.delegate.invoke(request)
        if request.invocation.role is SpecialistRole.VERIFIER:
            self.path.write_text("review drift", encoding="utf-8")
        return result


def task_spec(tmp_path: Path, *, full: bool = False) -> TaskSpec:
    (tmp_path / "product.py").write_text("original", encoding="utf-8")
    return TaskSpec(
        TaskId("T-1"),
        "make an exact tested change",
        ("focused check passes",),
        RiskLevel.STANDARD if full else RiskLevel.TRIVIAL_MECHANICAL,
        not full,
        tmp_path.resolve(),
        (RequiredCommand(CommandId("CMD-001"), ("pytest", "-q")),),
        ("product.py",),
    )


def engine(
    spec: TaskSpec,
    client: SpecialistClient,
    *,
    runner: Any | None = None,
    authorized: bool = True,
    store: InMemoryWorkflowStore | None = None,
    events: InMemoryEventSink | None = None,
    scope_detector: WorkspaceChangeDetector | None = None,
    authorization_status: AuthorizationStatus | None = None,
) -> Orchestrator:
    policy = StaticAuthorization(
        commands=authorization_status
        or (AuthorizationStatus.AUTHORIZED if authorized else AuthorizationStatus.DENIED)
    )
    broker = CommandBroker(runner or Runner(), policy)
    fingerprints = FingerprintService(
        spec.repository_root, FileIdentities(spec.repository_root)
    )
    return Orchestrator(
        client,
        broker,
        fingerprints,
        store=store,
        events=events,
        scope_detector=scope_detector or StaticScopeDetector(),
    )


def fast_success_script() -> list[ScriptedResponse]:
    return [
        response(SpecialistRole.IMPLEMENTER, implementation()),
        response(SpecialistRole.VERIFIER, verification()),
    ]


def full_success_script() -> list[ScriptedResponse]:
    return [
        response(SpecialistRole.PLANNER, plan()),
        response(SpecialistRole.PLAN_CRITIC, approved_critique()),
        response(SpecialistRole.IMPLEMENTER, implementation(depth="FULL")),
        response(SpecialistRole.VERIFIER, verification(depth="FULL")),
        response(SpecialistRole.REVIEWER, review()),
    ]


def test_successful_fast_workflow(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    events = InMemoryEventSink()
    result = engine(
        spec, ScriptedSpecialistClient(fast_success_script()), events=events
    ).run(spec)
    assert result.status is CompletionStatus.CHANGE_COMPLETE
    assert result.depth is WorkflowDepth.FAST
    assert result.gate2 is not None and result.gate2.value == "PASSED"
    assert result.gate3 is None
    assert events.events[-1].event_type == "TASK_COMPLETED"


def test_successful_full_workflow(tmp_path: Path) -> None:
    spec = task_spec(tmp_path, full=True)
    result = engine(spec, ScriptedSpecialistClient(full_success_script())).run(spec)
    assert result.status is CompletionStatus.CHANGE_COMPLETE
    assert result.depth is WorkflowDepth.FULL
    assert result.gate1 is not None and result.gate1.value == "APPROVED"
    assert result.gate2 is not None and result.gate2.value == "PASSED"
    assert result.gate3 is not None and result.gate3.value == "APPROVED"


def test_plan_critic_rejection_causes_bounded_plan_revision(tmp_path: Path) -> None:
    spec = task_spec(tmp_path, full=True)
    script = [
        response(SpecialistRole.PLANNER, plan()),
        response(SpecialistRole.PLAN_CRITIC, critique("CHANGES_REQUESTED")),
        response(SpecialistRole.PLANNER, plan()),
        response(SpecialistRole.PLAN_CRITIC, approved_critique(2)),
        response(
            SpecialistRole.IMPLEMENTER,
            implementation(depth="FULL", plan_reference="PLAN-2"),
        ),
        response(
            SpecialistRole.VERIFIER,
            verification(depth="FULL", plan_reference="PLAN-2"),
        ),
        response(SpecialistRole.REVIEWER, review(plan_version=2)),
    ]
    result = engine(spec, ScriptedSpecialistClient(script)).run(spec)
    assert result.status is CompletionStatus.CHANGE_COMPLETE
    assert result.plan_version.value == 2


def test_failed_required_command_drives_implementation_revision(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    script = [
        response(SpecialistRole.IMPLEMENTER, implementation()),
        response(SpecialistRole.IMPLEMENTER, implementation(iteration=2)),
        response(
            SpecialistRole.VERIFIER,
            verification(implementation_iteration=2),
        ),
    ]
    runner = Runner([RunnerResult(1, stderr="failed"), RunnerResult(0, "passed")])
    result = engine(spec, ScriptedSpecialistClient(script), runner=runner).run(spec)
    assert result.status is CompletionStatus.CHANGE_COMPLETE
    assert result.implementation_iteration.value == 2


def test_verifier_failure_drives_full_repair_and_reverification(tmp_path: Path) -> None:
    spec = task_spec(tmp_path, full=True)
    script = full_success_script()[:3] + [
        response(SpecialistRole.VERIFIER, verification(depth="FULL", verdict="FAILED")),
        response(
            SpecialistRole.IMPLEMENTER,
            implementation(depth="FULL", iteration=2),
        ),
        response(
            SpecialistRole.VERIFIER,
            verification(depth="FULL", implementation_iteration=2),
        ),
        response(SpecialistRole.REVIEWER, review(implementation_iteration=2)),
    ]
    result = engine(
        spec,
        ScriptedSpecialistClient(script),
        runner=Runner([RunnerResult(0), RunnerResult(0)]),
    ).run(spec)
    assert result.status is CompletionStatus.CHANGE_COMPLETE
    assert result.implementation_iteration.value == 2


def test_fast_verifier_failure_explicitly_escalates_into_full_flow(
    tmp_path: Path,
) -> None:
    spec = task_spec(tmp_path)
    events = InMemoryEventSink()
    script = [
        response(SpecialistRole.IMPLEMENTER, implementation()),
        response(SpecialistRole.VERIFIER, verification(verdict="FAILED")),
        response(SpecialistRole.PLANNER, plan()),
        response(SpecialistRole.PLAN_CRITIC, approved_critique()),
        response(
            SpecialistRole.IMPLEMENTER,
            implementation(depth="FULL", iteration=2),
        ),
        response(
            SpecialistRole.VERIFIER,
            verification(depth="FULL", implementation_iteration=2),
        ),
        response(SpecialistRole.REVIEWER, review(implementation_iteration=2)),
    ]
    result = engine(
        spec,
        ScriptedSpecialistClient(script),
        runner=Runner([RunnerResult(0), RunnerResult(0)]),
        events=events,
    ).run(spec)
    assert result.status is CompletionStatus.CHANGE_COMPLETE
    assert result.depth is WorkflowDepth.FULL
    assert any(event.event_type == "FAST_ESCALATED_TO_FULL" for event in events.events)


def test_plan_human_intent_finding_escalates_without_guessing(tmp_path: Path) -> None:
    spec = task_spec(tmp_path, full=True)
    script = [
        response(SpecialistRole.PLANNER, plan()),
        response(
            SpecialistRole.PLAN_CRITIC,
            critique("CHANGES_REQUESTED", human=True),
        ),
    ]
    result = engine(spec, ScriptedSpecialistClient(script)).run(spec)
    assert result.status is CompletionStatus.ESCALATED
    assert result.escalation is not None
    assert result.escalation.resolution_class is not None
    assert result.escalation.resolution_class.value == "HUMAN_INTENT_REQUIRED"


def test_verifier_malformed_once_gets_schema_only_repair(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    script = [
        response(SpecialistRole.IMPLEMENTER, implementation()),
        response(SpecialistRole.VERIFIER, "VERIFICATION\nnot json"),
        response(SpecialistRole.VERIFIER, verification()),
    ]
    client = ScriptedSpecialistClient(script)
    result = engine(spec, client).run(spec)
    assert result.status is CompletionStatus.CHANGE_COMPLETE
    repair_request = client.requests[-1]
    assert "schema_repair" in repair_request.prompt


def test_verifier_malformed_twice_fails_closed(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    script = [
        response(SpecialistRole.IMPLEMENTER, implementation()),
        response(SpecialistRole.VERIFIER, "bad"),
        response(SpecialistRole.VERIFIER, "still bad"),
    ]
    result = engine(spec, ScriptedSpecialistClient(script)).run(spec)
    assert result.status is CompletionStatus.ESCALATED
    assert result.escalation is not None
    assert result.escalation.failure_kind is FailureKind.MALFORMED_ARTIFACT


def test_fingerprint_drift_blocks_schema_repair_without_consuming_second_call(
    tmp_path: Path,
) -> None:
    spec = task_spec(tmp_path)
    delegate = ScriptedSpecialistClient(
        [
            response(SpecialistRole.IMPLEMENTER, implementation()),
            response(SpecialistRole.VERIFIER, "malformed"),
        ]
    )
    result = engine(spec, MutatingClient(delegate, tmp_path / "product.py")).run(spec)
    assert result.escalation is not None
    assert result.escalation.code == "FINGERPRINT_DRIFT_BEFORE_SCHEMA_REPAIR"
    assert [request.invocation.role for request in delegate.requests].count(
        SpecialistRole.VERIFIER
    ) == 1


def test_reviewer_change_request_reenters_implementation(tmp_path: Path) -> None:
    spec = task_spec(tmp_path, full=True)
    script = full_success_script()[:-1] + [
        response(SpecialistRole.REVIEWER, review(verdict="CHANGES_REQUESTED")),
        response(
            SpecialistRole.IMPLEMENTER,
            implementation(depth="FULL", iteration=2),
        ),
        response(
            SpecialistRole.VERIFIER,
            verification(depth="FULL", implementation_iteration=2),
        ),
        response(SpecialistRole.REVIEWER, review(implementation_iteration=2)),
    ]
    result = engine(
        spec,
        ScriptedSpecialistClient(script),
        runner=Runner([RunnerResult(0), RunnerResult(0)]),
    ).run(spec)
    assert result.status is CompletionStatus.CHANGE_COMPLETE
    assert result.implementation_iteration.value == 2


def test_implementation_revision_budget_exhaustion(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    script = [
        response(SpecialistRole.IMPLEMENTER, implementation(iteration=iteration))
        for iteration in (1, 2, 3)
    ]
    result = engine(
        spec,
        ScriptedSpecialistClient(script),
        runner=Runner([RunnerResult(1), RunnerResult(1), RunnerResult(1)]),
    ).run(spec)
    assert result.status is CompletionStatus.ESCALATED
    assert result.escalation is not None
    assert result.escalation.failure_kind is FailureKind.BUDGET_EXHAUSTED


def test_provider_invocation_failure_retries_once(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    script = [
        ScriptedResponse(
            SpecialistRole.IMPLEMENTER,
            failure_kind=FailureKind.INVOCATION_FAILED,
        ),
        *fast_success_script(),
    ]
    result = engine(spec, ScriptedSpecialistClient(script)).run(spec)
    assert result.status is CompletionStatus.CHANGE_COMPLETE


def test_second_provider_invocation_failure_escalates(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    failures = [
        ScriptedResponse(
            SpecialistRole.IMPLEMENTER,
            failure_kind=FailureKind.INVOCATION_FAILED,
        )
        for _ in range(2)
    ]
    result = engine(spec, ScriptedSpecialistClient(failures)).run(spec)
    assert result.status is CompletionStatus.ESCALATED
    assert result.escalation is not None
    assert result.escalation.failure_kind is FailureKind.INVOCATION_FAILED


def test_tool_capability_failure_is_detected_before_invocation(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    client = ScriptedSpecialistClient(
        [],
        capabilities=ProviderCapabilities(False, False, False, False, False),
    )
    result = engine(spec, client).run(spec)
    assert result.escalation is not None
    assert result.escalation.failure_kind is FailureKind.TOOL_CAPABILITY_FAILURE
    assert not client.requests


def test_environment_command_failure_is_not_a_product_defect(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    result = engine(
        spec,
        ScriptedSpecialistClient(
            [response(SpecialistRole.IMPLEMENTER, implementation())]
        ),
        runner=Runner([RunnerResult(None, environment_error="pytest missing")]),
    ).run(spec)
    assert result.escalation is not None
    assert result.escalation.failure_kind is FailureKind.ENVIRONMENT_TOOLING_FAILURE


def test_human_command_authorization_denied(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    result = engine(
        spec,
        ScriptedSpecialistClient(
            [response(SpecialistRole.IMPLEMENTER, implementation())]
        ),
        authorized=False,
    ).run(spec)
    assert result.escalation is not None
    assert result.escalation.failure_kind is FailureKind.AUTHORIZATION_DENIED


def test_required_authorization_pauses_and_authorized_resume_continues(
    tmp_path: Path,
) -> None:
    spec = task_spec(tmp_path)
    store = InMemoryWorkflowStore()
    client = ScriptedSpecialistClient(fast_success_script())
    waiting = engine(
        spec,
        client,
        store=store,
        authorization_status=AuthorizationStatus.REQUIRED,
    ).run(spec)
    assert waiting.status is CompletionStatus.WAITING_AUTHORIZATION
    assert waiting.state is WorkflowState.WAITING_AUTHORIZATION

    completed = engine(spec, client, store=store).resume(spec)
    assert completed.status is CompletionStatus.CHANGE_COMPLETE
    snapshot = store.load(spec.task_id)
    assert snapshot is not None
    assert len(snapshot.events) == snapshot.event_count
    assert [event.sequence for event in snapshot.events] == list(
        range(1, snapshot.event_count + 1)
    )


def test_resumed_drifted_content_refuses_command_execution(tmp_path: Path) -> None:
    """Regression: after WAITING_AUTHORIZATION, content drift still executed the
    commands and recorded canonical evidence bound to the stale fingerprint."""
    spec = task_spec(tmp_path)
    store = InMemoryWorkflowStore()
    client = ScriptedSpecialistClient(fast_success_script())
    waiting = engine(
        spec,
        client,
        store=store,
        authorization_status=AuthorizationStatus.REQUIRED,
    ).run(spec)
    assert waiting.status is CompletionStatus.WAITING_AUTHORIZATION

    (tmp_path / "product.py").write_text("edited while waiting", encoding="utf-8")
    runner = CountingRunner()
    result = engine(spec, client, runner=runner, store=store).resume(spec)
    assert result.status is CompletionStatus.ESCALATED
    assert result.escalation is not None
    assert result.escalation.failure_kind is FailureKind.FINGERPRINT_DRIFT
    assert result.escalation.code == "FINGERPRINT_DRIFT_BEFORE_COMMANDS"
    assert runner.calls == 0


def test_actual_out_of_scope_change_is_included_then_rejected(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    result = engine(
        spec,
        ScriptedSpecialistClient(
            [response(SpecialistRole.IMPLEMENTER, implementation())]
        ),
        scope_detector=OutOfScopeDetector(tmp_path / "outside.py"),
    ).run(spec)
    assert result.escalation is not None
    assert result.escalation.failure_kind is FailureKind.SCOPE_VIOLATION
    assert result.fingerprint is not None
    assert "outside.py" in result.fingerprint.scope


def test_fingerprint_drift_before_verifier_invalidates_evidence(tmp_path: Path) -> None:
    spec = task_spec(tmp_path)
    events = InMemoryEventSink()
    result = engine(
        spec,
        ScriptedSpecialistClient(fast_success_script()),
        runner=Runner(mutate=tmp_path / "product.py"),
        events=events,
    ).run(spec)
    assert result.escalation is not None
    assert result.escalation.failure_kind is FailureKind.FINGERPRINT_DRIFT
    assert any(event.event_type == "EVIDENCE_INVALIDATED" for event in events.events)


def test_fingerprint_drift_before_reviewer_invalidates_gate2(tmp_path: Path) -> None:
    spec = task_spec(tmp_path, full=True)
    delegate = ScriptedSpecialistClient(full_success_script())
    result = engine(spec, MutatingClient(delegate, tmp_path / "product.py")).run(spec)
    assert result.escalation is not None
    assert result.escalation.code == "FINGERPRINT_DRIFT_BEFORE_REVIEWER"


def test_interrupted_command_phase_resumes_without_replaying_implementer(
    tmp_path: Path,
) -> None:
    spec = task_spec(tmp_path)
    store = InMemoryWorkflowStore()
    client = ScriptedSpecialistClient(fast_success_script())
    with pytest.raises(RuntimeError, match="interruption"):
        engine(spec, client, runner=CrashRunner(), store=store).run(spec)
    checkpoint = store.load(spec.task_id)
    assert checkpoint is not None
    assert checkpoint.state is WorkflowState.COMMAND_VERIFICATION

    result = engine(spec, client, store=store).resume(spec)
    assert result.status is CompletionStatus.CHANGE_COMPLETE
    assert [request.invocation.role for request in client.requests].count(
        SpecialistRole.IMPLEMENTER
    ) == 1
