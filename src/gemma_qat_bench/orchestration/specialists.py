"""Provider-independent specialist invocation boundary and deterministic fake."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .artifacts import artifact_json_schema
from .domain import (
    ArtifactKind,
    FailureKind,
    SpecialistInvocation,
    SpecialistRole,
    TransportStatus,
)


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    structured_output: bool
    raw_response_access: bool
    tool_calls: bool
    streaming: bool
    usage_metadata: bool


@dataclass(frozen=True, slots=True)
class SpecialistRequest:
    invocation: SpecialistInvocation
    repository_root: Path
    prompt: str
    output_schema: dict[str, Any]
    may_write_workspace: bool


@dataclass(frozen=True, slots=True)
class SpecialistResult:
    status: TransportStatus
    raw_response: str | None
    failure_kind: FailureKind | None = None
    error_message: str | None = None
    provider_request_id: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


class SpecialistClient(Protocol):
    @property
    def capabilities(self) -> ProviderCapabilities: ...

    def invoke(self, request: SpecialistRequest) -> SpecialistResult: ...


@dataclass(frozen=True, slots=True)
class ScriptedResponse:
    role: SpecialistRole
    raw_response: str | None = None
    failure_kind: FailureKind | None = None
    error_message: str | None = None


class ScriptedSpecialistClient:
    """FIFO fake that fails if actual specialist order differs from the script."""

    def __init__(
        self,
        responses: list[ScriptedResponse],
        *,
        capabilities: ProviderCapabilities | None = None,
    ) -> None:
        self._responses = deque(responses)
        self._capabilities = capabilities or ProviderCapabilities(
            structured_output=True,
            raw_response_access=True,
            tool_calls=False,
            streaming=False,
            usage_metadata=True,
        )
        self.requests: list[SpecialistRequest] = []

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def invoke(self, request: SpecialistRequest) -> SpecialistResult:
        self.requests.append(request)
        if not self._responses:
            return SpecialistResult(
                TransportStatus.FAILED,
                None,
                FailureKind.INVOCATION_FAILED,
                "script exhausted",
            )
        scripted = self._responses.popleft()
        if scripted.role is not request.invocation.role:
            return SpecialistResult(
                TransportStatus.FAILED,
                None,
                FailureKind.INVOCATION_FAILED,
                f"expected {scripted.role.value}, got {request.invocation.role.value}",
            )
        if scripted.failure_kind is not None:
            return SpecialistResult(
                TransportStatus.FAILED,
                None,
                scripted.failure_kind,
                scripted.error_message or "scripted provider failure",
            )
        return SpecialistResult(
            TransportStatus.SUCCEEDED,
            scripted.raw_response,
            provider_request_id=request.invocation.invocation_id,
            usage={"input_tokens": 0, "output_tokens": 0},
        )

    @property
    def remaining(self) -> int:
        return len(self._responses)


_ROLE_RULES: dict[SpecialistRole, str] = {
    SpecialistRole.PLANNER: (
        "Inspect repository evidence and author the smallest complete implementation "
        "plan. "
        "Do not edit files or resolve material human intent by guessing."
    ),
    SpecialistRole.PLAN_CRITIC: (
        "Independently judge whether the plan is implementation-ready. Do not edit files "
        "or rewrite the plan."
    ),
    SpecialistRole.IMPLEMENTER: (
        "Implement only the approved scope in the workspace. Do not execute verification "
        "commands, invoke other specialists, or perform Git mutations."
    ),
    SpecialistRole.VERIFIER: (
        "Independently judge current files and supplied canonical evidence. Do not edit "
        "files, execute commands, or reconstruct canonical ledger fields."
    ),
    SpecialistRole.REVIEWER: (
        "Independently review the verified implementation. Do not edit files, execute "
        "commands, or reconstruct canonical ledger fields."
    ),
}


def build_specialist_request(
    *,
    invocation: SpecialistInvocation,
    repository_root: Path,
    context: dict[str, Any],
    expected_command_ids: tuple[str, ...] = (),
) -> SpecialistRequest:
    """Build a schema-bound request without passing transcript history."""
    schema = artifact_json_schema(
        invocation.artifact_kind, expected_command_ids=expected_command_ids
    )
    prompt = "\n\n".join(
        (
            f"You are the {invocation.role.value} specialist.",
            _ROLE_RULES[invocation.role],
            "Return exactly one JSON object matching the supplied output schema. "
            "No prose, Markdown fences, wrapper text, or second artifact is allowed.",
            "Task-scoped context:\n" + json.dumps(context, indent=2, sort_keys=True),
        )
    )
    return SpecialistRequest(
        invocation=invocation,
        repository_root=repository_root,
        prompt=prompt,
        output_schema=schema,
        may_write_workspace=invocation.role is SpecialistRole.IMPLEMENTER,
    )


ROLE_TO_ARTIFACT: dict[SpecialistRole, ArtifactKind] = {
    SpecialistRole.PLANNER: ArtifactKind.PLAN,
    SpecialistRole.PLAN_CRITIC: ArtifactKind.PLAN_CRITIQUE,
    SpecialistRole.IMPLEMENTER: ArtifactKind.IMPLEMENTATION,
    SpecialistRole.VERIFIER: ArtifactKind.VERIFICATION,
    SpecialistRole.REVIEWER: ArtifactKind.REVIEW,
}
