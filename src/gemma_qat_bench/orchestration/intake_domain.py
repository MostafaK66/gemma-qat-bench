"""Typed boundary models for natural-language task intake."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .domain import DomainError, FailureKind, RoutingDecision, TaskSpec, TransportStatus


@dataclass(frozen=True, slots=True)
class NaturalLanguageTaskRequest:
    """The semantic input a normal user supplies before deterministic compilation."""

    description: str
    repository_root: Path
    clarifications: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise DomainError("natural-language task description must not be empty")
        if not self.repository_root.is_absolute():
            raise DomainError("intake repository root must be absolute")
        if any(not item.strip() for item in self.clarifications):
            raise DomainError("task clarifications must be non-empty strings")


@dataclass(frozen=True, slots=True)
class IntakeRiskSignals:
    """Semantic facts consumed by deterministic risk and FAST/FULL policy."""

    exact_outcome: bool
    unique_repository_evidence: bool
    cohesive_scope: bool
    focused_verification_available: bool
    public_contract_impact: bool
    configuration_impact: bool
    architecture_or_ownership_impact: bool
    security_or_privacy_impact: bool
    data_impact: bool
    dependency_impact: bool
    operational_impact: bool
    compatibility_impact: bool
    uncertainty_present: bool


@dataclass(frozen=True, slots=True)
class VerificationCommandProposal:
    """A shell-free verification command proposed from repository evidence."""

    argv: tuple[str, ...]
    cwd: str
    rationale: str


@dataclass(frozen=True, slots=True)
class IntakeAmbiguity:
    """One consequential product decision that repository evidence cannot resolve."""

    question: str
    impact: str


@dataclass(frozen=True, slots=True)
class TaskIntakeAnalysis:
    """Strict read-only semantic analysis returned by an intake provider."""

    normalized_description: str
    acceptance_criteria: tuple[str, ...]
    candidate_scope: tuple[str, ...]
    verification_commands: tuple[VerificationCommandProposal, ...]
    risk_signals: IntakeRiskSignals
    ambiguities: tuple[IntakeAmbiguity, ...]
    assumptions: tuple[str, ...]
    repository_evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TaskIntakeProviderResult:
    """Transport result kept distinct from local intake-schema validation."""

    status: TransportStatus
    raw_response: str | None
    failure_kind: FailureKind | None = None
    error_message: str | None = None
    provider_request_id: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


class TaskIntentAnalyzer(Protocol):
    """Read-only provider boundary for repository-aware semantic task analysis."""

    def analyze(
        self, request: NaturalLanguageTaskRequest
    ) -> TaskIntakeProviderResult: ...


@dataclass(frozen=True, slots=True)
class CompiledTask:
    """A complete strict TaskSpec plus transparent intake reasoning."""

    spec: TaskSpec
    analysis: TaskIntakeAnalysis
    routing: RoutingDecision


__all__ = [
    "CompiledTask",
    "IntakeAmbiguity",
    "IntakeRiskSignals",
    "NaturalLanguageTaskRequest",
    "TaskIntakeAnalysis",
    "TaskIntakeProviderResult",
    "TaskIntentAnalyzer",
    "VerificationCommandProposal",
]
