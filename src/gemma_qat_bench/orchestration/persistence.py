"""Local, atomic persistence for inspectable and resumable workflow checkpoints."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from .domain import (
    CommandId,
    DomainError,
    OutputHandling,
    RequiredCommand,
    RiskLevel,
    TaskId,
    TaskSpec,
    WorkflowDepth,
    WorkflowState,
)


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    kind: str
    invocation_id: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class StoredValidation:
    kind: str
    valid: bool
    defect_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StoredEvidence:
    command_id: str
    exact_argv: tuple[str, ...]
    cwd: str
    status: str
    exit_code: int | None
    permitted_output_excerpt: str
    output_truncated: bool
    required: bool
    fingerprint: str
    output_handling: str = "STATUS_ONLY"


@dataclass(frozen=True, slots=True)
class StoredEvent:
    sequence: int
    event_type: str
    timestamp: str
    attributes: dict[str, Any]


@dataclass(frozen=True, slots=True)
class StoredRequiredCommand:
    command_id: str
    argv: tuple[str, ...]
    cwd: str
    required: bool
    rationale: str
    output_handling: str


@dataclass(frozen=True, slots=True)
class StoredTaskSpec:
    description: str
    acceptance_criteria: tuple[str, ...]
    risk: str
    fast_eligible: bool
    repository_root: str
    required_commands: tuple[StoredRequiredCommand, ...]
    fingerprint_scope: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkflowSnapshot:
    schema_version: int
    task_id: TaskId
    state: WorkflowState
    depth: WorkflowDepth
    risk: str
    plan_version: int
    implementation_iteration: int
    verification_iteration: int
    budgets: dict[str, dict[str, int]]
    gate1: str | None
    gate2: str | None
    gate3: str | None
    artifacts: tuple[StoredArtifact, ...]
    validations: tuple[StoredValidation, ...]
    evidence: tuple[StoredEvidence, ...]
    fingerprint_digest: str | None
    fingerprint_scope: tuple[str, ...]
    scope_baseline: dict[str, str]
    escalation: dict[str, str] | None
    events: tuple[StoredEvent, ...]
    event_count: int
    task_spec: StoredTaskSpec | None = None

    def __post_init__(self) -> None:
        if self.schema_version not in {1, 2}:
            raise DomainError("unsupported workflow snapshot schema version")
        if self.schema_version == 2 and self.task_spec is None:
            raise DomainError("workflow snapshot schema v2 requires a stored TaskSpec")
        if self.event_count != len(self.events) or tuple(
            event.sequence for event in self.events
        ) != tuple(range(1, self.event_count + 1)):
            raise DomainError(
                "workflow snapshot event history is incomplete or unordered"
            )


class WorkflowStore(Protocol):
    def save(self, snapshot: WorkflowSnapshot) -> None: ...

    def load(self, task_id: TaskId) -> WorkflowSnapshot | None: ...


class InMemoryWorkflowStore:
    def __init__(self) -> None:
        self.snapshots: dict[str, WorkflowSnapshot] = {}

    def save(self, snapshot: WorkflowSnapshot) -> None:
        self.snapshots[str(snapshot.task_id)] = snapshot

    def load(self, task_id: TaskId) -> WorkflowSnapshot | None:
        return self.snapshots.get(str(task_id))


class JsonFileWorkflowStore:
    """Write mode-0600 JSON checkpoints in a private state directory."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def _path(self, task_id: TaskId) -> Path:
        return self._directory / f"{task_id}.json"

    def save(self, snapshot: WorkflowSnapshot) -> None:
        self._directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._directory.chmod(0o700)
        payload = asdict(snapshot)
        payload["task_id"] = str(snapshot.task_id)
        payload["state"] = snapshot.state.value
        payload["depth"] = snapshot.depth.value
        content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        fd, temporary = tempfile.mkstemp(
            prefix=f".{snapshot.task_id}.", suffix=".tmp", dir=self._directory
        )
        temporary_path = Path(temporary)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.chmod(0o600)
            os.replace(temporary_path, self._path(snapshot.task_id))
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def load(self, task_id: TaskId) -> WorkflowSnapshot | None:
        path = self._path(task_id)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise TypeError("snapshot root must be an object")
            data = cast(dict[str, Any], raw)
            artifacts = tuple(
                StoredArtifact(
                    str(item["kind"]),
                    str(item["invocation_id"]),
                    cast(dict[str, Any], item["payload"]),
                )
                for item in data["artifacts"]
            )
            validations = tuple(
                StoredValidation(
                    str(item["kind"]),
                    bool(item["valid"]),
                    tuple(str(code) for code in item["defect_codes"]),
                )
                for item in data["validations"]
            )
            evidence = tuple(
                StoredEvidence(
                    command_id=str(item["command_id"]),
                    exact_argv=tuple(str(value) for value in item["exact_argv"]),
                    cwd=str(item["cwd"]),
                    status=str(item["status"]),
                    exit_code=(
                        None if item["exit_code"] is None else int(item["exit_code"])
                    ),
                    permitted_output_excerpt=str(item["permitted_output_excerpt"]),
                    output_truncated=bool(item["output_truncated"]),
                    required=bool(item["required"]),
                    fingerprint=str(item["fingerprint"]),
                    output_handling=str(item.get("output_handling", "STATUS_ONLY")),
                )
                for item in data["evidence"]
            )
            escalation_raw = data["escalation"]
            escalation = (
                None
                if escalation_raw is None
                else {str(key): str(value) for key, value in escalation_raw.items()}
            )
            events = tuple(
                StoredEvent(
                    sequence=int(item["sequence"]),
                    event_type=str(item["event_type"]),
                    timestamp=str(item["timestamp"]),
                    attributes=cast(dict[str, Any], item["attributes"]),
                )
                for item in data["events"]
            )
            task_spec = _decode_task_spec(data.get("task_spec"))
            return WorkflowSnapshot(
                schema_version=int(data["schema_version"]),
                task_id=TaskId(str(data["task_id"])),
                state=WorkflowState(str(data["state"])),
                depth=WorkflowDepth(str(data["depth"])),
                risk=str(data["risk"]),
                plan_version=int(data["plan_version"]),
                implementation_iteration=int(data["implementation_iteration"]),
                verification_iteration=int(data["verification_iteration"]),
                budgets={
                    str(name): {str(key): int(value) for key, value in counters.items()}
                    for name, counters in data["budgets"].items()
                },
                gate1=None if data["gate1"] is None else str(data["gate1"]),
                gate2=None if data["gate2"] is None else str(data["gate2"]),
                gate3=None if data["gate3"] is None else str(data["gate3"]),
                artifacts=artifacts,
                validations=validations,
                evidence=evidence,
                fingerprint_digest=(
                    None
                    if data["fingerprint_digest"] is None
                    else str(data["fingerprint_digest"])
                ),
                fingerprint_scope=tuple(
                    str(value) for value in data["fingerprint_scope"]
                ),
                scope_baseline={
                    str(path): str(identity)
                    for path, identity in data["scope_baseline"].items()
                },
                escalation=escalation,
                events=events,
                event_count=int(data["event_count"]),
                task_spec=task_spec,
            )
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise DomainError(f"invalid workflow snapshot {path}: {exc}") from exc


def store_task_spec(spec: TaskSpec) -> StoredTaskSpec:
    """Encode the complete validated spec needed for task-ID-only resume."""
    return StoredTaskSpec(
        description=spec.description,
        acceptance_criteria=spec.acceptance_criteria,
        risk=spec.risk.value,
        fast_eligible=spec.fast_eligible,
        repository_root=str(spec.repository_root),
        required_commands=tuple(
            StoredRequiredCommand(
                command_id=str(command.command_id),
                argv=command.argv,
                cwd=command.cwd,
                required=command.required,
                rationale=command.rationale,
                output_handling=command.output_handling.value,
            )
            for command in spec.required_commands
        ),
        fingerprint_scope=spec.fingerprint_scope,
    )


def restore_task_spec(task_id: TaskId, stored: StoredTaskSpec) -> TaskSpec:
    """Reconstruct a strict TaskSpec from its protected checkpoint representation."""
    return TaskSpec(
        task_id=task_id,
        description=stored.description,
        acceptance_criteria=stored.acceptance_criteria,
        risk=RiskLevel(stored.risk),
        fast_eligible=stored.fast_eligible,
        repository_root=Path(stored.repository_root),
        required_commands=tuple(
            RequiredCommand(
                command_id=CommandId(command.command_id),
                argv=command.argv,
                cwd=command.cwd,
                required=command.required,
                rationale=command.rationale,
                output_handling=OutputHandling(command.output_handling),
            )
            for command in stored.required_commands
        ),
        fingerprint_scope=stored.fingerprint_scope,
    )


def _decode_task_spec(raw: Any) -> StoredTaskSpec | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise TypeError("task_spec must be an object")
    data = cast(dict[str, Any], raw)
    _require_exact_fields(
        data,
        {
            "description",
            "acceptance_criteria",
            "risk",
            "fast_eligible",
            "repository_root",
            "required_commands",
            "fingerprint_scope",
        },
        "task_spec",
    )
    commands_raw = data["required_commands"]
    if not isinstance(commands_raw, list):
        raise TypeError("task_spec.required_commands must be an array")
    commands: list[StoredRequiredCommand] = []
    for index, raw_command in enumerate(commands_raw, start=1):
        if not isinstance(raw_command, dict):
            raise TypeError(f"task_spec.required_commands[{index}] must be an object")
        command = cast(dict[str, Any], raw_command)
        location = f"task_spec.required_commands[{index}]"
        _require_exact_fields(
            command,
            {
                "command_id",
                "argv",
                "cwd",
                "required",
                "rationale",
                "output_handling",
            },
            location,
        )
        commands.append(
            StoredRequiredCommand(
                command_id=_strict_string(
                    command["command_id"], f"{location}.command_id"
                ),
                argv=_strict_strings(command["argv"], f"{location}.argv"),
                cwd=_strict_string(command["cwd"], f"{location}.cwd"),
                required=_strict_bool(command["required"], f"{location}.required"),
                rationale=_strict_string(command["rationale"], f"{location}.rationale"),
                output_handling=_strict_string(
                    command["output_handling"], f"{location}.output_handling"
                ),
            )
        )
    return StoredTaskSpec(
        description=_strict_string(data["description"], "task_spec.description"),
        acceptance_criteria=_strict_strings(
            data["acceptance_criteria"], "task_spec.acceptance_criteria"
        ),
        risk=_strict_string(data["risk"], "task_spec.risk"),
        fast_eligible=_strict_bool(data["fast_eligible"], "task_spec.fast_eligible"),
        repository_root=_strict_string(
            data["repository_root"], "task_spec.repository_root"
        ),
        required_commands=tuple(commands),
        fingerprint_scope=_strict_strings(
            data["fingerprint_scope"], "task_spec.fingerprint_scope"
        ),
    )


def _require_exact_fields(
    data: dict[str, Any], expected: set[str], location: str
) -> None:
    if set(data) != expected:
        missing = sorted(expected - data.keys())
        unknown = sorted(data.keys() - expected)
        raise TypeError(
            f"{location} field mismatch; missing={missing}, unknown={unknown}"
        )


def _strict_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{location} must be a non-empty string")
    return value


def _strict_strings(value: Any, location: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{location} must be an array")
    return tuple(
        _strict_string(item, f"{location}[{index}]")
        for index, item in enumerate(value, start=1)
    )


def _strict_bool(value: Any, location: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{location} must be a boolean")
    return value
