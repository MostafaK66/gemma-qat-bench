"""Deterministic V3 orchestration application engine."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, cast

from .artifacts import (
    EvidenceAssessment,
    ImplementationArtifact,
    ImplementationDisposition,
    PlanArtifact,
    PlanCritiqueArtifact,
    ReviewArtifact,
    SpecialistArtifact,
    VerificationArtifact,
    validate_artifact,
)
from .commands import CommandBroker
from .domain import (
    ArtifactDefect,
    ArtifactValidationResult,
    CommandStatus,
    CompletionResult,
    DomainError,
    EscalationReason,
    FailureKind,
    Gate1Verdict,
    Gate2Verdict,
    Gate3Verdict,
    PlanVersion,
    ResolutionClass,
    SpecialistInvocation,
    SpecialistRole,
    TaskSpec,
    TransportStatus,
    VerificationIteration,
    WorkflowDepth,
    WorkflowState,
)
from .events import EventRecorder, EventSink, InMemoryEventSink
from .evidence import EvidenceBinding, EvidenceLedger
from .fingerprint import FingerprintService
from .persistence import (
    InMemoryWorkflowStore,
    StoredEvent,
    WorkflowSnapshot,
    WorkflowStore,
)
from .routing import RoutingPolicy
from .runtime import CheckpointManager
from .runtime import RuntimeState as _Runtime
from .scope import (
    GitWorkspaceChangeDetector,
    WorkspaceChangeDetector,
    changed_since,
)
from .specialists import (
    ROLE_TO_ARTIFACT,
    SpecialistClient,
    build_specialist_request,
)
from .state_machine import WorkflowMachine


class Orchestrator:
    """Own state, routing, evidence, budgets, retries, and all Gate transitions."""

    def __init__(
        self,
        specialists: SpecialistClient,
        command_broker: CommandBroker,
        fingerprint_service: FingerprintService,
        *,
        routing: RoutingPolicy | None = None,
        store: WorkflowStore | None = None,
        events: EventSink | None = None,
        scope_detector: WorkspaceChangeDetector | None = None,
    ) -> None:
        self._specialists = specialists
        self._commands = command_broker
        self._fingerprints = fingerprint_service
        self._routing = routing or RoutingPolicy()
        self._checkpoints = CheckpointManager(store or InMemoryWorkflowStore())
        self._events = events or InMemoryEventSink()
        self._scope_detector = scope_detector
        self._recorder: EventRecorder | None = None

    def run(self, spec: TaskSpec) -> CompletionResult:
        """Start a new workflow and drive it to a deterministic terminal state."""
        if self._checkpoints.load(spec.task_id) is not None:
            raise DomainError(
                f"workflow {spec.task_id} already exists; use resume() or a new task ID"
            )
        decision = self._routing.decide(spec)
        runtime = _Runtime(spec, WorkflowMachine(decision.native_depth))
        self._recorder = EventRecorder(spec.task_id, self._events)
        self._event(runtime, "TASK_STARTED", risk=spec.risk.value)
        self._event(
            runtime,
            "ROUTE_SELECTED",
            depth=decision.native_depth.value,
            reason=decision.reason,
            policy_version=decision.policy_version,
        )
        if not self._capture_scope_baseline(runtime):
            return self._result(runtime)
        self._persist(runtime)
        if not self._provider_boundary_available(runtime):
            return self._result(runtime)
        runtime.machine.transition(
            WorkflowState.IMPLEMENTATION
            if runtime.machine.depth is WorkflowDepth.FAST
            else WorkflowState.PLANNING
        )
        self._state_changed(runtime)
        return self._drive(runtime)

    def resume(self, spec: TaskSpec) -> CompletionResult:
        """Resume from the last atomic checkpoint without replaying ambiguous writes."""
        snapshot = self._checkpoints.load(spec.task_id)
        if snapshot is None:
            raise DomainError(f"workflow {spec.task_id} does not exist")
        runtime = self._checkpoints.restore(spec, snapshot)
        self._recorder = EventRecorder(
            spec.task_id, self._events, initial_sequence=snapshot.event_count
        )
        runtime.resumed = True
        self._event(runtime, "WORKFLOW_RESUMED", state=runtime.machine.state.value)
        self._persist(runtime)
        if runtime.machine.state in {
            WorkflowState.COMPLETE,
            WorkflowState.ESCALATED,
            WorkflowState.FAILED,
        }:
            return self._result(runtime)
        if runtime.machine.state is WorkflowState.WAITING_AUTHORIZATION:
            runtime.machine.transition(WorkflowState.COMMAND_VERIFICATION)
            self._state_changed(runtime)
        if not self._provider_boundary_available(runtime):
            return self._result(runtime)
        return self._drive(runtime)

    def inspect(self, task_id: Any) -> WorkflowSnapshot | None:
        """Read a persisted workflow without invoking providers or commands."""
        return self._checkpoints.load(task_id)

    def _drive(self, runtime: _Runtime) -> CompletionResult:
        while runtime.machine.state not in {
            WorkflowState.COMPLETE,
            WorkflowState.WAITING_AUTHORIZATION,
            WorkflowState.ESCALATED,
            WorkflowState.FAILED,
        }:
            state = runtime.machine.state
            if state is WorkflowState.PLANNING:
                self._step_planning(runtime)
            elif state is WorkflowState.PLAN_CRITIQUE:
                self._step_plan_critique(runtime)
            elif state is WorkflowState.IMPLEMENTATION:
                self._step_implementation(runtime)
            elif state is WorkflowState.COMMAND_VERIFICATION:
                self._step_commands(runtime)
            elif state is WorkflowState.GATE_2:
                self._step_verification(runtime)
            elif state is WorkflowState.REVIEW:
                self._step_review(runtime)
            else:
                self._escalate(
                    runtime,
                    FailureKind.AGENT_LOOP_TIMEOUT_OR_LIMIT,
                    "UNHANDLED_STATE",
                    f"no deterministic driver for state {state.value}",
                )
        return self._result(runtime)

    def _step_planning(self, runtime: _Runtime) -> None:
        plan = self._latest(runtime, PlanArtifact)
        context: dict[str, Any] = {
            "task_id": str(runtime.spec.task_id),
            "description": runtime.spec.description,
            "acceptance_criteria": runtime.spec.acceptance_criteria,
            "plan_version": runtime.plan_version.value,
        }
        prior_critique = self._latest(runtime, PlanCritiqueArtifact)
        if prior_critique is not None:
            context["required_corrections"] = [
                finding.required_correction
                for finding in prior_critique.blocking_findings
            ]
        if plan is not None and prior_critique is None and runtime.resumed:
            runtime.machine.transition(WorkflowState.PLAN_CRITIQUE)
            self._state_changed(runtime)
            return
        artifact = self._invoke(runtime, SpecialistRole.PLANNER, context)
        if artifact is None:
            return
        if (
            not isinstance(artifact, PlanArtifact)
            or artifact.task_id != runtime.spec.task_id
        ):
            self._malformed_binding(runtime, SpecialistRole.PLANNER)
            return
        runtime.machine.transition(WorkflowState.PLAN_CRITIQUE)
        self._state_changed(runtime)

    def _step_plan_critique(self, runtime: _Runtime) -> None:
        plan = self._latest(runtime, PlanArtifact)
        if plan is None:
            self._escalate(
                runtime,
                FailureKind.MALFORMED_ARTIFACT,
                "MISSING_PLAN",
                "Plan Critic cannot run without a valid current plan",
            )
            return
        critique = self._invoke(
            runtime,
            SpecialistRole.PLAN_CRITIC,
            {
                "task_id": str(runtime.spec.task_id),
                "plan_version": runtime.plan_version.value,
                "plan": asdict(plan),
            },
        )
        if critique is None:
            return
        if (
            not isinstance(critique, PlanCritiqueArtifact)
            or critique.task_id != runtime.spec.task_id
            or critique.plan_version != runtime.plan_version.value
        ):
            self._malformed_binding(runtime, SpecialistRole.PLAN_CRITIC)
            return
        runtime.machine.transition(WorkflowState.GATE_1)
        self._state_changed(runtime)
        runtime.gate1 = critique.verdict
        self._event(runtime, "GATE_REACHED", gate="GATE_1")
        self._event(
            runtime, "GATE_DECIDED", gate="GATE_1", verdict=critique.verdict.value
        )
        if critique.verdict is Gate1Verdict.APPROVED:
            if critique.blocking_findings:
                self._malformed_binding(runtime, SpecialistRole.PLAN_CRITIC)
                return
            runtime.machine.transition(WorkflowState.IMPLEMENTATION)
            self._state_changed(runtime)
            return
        if not critique.blocking_findings:
            self._malformed_binding(runtime, SpecialistRole.PLAN_CRITIC)
            return
        if any(
            finding.classification is ResolutionClass.HUMAN_INTENT_REQUIRED
            for finding in critique.blocking_findings
        ):
            self._escalate(
                runtime,
                FailureKind.MALFORMED_ARTIFACT,
                "HUMAN_INTENT_REQUIRED",
                "Gate 1 requires an explicit human product decision",
                ResolutionClass.HUMAN_INTENT_REQUIRED,
            )
            return
        if not self._consume(runtime, "plan_revision"):
            return
        runtime.plan_version = runtime.plan_version.next()
        runtime.machine.transition(WorkflowState.PLANNING)
        self._event(
            runtime,
            "REVISION_REQUESTED",
            target="PLAN",
            plan_version=runtime.plan_version.value,
        )
        self._state_changed(runtime)

    def _step_implementation(self, runtime: _Runtime) -> None:
        existing = self._latest(runtime, ImplementationArtifact)
        if (
            existing is not None
            and existing.iteration == runtime.implementation_iteration.value
        ):
            self._finish_implementation(runtime, existing)
            return
        if (
            runtime.resumed
            and runtime.fingerprint is not None
            and not self._fingerprint_is_current(runtime)
        ):
            self._escalate(
                runtime,
                FailureKind.FINGERPRINT_DRIFT,
                "AMBIGUOUS_INTERRUPTED_IMPLEMENTATION",
                "workspace changed during an interrupted Implementer invocation",
                ResolutionClass.HUMAN_INTENT_REQUIRED,
            )
            return
        try:
            current_scope = self._current_scope(runtime)
            runtime.fingerprint = self._fingerprints.capture(current_scope)
        except DomainError as exc:
            self._escalate(
                runtime,
                FailureKind.ENVIRONMENT_TOOLING_FAILURE,
                "FINGERPRINT_CAPTURE_FAILED",
                str(exc),
            )
            return
        actual_delta = set(current_scope) - set(runtime.spec.fingerprint_scope)
        if actual_delta:
            self._event(
                runtime,
                "SCOPE_VIOLATION_DETECTED",
                paths=sorted(actual_delta),
            )
            self._escalate(
                runtime,
                FailureKind.SCOPE_VIOLATION,
                "ACTUAL_SCOPE_VIOLATION",
                "workspace content changed outside the authorized task scope",
            )
            return
        self._persist(runtime)
        plan = self._latest(runtime, PlanArtifact)
        prior_verification = self._latest(runtime, VerificationArtifact)
        prior_review = self._latest(runtime, ReviewArtifact)
        context: dict[str, Any] = {
            "task_id": str(runtime.spec.task_id),
            "depth": runtime.machine.depth.value,
            "plan_reference": self._plan_reference(runtime),
            "implementation_iteration": runtime.implementation_iteration.value,
            "description": runtime.spec.description,
            "acceptance_criteria": runtime.spec.acceptance_criteria,
            "authorized_file_scope": runtime.spec.fingerprint_scope,
            "approved_plan": None if plan is None else asdict(plan),
        }
        if prior_verification is not None:
            context["verification_repair_findings"] = [
                asdict(finding) for finding in prior_verification.blocking_findings
            ]
        if prior_review is not None:
            context["review_repair_findings"] = [
                asdict(finding) for finding in prior_review.blocking_findings
            ]
        artifact = self._invoke(runtime, SpecialistRole.IMPLEMENTER, context)
        if artifact is None:
            return
        if not isinstance(artifact, ImplementationArtifact):
            self._malformed_binding(runtime, SpecialistRole.IMPLEMENTER)
            return
        self._finish_implementation(runtime, artifact)

    def _finish_implementation(
        self, runtime: _Runtime, implementation: ImplementationArtifact
    ) -> None:
        if (
            implementation.task_id != runtime.spec.task_id
            or implementation.depth is not runtime.machine.depth
            or implementation.plan_reference != self._plan_reference(runtime)
            or implementation.iteration != runtime.implementation_iteration.value
        ):
            self._malformed_binding(runtime, SpecialistRole.IMPLEMENTER)
            return
        if implementation.disposition is not ImplementationDisposition.COMPLETED:
            resolution = (
                ResolutionClass.HUMAN_INTENT_REQUIRED
                if implementation.disposition
                is ImplementationDisposition.HUMAN_INTENT_REQUIRED
                else None
            )
            kind = (
                FailureKind.TOOL_CAPABILITY_FAILURE
                if implementation.disposition is ImplementationDisposition.BLOCKED
                else FailureKind.MALFORMED_ARTIFACT
            )
            self._escalate(
                runtime,
                kind,
                implementation.disposition.value,
                "Implementer could not complete the authorized scope",
                resolution,
            )
            return
        if implementation.blockers:
            self._malformed_binding(runtime, SpecialistRole.IMPLEMENTER)
            return
        declared = set(implementation.files_changed)
        authorized = set(runtime.spec.fingerprint_scope)
        if not declared.issubset(authorized):
            self._escalate(
                runtime,
                FailureKind.SCOPE_VIOLATION,
                "DECLARED_SCOPE_VIOLATION",
                "Implementer declared files outside the authorized fingerprint scope",
            )
            return
        try:
            actual_delta = set(self._actual_delta(runtime))
            current_scope = tuple(sorted(authorized | actual_delta))
            runtime.fingerprint = self._fingerprints.capture(current_scope)
        except DomainError as exc:
            self._escalate(
                runtime,
                FailureKind.ENVIRONMENT_TOOLING_FAILURE,
                "FINGERPRINT_CAPTURE_FAILED",
                str(exc),
            )
            return
        undeclared_delta = actual_delta - declared
        if undeclared_delta:
            self._event(
                runtime,
                "SCOPE_VIOLATION_DETECTED",
                paths=sorted(undeclared_delta),
            )
            self._escalate(
                runtime,
                FailureKind.SCOPE_VIOLATION,
                "UNDECLARED_ACTUAL_CHANGE",
                "actual workspace changes were omitted from the Implementer artifact",
            )
            return
        unauthorized_delta = actual_delta - authorized
        if unauthorized_delta:
            self._event(
                runtime,
                "SCOPE_VIOLATION_DETECTED",
                paths=sorted(unauthorized_delta),
            )
            self._escalate(
                runtime,
                FailureKind.SCOPE_VIOLATION,
                "ACTUAL_SCOPE_VIOLATION",
                "workspace content changed outside the authorized task scope",
            )
            return
        self._event(
            runtime,
            "IMPLEMENTATION_FINGERPRINT_CAPTURED",
            digest=runtime.fingerprint.digest,
            scope_count=len(runtime.fingerprint.scope),
        )
        runtime.machine.transition(WorkflowState.COMMAND_VERIFICATION)
        runtime.resumed = False
        self._state_changed(runtime)

    def _step_commands(self, runtime: _Runtime) -> None:
        if runtime.fingerprint is None:
            self._escalate(
                runtime,
                FailureKind.FINGERPRINT_DRIFT,
                "MISSING_FINGERPRINT",
                "verification commands require a bound implementation fingerprint",
            )
            return
        if not self._fingerprint_is_current(runtime):
            if runtime.ledger is not None:
                runtime.ledger.invalidate()
                runtime.ledger = None
                self._event(
                    runtime,
                    "EVIDENCE_INVALIDATED",
                    reason="fingerprint drift before commands",
                )
            self._escalate(
                runtime,
                FailureKind.FINGERPRINT_DRIFT,
                "FINGERPRINT_DRIFT_BEFORE_COMMANDS",
                "implementation content changed before verification commands ran",
            )
            return
        command_ids = tuple(
            str(item.command_id) for item in runtime.spec.required_commands
        )
        binding = EvidenceBinding(
            runtime.spec.task_id,
            self._plan_reference(runtime),
            runtime.implementation_iteration.value,
            runtime.verification_iteration.value,
            "task_spec.required_commands",
            runtime.fingerprint.digest,
        )
        ledger = EvidenceLedger(binding, command_ids)
        records = self._commands.execute(
            runtime.spec.required_commands, fingerprint=runtime.fingerprint.digest
        )
        for record in records:
            ledger.record(record)
        runtime.ledger = ledger
        self._event(
            runtime,
            "COMMAND_SET_FINISHED",
            command_count=len(records),
            successful=sum(
                record.status is CommandStatus.SUCCEEDED for record in records
            ),
        )
        self._persist(runtime)
        if ledger.authorization_required:
            runtime.machine.transition(WorkflowState.WAITING_AUTHORIZATION)
            self._event(runtime, "AUTHORIZATION_REQUIRED", action="COMMAND_EXECUTION")
            self._state_changed(runtime)
            return
        if ledger.authorization_denied:
            self._event(runtime, "AUTHORIZATION_DENIED", action="COMMAND_EXECUTION")
            self._escalate(
                runtime,
                FailureKind.AUTHORIZATION_DENIED,
                "COMMAND_AUTHORIZATION_DENIED",
                "a required verification command was not authorized",
                ResolutionClass.HUMAN_INTENT_REQUIRED,
            )
            return
        if ledger.environment_failed:
            self._escalate(
                runtime,
                FailureKind.ENVIRONMENT_TOOLING_FAILURE,
                "COMMAND_ENVIRONMENT_FAILURE",
                "a required command could not be executed by the environment",
            )
            return
        if ledger.required_failed:
            self._event(
                runtime,
                "REVISION_REQUESTED",
                target="IMPLEMENTATION",
                reason="required command failed",
            )
            self._implementation_revision(runtime)
            return
        runtime.machine.transition(WorkflowState.GATE_2)
        self._state_changed(runtime)

    def _step_verification(self, runtime: _Runtime) -> None:
        if runtime.fingerprint is None or runtime.ledger is None:
            self._escalate(
                runtime,
                FailureKind.QUALITY_GATE_FAILURE,
                "MISSING_CANONICAL_EVIDENCE",
                "Gate 2 requires a fingerprint-bound complete evidence ledger",
            )
            return
        if not self._fingerprint_is_current(runtime):
            runtime.ledger.invalidate()
            self._event(runtime, "EVIDENCE_INVALIDATED", reason="fingerprint drift")
            self._escalate(
                runtime,
                FailureKind.FINGERPRINT_DRIFT,
                "FINGERPRINT_DRIFT_BEFORE_VERIFIER",
                "implementation content changed after command evidence was captured",
            )
            return
        command_ids = tuple(
            str(item.command_id) for item in runtime.spec.required_commands
        )
        verification = self._invoke(
            runtime,
            SpecialistRole.VERIFIER,
            {
                "task_id": str(runtime.spec.task_id),
                "depth": runtime.machine.depth.value,
                "plan_reference": self._plan_reference(runtime),
                "implementation_iteration": runtime.implementation_iteration.value,
                "verification_iteration": runtime.verification_iteration.value,
                "acceptance_criteria": runtime.spec.acceptance_criteria,
                "implementation_fingerprint": runtime.fingerprint.digest,
                "evidence": [asdict(item) for item in runtime.ledger.verifier_view()],
            },
            expected_command_ids=command_ids,
        )
        if verification is None:
            return
        if (
            not isinstance(verification, VerificationArtifact)
            or verification.task_id != runtime.spec.task_id
            or verification.depth is not runtime.machine.depth
            or verification.plan_reference != self._plan_reference(runtime)
            or verification.implementation_iteration
            != runtime.implementation_iteration.value
            or verification.verification_iteration != runtime.verification_iteration.value
        ):
            self._malformed_binding(runtime, SpecialistRole.VERIFIER)
            return
        runtime.gate2 = verification.verdict
        self._event(runtime, "GATE_REACHED", gate="GATE_2")
        self._event(
            runtime, "GATE_DECIDED", gate="GATE_2", verdict=verification.verdict.value
        )
        if verification.verdict is Gate2Verdict.PASSED:
            if not self._verification_pass_is_consistent(verification):
                self._malformed_binding(runtime, SpecialistRole.VERIFIER)
                return
            if runtime.machine.depth is WorkflowDepth.FAST:
                runtime.machine.transition(WorkflowState.COMPLETE)
                self._complete(runtime)
            else:
                runtime.machine.transition(WorkflowState.REVIEW)
                self._state_changed(runtime)
            return
        if not verification.blocking_findings:
            self._malformed_binding(runtime, SpecialistRole.VERIFIER)
            return
        if any(
            finding.resolution_class is ResolutionClass.HUMAN_INTENT_REQUIRED
            for finding in verification.blocking_findings
        ):
            self._escalate(
                runtime,
                FailureKind.QUALITY_GATE_FAILURE,
                "GATE_2_HUMAN_INTENT_REQUIRED",
                "Verifier found a blocking product decision",
                ResolutionClass.HUMAN_INTENT_REQUIRED,
            )
            return
        if runtime.machine.depth is WorkflowDepth.FAST:
            runtime.machine.escalate_fast_to_full()
            runtime.plan_version = PlanVersion()
            runtime.implementation_iteration = runtime.implementation_iteration.next()
            runtime.verification_iteration = VerificationIteration()
            runtime.gate1 = None
            runtime.gate2 = None
            runtime.gate3 = None
            runtime.ledger = None
            self._event(
                runtime,
                "FAST_ESCALATED_TO_FULL",
                reason="independent verification rejected FAST implementation",
            )
            self._state_changed(runtime)
            return
        self._implementation_revision(runtime)

    def _step_review(self, runtime: _Runtime) -> None:
        if runtime.fingerprint is None or runtime.ledger is None:
            self._escalate(
                runtime,
                FailureKind.QUALITY_GATE_FAILURE,
                "MISSING_REVIEW_EVIDENCE",
                "Gate 3 requires current Gate 2 evidence",
            )
            return
        if not self._fingerprint_is_current(runtime):
            runtime.ledger.invalidate()
            self._event(runtime, "EVIDENCE_INVALIDATED", reason="fingerprint drift")
            self._escalate(
                runtime,
                FailureKind.FINGERPRINT_DRIFT,
                "FINGERPRINT_DRIFT_BEFORE_REVIEWER",
                "implementation content changed after Gate 2",
            )
            return
        implementation = self._latest(runtime, ImplementationArtifact)
        verification = self._latest(runtime, VerificationArtifact)
        review = self._invoke(
            runtime,
            SpecialistRole.REVIEWER,
            {
                "task_id": str(runtime.spec.task_id),
                "plan_version": runtime.plan_version.value,
                "implementation_iteration": runtime.implementation_iteration.value,
                "implementation": None
                if implementation is None
                else asdict(implementation),
                "verification": None if verification is None else asdict(verification),
                "fingerprint": runtime.fingerprint.digest,
            },
        )
        if review is None:
            return
        if (
            not isinstance(review, ReviewArtifact)
            or review.task_id != runtime.spec.task_id
            or review.plan_version != runtime.plan_version.value
            or review.implementation_iteration != runtime.implementation_iteration.value
        ):
            self._malformed_binding(runtime, SpecialistRole.REVIEWER)
            return
        runtime.machine.transition(WorkflowState.GATE_3)
        self._state_changed(runtime)
        runtime.gate3 = review.verdict
        self._event(runtime, "GATE_REACHED", gate="GATE_3")
        self._event(runtime, "GATE_DECIDED", gate="GATE_3", verdict=review.verdict.value)
        if review.verdict is Gate3Verdict.APPROVED:
            if review.blocking_findings:
                self._malformed_binding(runtime, SpecialistRole.REVIEWER)
                return
            runtime.machine.transition(WorkflowState.COMPLETE)
            self._complete(runtime)
            return
        if not review.blocking_findings:
            self._malformed_binding(runtime, SpecialistRole.REVIEWER)
            return
        if any(
            finding.resolution_class is ResolutionClass.HUMAN_INTENT_REQUIRED
            for finding in review.blocking_findings
        ):
            self._escalate(
                runtime,
                FailureKind.QUALITY_GATE_FAILURE,
                "GATE_3_HUMAN_INTENT_REQUIRED",
                "Reviewer found a blocking product decision",
                ResolutionClass.HUMAN_INTENT_REQUIRED,
            )
            return
        if not self._consume(runtime, "reviewer_repair"):
            return
        self._implementation_revision(runtime)

    def _implementation_revision(self, runtime: _Runtime) -> None:
        if not self._consume(runtime, "implementation_revision"):
            return
        runtime.implementation_iteration = runtime.implementation_iteration.next()
        runtime.verification_iteration = VerificationIteration()
        runtime.ledger = None
        runtime.gate2 = None
        runtime.gate3 = None
        runtime.machine.transition(WorkflowState.IMPLEMENTATION)
        self._event(
            runtime,
            "REVISION_REQUESTED",
            target="IMPLEMENTATION",
            implementation_iteration=runtime.implementation_iteration.value,
        )
        self._state_changed(runtime)

    def _invoke(
        self,
        runtime: _Runtime,
        role: SpecialistRole,
        context: dict[str, Any],
        *,
        expected_command_ids: tuple[str, ...] = (),
    ) -> SpecialistArtifact | None:
        artifact_kind = ROLE_TO_ARTIFACT[role]
        schema_repair = False
        while True:
            runtime.invocation_count += 1
            invocation = SpecialistInvocation(
                f"{runtime.spec.task_id}-{role.value.lower()}-{runtime.invocation_count}",
                role,
                artifact_kind,
                1 + int(schema_repair),
            )
            request_context = dict(context)
            if schema_repair:
                last = runtime.validations[-1]
                request_context["schema_repair"] = {
                    "defect_codes": [defect.code for defect in last.defects],
                    "instruction": "repair structure only; do not change product files",
                }
            request = build_specialist_request(
                invocation=invocation,
                repository_root=runtime.spec.repository_root,
                context=request_context,
                expected_command_ids=expected_command_ids,
            )
            self._event(
                runtime,
                "SPECIALIST_INVOCATION_STARTED",
                role=role.value,
                invocation_id=invocation.invocation_id,
            )
            result = self._specialists.invoke(request)
            self._event(
                runtime,
                "SPECIALIST_INVOCATION_FINISHED",
                role=role.value,
                invocation_id=invocation.invocation_id,
                transport_status=result.status.value,
                usage=result.usage,
            )
            if result.status is TransportStatus.FAILED or result.raw_response is None:
                if runtime.budgets.invocation_retry.remaining:
                    if not self._consume(runtime, "invocation_retry"):
                        return None
                    self._event(runtime, "RETRY_CONSUMED", target="SPECIALIST_INVOCATION")
                    continue
                self._escalate(
                    runtime,
                    result.failure_kind or FailureKind.INVOCATION_FAILED,
                    "SPECIALIST_INVOCATION_FAILED",
                    result.error_message or "provider returned no response",
                )
                return None
            validation = validate_artifact(
                artifact_kind,
                result.raw_response,
                expected_command_ids=expected_command_ids,
            )
            runtime.validations.append(validation)
            self._persist(runtime)
            if validation.valid:
                if validation.artifact is None:
                    raise RuntimeError("valid artifact result has no artifact")
                payload = json.loads(result.raw_response)
                runtime.artifacts.append(
                    (
                        invocation.invocation_id,
                        cast(SpecialistArtifact, validation.artifact),
                        cast(dict[str, Any], payload),
                    )
                )
                self._persist(runtime)
                return cast(SpecialistArtifact, validation.artifact)
            self._event(
                runtime,
                "ARTIFACT_REJECTED",
                role=role.value,
                defect_codes=[defect.code for defect in validation.defects],
            )
            if role is SpecialistRole.VERIFIER and not schema_repair:
                if runtime.fingerprint is None or not self._fingerprint_is_current(
                    runtime
                ):
                    self._escalate(
                        runtime,
                        FailureKind.FINGERPRINT_DRIFT,
                        "FINGERPRINT_DRIFT_BEFORE_SCHEMA_REPAIR",
                        "schema repair cannot run against changed implementation content",
                    )
                    return None
                if self._consume(runtime, "verifier_schema_repair"):
                    schema_repair = True
                    self._event(runtime, "RETRY_CONSUMED", target="VERIFIER_SCHEMA")
                    continue
                return None
            self._escalate(
                runtime,
                FailureKind.MALFORMED_ARTIFACT,
                "MALFORMED_SPECIALIST_ARTIFACT",
                f"{role.value} returned an invalid {artifact_kind.value} artifact",
            )
            return None

    def _provider_boundary_available(self, runtime: _Runtime) -> bool:
        capabilities = self._specialists.capabilities
        if capabilities.structured_output or capabilities.raw_response_access:
            return True
        self._escalate(
            runtime,
            FailureKind.TOOL_CAPABILITY_FAILURE,
            "NO_VALIDATABLE_RESPONSE_BOUNDARY",
            "provider offers neither schema-bound output nor raw response access",
        )
        return False

    def _consume(self, runtime: _Runtime, budget_name: str) -> bool:
        try:
            budget = runtime.budgets.consume(budget_name)
        except DomainError:
            self._escalate(
                runtime,
                FailureKind.BUDGET_EXHAUSTED,
                "REVISION_BUDGET_EXHAUSTED",
                f"no retries remain for {budget_name}",
            )
            return False
        self._event(
            runtime,
            "RETRY_CONSUMED",
            budget=budget_name,
            consumed=budget.consumed,
            remaining=budget.remaining,
        )
        self._persist(runtime)
        return True

    def _malformed_binding(self, runtime: _Runtime, role: SpecialistRole) -> None:
        result = ArtifactValidationResult(
            ROLE_TO_ARTIFACT[role],
            False,
            None,
            (ArtifactDefect("STALE_OR_INCONSISTENT_BINDING", role.value),),
        )
        runtime.validations.append(result)
        self._event(
            runtime,
            "ARTIFACT_REJECTED",
            role=role.value,
            defect_codes=["STALE_OR_INCONSISTENT_BINDING"],
        )
        self._escalate(
            runtime,
            FailureKind.MALFORMED_ARTIFACT,
            "STALE_OR_INCONSISTENT_BINDING",
            f"{role.value} artifact does not match the current workflow binding",
        )

    def _verification_pass_is_consistent(self, artifact: VerificationArtifact) -> bool:
        return not artifact.blocking_findings and all(
            self._assessment_sufficient(assessment)
            for assessment in artifact.command_assessments
        )

    @staticmethod
    def _assessment_sufficient(assessment: EvidenceAssessment) -> bool:
        return assessment.evidence_quality.value == "sufficient"

    def _escalate(
        self,
        runtime: _Runtime,
        failure_kind: FailureKind,
        code: str,
        message: str,
        resolution_class: ResolutionClass | None = None,
    ) -> None:
        runtime.escalation = EscalationReason(
            failure_kind, code, message, resolution_class
        )
        if runtime.machine.state not in {
            WorkflowState.ESCALATED,
            WorkflowState.FAILED,
            WorkflowState.COMPLETE,
        }:
            runtime.machine.transition(WorkflowState.ESCALATED)
        self._event(
            runtime,
            "ESCALATED",
            failure_kind=failure_kind.value,
            code=code,
            resolution_class=None if resolution_class is None else resolution_class.value,
        )
        self._persist(runtime)

    def _complete(self, runtime: _Runtime) -> None:
        self._event(runtime, "TASK_COMPLETED", depth=runtime.machine.depth.value)
        self._persist(runtime)

    def _state_changed(self, runtime: _Runtime) -> None:
        self._event(runtime, "WORKFLOW_STATE_CHANGED", state=runtime.machine.state.value)
        self._persist(runtime)

    def _event(self, runtime: _Runtime, event_type: str, **attributes: Any) -> None:
        runtime.event_count += 1
        if self._recorder is None:
            raise RuntimeError("event recorder was not initialized")
        event = self._recorder.record(event_type, **attributes)
        runtime.event_history.append(
            StoredEvent(
                event.sequence,
                event.event_type,
                event.timestamp,
                event.attributes,
            )
        )

    def _persist(self, runtime: _Runtime) -> None:
        self._checkpoints.save(runtime)

    def _capture_scope_baseline(self, runtime: _Runtime) -> bool:
        try:
            runtime.scope_baseline = self._detector(runtime).capture()
        except DomainError as exc:
            self._escalate(
                runtime,
                FailureKind.ENVIRONMENT_TOOLING_FAILURE,
                "SCOPE_BASELINE_FAILED",
                str(exc),
            )
            return False
        self._event(
            runtime,
            "SCOPE_BASELINE_CAPTURED",
            changed_path_count=len(runtime.scope_baseline),
        )
        return True

    def _current_scope(self, runtime: _Runtime) -> tuple[str, ...]:
        return tuple(
            sorted(set(runtime.spec.fingerprint_scope) | set(self._actual_delta(runtime)))
        )

    def _actual_delta(self, runtime: _Runtime) -> tuple[str, ...]:
        current = self._detector(runtime).capture()
        return changed_since(runtime.scope_baseline, current)

    def _fingerprint_is_current(self, runtime: _Runtime) -> bool:
        if runtime.fingerprint is None:
            return False
        try:
            current_scope = self._current_scope(runtime)
            return (
                current_scope == runtime.fingerprint.scope
                and self._fingerprints.is_current(runtime.fingerprint)
            )
        except DomainError:
            return False

    def _detector(self, runtime: _Runtime) -> WorkspaceChangeDetector:
        if self._scope_detector is None:
            self._scope_detector = GitWorkspaceChangeDetector(
                runtime.spec.repository_root
            )
        return self._scope_detector

    @staticmethod
    def _latest(runtime: _Runtime, artifact_type: type[Any]) -> Any | None:
        return runtime.latest(artifact_type)

    @staticmethod
    def _plan_reference(runtime: _Runtime) -> str:
        return runtime.plan_reference

    @staticmethod
    def _result(runtime: _Runtime) -> CompletionResult:
        return runtime.completion_result()
