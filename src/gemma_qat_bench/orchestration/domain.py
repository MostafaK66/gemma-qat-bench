"""Typed domain model for deterministic V3 coding orchestration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any


class DomainError(ValueError):
    """Raised when a domain invariant would be violated."""


class RiskLevel(StrEnum):
    TRIVIAL_MECHANICAL = "TRIVIAL_MECHANICAL"
    LOW_RISK = "LOW_RISK"
    STANDARD = "STANDARD"
    HIGH_RISK = "HIGH_RISK"


class WorkflowDepth(StrEnum):
    FAST = "FAST"
    FULL = "FULL"


class WorkflowState(StrEnum):
    INTAKE = "INTAKE"
    PLANNING = "PLANNING"
    PLAN_CRITIQUE = "PLAN_CRITIQUE"
    GATE_1 = "GATE_1"
    IMPLEMENTATION = "IMPLEMENTATION"
    COMMAND_VERIFICATION = "COMMAND_VERIFICATION"
    GATE_2 = "GATE_2"
    REVIEW = "REVIEW"
    GATE_3 = "GATE_3"
    ESCALATING = "ESCALATING"
    WAITING_AUTHORIZATION = "WAITING_AUTHORIZATION"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"
    COMPLETE = "COMPLETE"


class Gate(StrEnum):
    GATE_1 = "GATE_1"
    GATE_2 = "GATE_2"
    GATE_3 = "GATE_3"


class Gate1Verdict(StrEnum):
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class Gate2Verdict(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"


class Gate3Verdict(StrEnum):
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class SpecialistRole(StrEnum):
    PLANNER = "PLANNER"
    PLAN_CRITIC = "PLAN_CRITIC"
    IMPLEMENTER = "IMPLEMENTER"
    VERIFIER = "VERIFIER"
    REVIEWER = "REVIEWER"


class ArtifactKind(StrEnum):
    PLAN = "PLAN"
    PLAN_CRITIQUE = "PLAN_CRITIQUE"
    IMPLEMENTATION = "IMPLEMENTATION"
    VERIFICATION = "VERIFICATION"
    REVIEW = "REVIEW"


class FailureKind(StrEnum):
    PROFILE_UNAVAILABLE = "PROFILE_UNAVAILABLE"
    INVOCATION_FAILED = "INVOCATION_FAILED"
    MALFORMED_ARTIFACT = "MALFORMED_ARTIFACT"
    AGENT_LOOP_TIMEOUT_OR_LIMIT = "AGENT_LOOP_TIMEOUT_OR_LIMIT"
    TOOL_CAPABILITY_FAILURE = "TOOL_CAPABILITY_FAILURE"
    ENVIRONMENT_TOOLING_FAILURE = "ENVIRONMENT_TOOLING_FAILURE"
    QUALITY_GATE_FAILURE = "QUALITY_GATE_FAILURE"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    FINGERPRINT_DRIFT = "FINGERPRINT_DRIFT"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"


class ResolutionClass(StrEnum):
    EVIDENCE_RESOLVABLE = "EVIDENCE_RESOLVABLE"
    HUMAN_INTENT_REQUIRED = "HUMAN_INTENT_REQUIRED"


class EvidenceQuality(StrEnum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"


class AuthorizationStatus(StrEnum):
    REQUIRED = "REQUIRED"
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"


class CommandStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ENVIRONMENT_ERROR = "ENVIRONMENT_ERROR"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    DENIED = "DENIED"


class OutputHandling(StrEnum):
    STATUS_ONLY = "STATUS_ONLY"
    EXCERPT = "EXCERPT"


class TransportStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class CompletionStatus(StrEnum):
    CHANGE_COMPLETE = "CHANGE_COMPLETE"
    WAITING_AUTHORIZATION = "WAITING_AUTHORIZATION"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class TaskId:
    value: str

    def __post_init__(self) -> None:
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", self.value) is None:
            raise DomainError(
                "task ID must use only letters, digits, dot, underscore, or hyphen"
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PlanVersion:
    value: int = 1

    def __post_init__(self) -> None:
        if self.value < 1:
            raise DomainError("plan version must be positive")

    def next(self) -> PlanVersion:
        return PlanVersion(self.value + 1)


@dataclass(frozen=True, slots=True)
class ImplementationIteration:
    value: int = 1

    def __post_init__(self) -> None:
        if self.value < 1:
            raise DomainError("implementation iteration must be positive")

    def next(self) -> ImplementationIteration:
        return ImplementationIteration(self.value + 1)


@dataclass(frozen=True, slots=True)
class VerificationIteration:
    value: int = 1

    def __post_init__(self) -> None:
        if self.value < 1:
            raise DomainError("verification iteration must be positive")

    def next(self) -> VerificationIteration:
        return VerificationIteration(self.value + 1)


@dataclass(frozen=True, slots=True)
class RevisionBudget:
    name: str
    limit: int
    consumed: int = 0

    def __post_init__(self) -> None:
        if self.limit < 0 or not 0 <= self.consumed <= self.limit:
            raise DomainError("revision budget counters are invalid")

    @property
    def remaining(self) -> int:
        return self.limit - self.consumed

    def consume(self) -> RevisionBudget:
        if self.remaining == 0:
            raise DomainError(f"budget exhausted: {self.name}")
        return RevisionBudget(self.name, self.limit, self.consumed + 1)


@dataclass(frozen=True, slots=True)
class CommandId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or any(ch.isspace() for ch in self.value):
            raise DomainError("command ID must be non-empty and contain no whitespace")

    def __str__(self) -> str:
        return self.value


def normalize_repository_path(value: str) -> str:
    """Return a safe, normalized repository-relative path."""
    raw = value.replace("\\", "/")
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or path == PurePosixPath("."):
        raise DomainError(f"unsafe repository-relative path: {value!r}")
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class RequiredCommand:
    command_id: CommandId
    argv: tuple[str, ...]
    cwd: str = "."
    required: bool = True
    rationale: str = "task acceptance criteria"
    output_handling: OutputHandling = OutputHandling.STATUS_ONLY

    def __post_init__(self) -> None:
        if not self.argv or any(not part for part in self.argv):
            raise DomainError("command argv must contain non-empty arguments")
        if (
            Path(self.cwd).is_absolute()
            or ".." in PurePosixPath(self.cwd.replace("\\", "/")).parts
        ):
            raise DomainError("command cwd must stay within the repository")


@dataclass(frozen=True, slots=True)
class CommandEvidence:
    command_id: CommandId
    exact_argv: tuple[str, ...]
    cwd: str
    status: CommandStatus
    exit_code: int | None
    output_excerpt: str
    output_truncated: bool
    required: bool
    fingerprint: str
    output_handling: OutputHandling = OutputHandling.STATUS_ONLY


@dataclass(frozen=True, slots=True)
class ImplementationFingerprint:
    algorithm: str
    digest: str
    scope: tuple[str, ...]
    manifest: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.algorithm != "implementation-fingerprint-v1":
            raise DomainError("unsupported implementation fingerprint algorithm")
        if len(self.digest) != 64:
            raise DomainError("implementation fingerprint must be SHA-256 hex")


@dataclass(frozen=True, slots=True)
class SpecialistInvocation:
    invocation_id: str
    role: SpecialistRole
    artifact_kind: ArtifactKind
    attempt: int

    def __post_init__(self) -> None:
        if not self.invocation_id or self.attempt < 1:
            raise DomainError("specialist invocation identity is invalid")


@dataclass(frozen=True, slots=True)
class ArtifactDefect:
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class ArtifactValidationResult:
    kind: ArtifactKind
    valid: bool
    artifact: Any | None
    defects: tuple[ArtifactDefect, ...] = ()

    def __post_init__(self) -> None:
        if self.valid != (self.artifact is not None and not self.defects):
            raise DomainError("artifact validation result is internally inconsistent")


@dataclass(frozen=True, slots=True)
class EscalationReason:
    failure_kind: FailureKind
    code: str
    message: str
    resolution_class: ResolutionClass | None = None


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: TaskId
    description: str
    acceptance_criteria: tuple[str, ...]
    risk: RiskLevel
    fast_eligible: bool
    repository_root: Path
    required_commands: tuple[RequiredCommand, ...]
    fingerprint_scope: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.description.strip() or not self.acceptance_criteria:
            raise DomainError("task description and acceptance criteria are required")
        ids = [str(command.command_id) for command in self.required_commands]
        if len(ids) != len(set(ids)):
            raise DomainError("required command IDs must be unique")
        if not any(command.required for command in self.required_commands):
            raise DomainError(
                "task must declare at least one required verification command; "
                "Gate 2 cannot pass on an empty evidence ledger"
            )
        normalized = tuple(
            normalize_repository_path(path) for path in self.fingerprint_scope
        )
        if len(normalized) != len(set(normalized)):
            raise DomainError("fingerprint scope paths must be unique")
        if not self.repository_root.is_absolute():
            raise DomainError("repository root must be absolute")


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    risk: RiskLevel
    native_depth: WorkflowDepth
    reason: str
    policy_version: str


@dataclass(frozen=True, slots=True)
class CompletionResult:
    task_id: TaskId
    status: CompletionStatus
    state: WorkflowState
    depth: WorkflowDepth
    plan_version: PlanVersion
    implementation_iteration: ImplementationIteration
    verification_iteration: VerificationIteration
    gate1: Gate1Verdict | None = None
    gate2: Gate2Verdict | None = None
    gate3: Gate3Verdict | None = None
    fingerprint: ImplementationFingerprint | None = None
    escalation: EscalationReason | None = None


@dataclass(slots=True)
class BudgetSet:
    """Mutable holder whose values remain immutable and auditable."""

    plan_revision: RevisionBudget = field(
        default_factory=lambda: RevisionBudget("plan_revision", 2)
    )
    implementation_revision: RevisionBudget = field(
        default_factory=lambda: RevisionBudget("implementation_revision", 2)
    )
    verifier_schema_repair: RevisionBudget = field(
        default_factory=lambda: RevisionBudget("verifier_schema_repair", 1)
    )
    reviewer_repair: RevisionBudget = field(
        default_factory=lambda: RevisionBudget("reviewer_repair", 2)
    )
    invocation_retry: RevisionBudget = field(
        default_factory=lambda: RevisionBudget("invocation_retry", 1)
    )

    def consume(self, name: str) -> RevisionBudget:
        budget = getattr(self, name, None)
        if not isinstance(budget, RevisionBudget):
            raise DomainError(f"unknown budget: {name}")
        updated = budget.consume()
        setattr(self, name, updated)
        return updated

    def as_dict(self) -> dict[str, dict[str, int]]:
        names = (
            "plan_revision",
            "implementation_revision",
            "verifier_schema_repair",
            "reviewer_repair",
            "invocation_retry",
        )
        return {
            name: {
                "limit": getattr(self, name).limit,
                "consumed": getattr(self, name).consumed,
            }
            for name in names
        }
