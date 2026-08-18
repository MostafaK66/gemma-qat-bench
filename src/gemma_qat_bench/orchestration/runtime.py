"""Mutable workflow runtime state and durable checkpoint codec."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, cast

from .artifacts import SpecialistArtifact, validate_artifact
from .domain import (
    ArtifactDefect,
    ArtifactKind,
    ArtifactValidationResult,
    BudgetSet,
    CommandEvidence,
    CommandId,
    CommandStatus,
    CompletionResult,
    CompletionStatus,
    DomainError,
    EscalationReason,
    FailureKind,
    Gate1Verdict,
    Gate2Verdict,
    Gate3Verdict,
    ImplementationFingerprint,
    ImplementationIteration,
    OutputHandling,
    PlanVersion,
    ResolutionClass,
    TaskId,
    TaskSpec,
    VerificationIteration,
    WorkflowDepth,
    WorkflowState,
)
from .evidence import EvidenceBinding, EvidenceLedger
from .fingerprint import FingerprintService
from .persistence import (
    StoredArtifact,
    StoredEvent,
    StoredEvidence,
    StoredValidation,
    WorkflowSnapshot,
    WorkflowStore,
    restore_task_spec,
    store_task_spec,
)
from .scope import ScopeBaseline
from .state_machine import WorkflowMachine


@dataclass(slots=True)
class RuntimeState:
    spec: TaskSpec
    machine: WorkflowMachine
    budgets: BudgetSet = field(default_factory=BudgetSet)
    plan_version: PlanVersion = field(default_factory=PlanVersion)
    implementation_iteration: ImplementationIteration = field(
        default_factory=ImplementationIteration
    )
    verification_iteration: VerificationIteration = field(
        default_factory=VerificationIteration
    )
    gate1: Gate1Verdict | None = None
    gate2: Gate2Verdict | None = None
    gate3: Gate3Verdict | None = None
    fingerprint: ImplementationFingerprint | None = None
    ledger: EvidenceLedger | None = None
    artifacts: list[tuple[str, SpecialistArtifact, dict[str, Any]]] = field(
        default_factory=list
    )
    validations: list[ArtifactValidationResult] = field(default_factory=list)
    escalation: EscalationReason | None = None
    event_count: int = 0
    invocation_count: int = 0
    resumed: bool = False
    scope_baseline: ScopeBaseline = field(default_factory=dict)
    event_history: list[StoredEvent] = field(default_factory=list)

    def latest(self, artifact_type: type[Any]) -> Any | None:
        for _, artifact, _ in reversed(self.artifacts):
            if isinstance(artifact, artifact_type):
                return artifact
        return None

    @property
    def plan_reference(self) -> str:
        return (
            "FAST-INTAKE"
            if self.machine.depth is WorkflowDepth.FAST
            else f"PLAN-{self.plan_version.value}"
        )

    def completion_result(self) -> CompletionResult:
        if self.machine.state is WorkflowState.COMPLETE:
            status = CompletionStatus.CHANGE_COMPLETE
        elif self.machine.state is WorkflowState.WAITING_AUTHORIZATION:
            status = CompletionStatus.WAITING_AUTHORIZATION
        elif self.machine.state is WorkflowState.ESCALATED:
            status = CompletionStatus.ESCALATED
        else:
            status = CompletionStatus.FAILED
        return CompletionResult(
            self.spec.task_id,
            status,
            self.machine.state,
            self.machine.depth,
            self.plan_version,
            self.implementation_iteration,
            self.verification_iteration,
            self.gate1,
            self.gate2,
            self.gate3,
            self.fingerprint,
            self.escalation,
        )


class CheckpointManager:
    """Encode/decode runtime state without exposing storage details to the engine."""

    def __init__(self, store: WorkflowStore) -> None:
        self._store = store

    def load(self, task_id: TaskId) -> WorkflowSnapshot | None:
        return self._store.load(task_id)

    def load_task_spec(self, task_id: TaskId) -> TaskSpec | None:
        """Load the protected complete spec for task-ID-only resume."""
        snapshot = self.load(task_id)
        if snapshot is None or snapshot.task_spec is None:
            return None
        return restore_task_spec(task_id, snapshot.task_spec)

    def save(self, runtime: RuntimeState) -> None:
        fingerprint = runtime.fingerprint
        evidence: tuple[StoredEvidence, ...] = ()
        if runtime.ledger is not None:
            evidence = tuple(
                StoredEvidence(
                    command_id=str(record.command_id),
                    exact_argv=record.exact_argv,
                    cwd=record.cwd,
                    status=record.status.value,
                    exit_code=record.exit_code,
                    permitted_output_excerpt=record.output_excerpt,
                    output_truncated=record.output_truncated,
                    required=record.required,
                    fingerprint=record.fingerprint,
                    output_handling=record.output_handling.value,
                )
                for record in runtime.ledger.records()
            )
        escalation = None
        if runtime.escalation is not None:
            escalation = {
                "failure_kind": runtime.escalation.failure_kind.value,
                "code": runtime.escalation.code,
                "message": runtime.escalation.message,
                "resolution_class": ""
                if runtime.escalation.resolution_class is None
                else runtime.escalation.resolution_class.value,
            }
        self._store.save(
            WorkflowSnapshot(
                schema_version=2,
                task_id=runtime.spec.task_id,
                state=runtime.machine.state,
                depth=runtime.machine.depth,
                risk=runtime.spec.risk.value,
                plan_version=runtime.plan_version.value,
                implementation_iteration=runtime.implementation_iteration.value,
                verification_iteration=runtime.verification_iteration.value,
                budgets=runtime.budgets.as_dict(),
                gate1=None if runtime.gate1 is None else runtime.gate1.value,
                gate2=None if runtime.gate2 is None else runtime.gate2.value,
                gate3=None if runtime.gate3 is None else runtime.gate3.value,
                artifacts=tuple(
                    StoredArtifact(type(artifact).__name__, invocation_id, payload)
                    for invocation_id, artifact, payload in runtime.artifacts
                ),
                validations=tuple(
                    StoredValidation(
                        validation.kind.value,
                        validation.valid,
                        tuple(defect.code for defect in validation.defects),
                    )
                    for validation in runtime.validations
                ),
                evidence=evidence,
                fingerprint_digest=None if fingerprint is None else fingerprint.digest,
                fingerprint_scope=() if fingerprint is None else fingerprint.scope,
                scope_baseline=dict(runtime.scope_baseline),
                escalation=escalation,
                events=tuple(runtime.event_history),
                event_count=runtime.event_count,
                task_spec=store_task_spec(runtime.spec),
            )
        )

    def restore(self, spec: TaskSpec, snapshot: WorkflowSnapshot) -> RuntimeState:
        if snapshot.task_id != spec.task_id or snapshot.risk != spec.risk.value:
            raise DomainError(
                "resume task specification does not match persisted identity"
            )
        if snapshot.task_spec is not None:
            persisted_spec = restore_task_spec(snapshot.task_id, snapshot.task_spec)
            if persisted_spec != spec:
                raise DomainError(
                    "resume task specification does not match the protected checkpoint"
                )
        budgets = BudgetSet()
        for name, counters in snapshot.budgets.items():
            budget = getattr(budgets, name, None)
            if budget is None:
                raise DomainError(f"snapshot contains unknown budget: {name}")
            setattr(
                budgets,
                name,
                type(budget)(name, counters["limit"], counters["consumed"]),
            )
        runtime = RuntimeState(
            spec=spec,
            machine=WorkflowMachine(snapshot.depth, snapshot.state),
            budgets=budgets,
            plan_version=PlanVersion(snapshot.plan_version),
            implementation_iteration=ImplementationIteration(
                snapshot.implementation_iteration
            ),
            verification_iteration=VerificationIteration(snapshot.verification_iteration),
            gate1=None if snapshot.gate1 is None else Gate1Verdict(snapshot.gate1),
            gate2=None if snapshot.gate2 is None else Gate2Verdict(snapshot.gate2),
            gate3=None if snapshot.gate3 is None else Gate3Verdict(snapshot.gate3),
            event_count=snapshot.event_count,
            invocation_count=len(snapshot.artifacts) + len(snapshot.validations),
            scope_baseline=dict(snapshot.scope_baseline),
            event_history=list(snapshot.events),
        )
        if snapshot.fingerprint_digest is not None:
            runtime.fingerprint = ImplementationFingerprint(
                FingerprintService.ALGORITHM,
                snapshot.fingerprint_digest,
                snapshot.fingerprint_scope,
                (),
            )
        self._restore_artifacts(runtime, snapshot)
        runtime.validations = [
            ArtifactValidationResult(
                ArtifactKind(item.kind),
                item.valid,
                object() if item.valid else None,
                ()
                if item.valid
                else tuple(
                    ArtifactDefect(code, "persisted defect") for code in item.defect_codes
                ),
            )
            for item in snapshot.validations
        ]
        if snapshot.evidence:
            runtime.ledger = self._restore_evidence(runtime, snapshot)
        if snapshot.escalation is not None:
            resolution = snapshot.escalation.get("resolution_class", "")
            runtime.escalation = EscalationReason(
                FailureKind(snapshot.escalation["failure_kind"]),
                snapshot.escalation["code"],
                snapshot.escalation["message"],
                None if not resolution else ResolutionClass(resolution),
            )
        return runtime

    @staticmethod
    def _restore_artifacts(runtime: RuntimeState, snapshot: WorkflowSnapshot) -> None:
        expected_ids = tuple(
            str(command.command_id) for command in runtime.spec.required_commands
        )
        for stored in snapshot.artifacts:
            kind = _stored_artifact_kind(stored.kind)
            validation = validate_artifact(
                kind,
                json.dumps(stored.payload),
                expected_command_ids=expected_ids,
            )
            if not validation.valid or validation.artifact is None:
                raise DomainError(f"persisted {stored.kind} artifact no longer validates")
            runtime.artifacts.append(
                (
                    stored.invocation_id,
                    cast(SpecialistArtifact, validation.artifact),
                    stored.payload,
                )
            )

    @staticmethod
    def _restore_evidence(
        runtime: RuntimeState, snapshot: WorkflowSnapshot
    ) -> EvidenceLedger:
        if runtime.fingerprint is None:
            raise DomainError("persisted evidence is missing its fingerprint binding")
        command_ids = tuple(
            str(command.command_id) for command in runtime.spec.required_commands
        )
        ledger = EvidenceLedger(
            EvidenceBinding(
                runtime.spec.task_id,
                runtime.plan_reference,
                runtime.implementation_iteration.value,
                runtime.verification_iteration.value,
                "task_spec.required_commands",
                runtime.fingerprint.digest,
            ),
            command_ids,
        )
        for item in snapshot.evidence:
            ledger.record(
                CommandEvidence(
                    CommandId(item.command_id),
                    item.exact_argv,
                    item.cwd,
                    CommandStatus(item.status),
                    item.exit_code,
                    item.permitted_output_excerpt,
                    item.output_truncated,
                    item.required,
                    item.fingerprint,
                    OutputHandling(item.output_handling),
                )
            )
        return ledger


def _stored_artifact_kind(class_name: str) -> ArtifactKind:
    mapping = {
        "PlanArtifact": ArtifactKind.PLAN,
        "PlanCritiqueArtifact": ArtifactKind.PLAN_CRITIQUE,
        "ImplementationArtifact": ArtifactKind.IMPLEMENTATION,
        "VerificationArtifact": ArtifactKind.VERIFICATION,
        "ReviewArtifact": ArtifactKind.REVIEW,
    }
    try:
        return mapping[class_name]
    except KeyError as exc:
        raise DomainError(f"unknown persisted artifact type: {class_name}") from exc
