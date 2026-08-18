"""Local, atomic persistence for inspectable and resumable workflow checkpoints."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from .domain import DomainError, TaskId, WorkflowDepth, WorkflowState


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

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise DomainError("unsupported workflow snapshot schema version")
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
    """Write one mode-0600 JSON checkpoint per task using atomic replacement."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def _path(self, task_id: TaskId) -> Path:
        return self._directory / f"{task_id}.json"

    def save(self, snapshot: WorkflowSnapshot) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
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
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise DomainError(f"invalid workflow snapshot {path}: {exc}") from exc
