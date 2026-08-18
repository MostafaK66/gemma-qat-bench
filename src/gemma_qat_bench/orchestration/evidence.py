"""Single canonical evidence ledger with specialist-safe projections."""

from __future__ import annotations

from dataclasses import dataclass

from .domain import CommandEvidence, CommandStatus, DomainError, TaskId


@dataclass(frozen=True, slots=True)
class EvidenceBinding:
    task_id: TaskId
    plan_reference: str
    implementation_iteration: int
    verification_iteration: int
    required_command_set_source: str
    implementation_fingerprint: str


@dataclass(frozen=True, slots=True)
class VerifierEvidenceView:
    command_id: str
    successful: bool
    status: str
    permitted_evidence_material: str
    output_truncated: bool


class EvidenceLedger:
    """The sole authoritative record for one verification attempt."""

    def __init__(
        self, binding: EvidenceBinding, expected_command_ids: tuple[str, ...]
    ) -> None:
        if len(expected_command_ids) != len(set(expected_command_ids)):
            raise DomainError("expected evidence command IDs must be unique")
        self.binding = binding
        self._expected = expected_command_ids
        self._records: dict[str, CommandEvidence] = {}
        self._valid = True

    def record(self, evidence: CommandEvidence) -> None:
        command_id = str(evidence.command_id)
        if command_id not in self._expected:
            raise DomainError(f"unknown command evidence: {command_id}")
        if command_id in self._records:
            raise DomainError(f"duplicate command evidence: {command_id}")
        if evidence.fingerprint != self.binding.implementation_fingerprint:
            raise DomainError(
                "command evidence fingerprint does not match ledger binding"
            )
        self._records[command_id] = evidence

    def invalidate(self) -> None:
        self._valid = False

    @property
    def valid(self) -> bool:
        return self._valid

    @property
    def complete(self) -> bool:
        return set(self._records) == set(self._expected)

    @property
    def required_failed(self) -> bool:
        return any(
            record.required and record.status is CommandStatus.FAILED
            for record in self._records.values()
        )

    @property
    def environment_failed(self) -> bool:
        return any(
            record.required and record.status is CommandStatus.ENVIRONMENT_ERROR
            for record in self._records.values()
        )

    @property
    def authorization_denied(self) -> bool:
        return any(
            record.required and record.status is CommandStatus.DENIED
            for record in self._records.values()
        )

    @property
    def authorization_required(self) -> bool:
        return any(
            record.required and record.status is CommandStatus.AUTHORIZATION_REQUIRED
            for record in self._records.values()
        )

    def verifier_view(self) -> tuple[VerifierEvidenceView, ...]:
        if not self._valid:
            raise DomainError("stale evidence cannot be projected")
        if not self.complete:
            raise DomainError("incomplete evidence cannot be projected")
        return tuple(
            VerifierEvidenceView(
                command_id,
                record.status is CommandStatus.SUCCEEDED,
                record.status.value,
                record.output_excerpt,
                record.output_truncated,
            )
            for command_id, record in sorted(self._records.items())
        )

    def records(self) -> tuple[CommandEvidence, ...]:
        return tuple(record for _, record in sorted(self._records.items()))
